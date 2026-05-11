import os
import time
from typing import Optional, Union
from pathlib import Path
from telethon import TelegramClient, errors, types
from ..core.cache import AsyncCache
from ..core.config import settings
from ..core.logger import logger
from ..core.file_utils import get_safe_path, is_suspicious, validate_size
from ..models.chats import ListChatsInput, ListChatsResult, ChatSummary, ChatType, ListChatsMeta
from ..models.media import DownloadMediaInput, DownloadMediaResult, MediaType
from datetime import datetime

class TelegramService:
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self._is_initialized = False
        self._cache = AsyncCache()

    async def start(self):
        if not self._is_initialized:
            logger.info("Starting Telethon client...")
            if not settings.API_ID or not settings.API_HASH or settings.API_HASH == "placeholder":
                logger.error("API_ID or API_HASH is missing. Please check your .env file.")
                raise ValueError("API_ID and API_HASH must be configured.")

            self.client = TelegramClient(
                settings.SESSION_NAME,
                settings.API_ID,
                settings.API_HASH
            )
            await self.client.connect()

            # Enforce secure permissions on the session file
            session_file = f"{settings.SESSION_NAME}.session"
            if os.path.exists(session_file):
                try:
                    os.chmod(session_file, 0o600)
                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not secure session file permissions: {e}")

            self._is_initialized = True
            logger.info("Telethon client connected successfully.")

    async def is_authorized(self):
        await self.start()
        if self.client:
            return await self.client.is_user_authorized()
        return False

    async def get_me(self):
        await self.start()
        if self.client and await self.client.is_user_authorized():
            cached_me = await self._cache.get("telegram_me")
            if cached_me is not None:
                return cached_me

            me = await self.client.get_me()
            if me is not None:
                await self._cache.set("telegram_me", me, ttl=300)
            return me
        return None

    async def list_chats(self, input_data: ListChatsInput) -> ListChatsResult:
        """
        List Telegram chats/dialogs available to the authenticated user.
        """
        start_time = time.time()
        logger.info(f"list_chats request: search='{input_data.search}', "
                    f"types={input_data.type_filters}, limit={input_data.limit}, offset={input_data.offset}")

        try:
            await self.start()
            if not self.client or not await self.client.is_user_authorized():
                raise ValueError("Telegram session is not authorized")

            # 1. Fetch dialogs
            # Suggested behavior from requirements:
            # internal_fetch_limit = max(300, offset + limit * 3)
            # cap internal_fetch_limit at 1000
            internal_fetch_limit = min(1000, max(300, input_data.offset + input_data.limit * 3))

            # get_dialogs returns a list of Dialog objects
            dialogs = await self.client.get_dialogs(limit=internal_fetch_limit)
            
            all_summaries = []

            # 2. Map dialogs to ChatSummary
            for dialog in dialogs:
                entity = dialog.entity
                chat_type = self._map_entity_to_chat_type(entity)

                if chat_type is None:
                    continue

                # Extracting basic metadata
                title = self._get_entity_title(entity)
                username = getattr(entity, 'username', None)

                summary = ChatSummary(
                    id=entity.id,
                    access_hash=getattr(entity, 'access_hash', None),
                    title=title,
                    username=username,
                    type=chat_type,
                    unread_count=dialog.unread_count,
                    is_pinned=dialog.pinned,
                    is_archived=dialog.archived
                )
                all_summaries.append(summary)

            # 3. Apply search filtering
            search_query = input_data.search.strip() if input_data.search else None
            if search_query:
                search_query = search_query.lower()
                filtered_summaries = []
                for s in all_summaries:
                    # Match title
                    if search_query in s.title.lower():
                        filtered_summaries.append(s)
                        continue

                    # Match username
                    if s.username and search_query in s.username.lower():
                        filtered_summaries.append(s)
                        continue

                    # Match first_name / last_name for user entities
                    # We need to check the original entity if possible, or we can just rely on title which usually contains name
                    # For Users, title is first_name + last_name in Telethon's get_display_name
                    # So title check covers it.
                all_summaries = filtered_summaries

            # 4. Apply type filtering
            if input_data.type_filters:
                all_summaries = [s for s in all_summaries if s.type in input_data.type_filters]

            # 5. Archived filtering
            if not input_data.include_archived:
                all_summaries = [s for s in all_summaries if not s.is_archived]

            total_filtered = len(all_summaries)

            # 6. Apply offset/limit
            paged_summaries = all_summaries[input_data.offset : input_data.offset + input_data.limit]
            has_more = total_filtered > (input_data.offset + input_data.limit)

            elapsed_time = time.time() - start_time
            logger.info(f"list_chats success: returned {len(paged_summaries)}/{total_filtered} chats in {elapsed_time:.2f}s")

            return ListChatsResult(
                data=paged_summaries,
                meta=ListChatsMeta(
                    total_returned=len(paged_summaries),
                    limit=input_data.limit,
                    offset=input_data.offset,
                    search=input_data.search,
                    type_filters=input_data.type_filters,
                    has_more=has_more
                )
            )

        except errors.FloodWaitError as e:
            logger.error(f"Telegram rate limit: try again in {e.seconds} seconds")
            raise ValueError(f"Telegram rate limit: try again in {e.seconds} seconds")
        except ValueError as e:
            logger.error(f"Validation error in list_chats: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in list_chats: {e}")
            raise ValueError("An unexpected error occurred")

    async def download_media(self, input_data: DownloadMediaInput) -> DownloadMediaResult:
        """
        Download media from a Telegram message.
        """
        logger.info(f"download_media request: chat_id='{input_data.chat_id}', message_id={input_data.message_id}")
        
        try:
            await self.start()
            if not self.client or not await self.client.is_user_authorized():
                raise ValueError("Telegram session is not authorized")

            # 1. Get the message
            try:
                entity = await self.client.get_entity(input_data.chat_id)
                message = await self.client.get_messages(entity, ids=input_data.message_id)
            except Exception as e:
                logger.error(f"Failed to fetch message {input_data.message_id} in {input_data.chat_id}: {e}")
                return DownloadMediaResult(
                    success=False,
                    chat_id=input_data.chat_id,
                    message_id=input_data.message_id,
                    media_type=MediaType.unknown,
                    error_reason=f"Message or chat not found: {str(e)}"
                )

            if not message or not message.media:
                return DownloadMediaResult(
                    success=False,
                    chat_id=input_data.chat_id,
                    message_id=input_data.message_id,
                    media_type=MediaType.unknown,
                    error_reason="Message does not exist or contains no media"
                )

            # 2. Detect media info
            media_info = self._detect_media_info(message)
            
            # 3. Validate size
            if media_info['size_bytes'] and not validate_size(media_info['size_bytes']):
                max_mb = settings.TELEGRAM_DOWNLOAD_MAX_FILE_SIZE_MB
                return DownloadMediaResult(
                    success=False,
                    chat_id=input_data.chat_id,
                    message_id=input_data.message_id,
                    media_type=media_info['type'],
                    size_bytes=media_info['size_bytes'],
                    error_reason=f"File size exceeds limit of {max_mb} MB"
                )

            # 4. Resolve file name
            filename = input_data.preferred_file_name or media_info['file_name']
            if not filename:
                # Generate a fallback filename
                ext = media_info['extension'] or ".bin"
                filename = f"telegram_{input_data.chat_id}_{input_data.message_id}{ext}"
            
            # 5. Check for suspicious files
            suspicious, detected_ext = is_suspicious(filename)
            warning = None
            if suspicious:
                if not input_data.allow_suspicious_files:
                    return DownloadMediaResult(
                        success=False,
                        chat_id=input_data.chat_id,
                        message_id=input_data.message_id,
                        media_type=media_info['type'],
                        extension=detected_ext,
                        suspicious=True,
                        error_reason="SUSPICIOUS_FILE_TYPE_BLOCKED"
                    )
                else:
                    warning = "This file type may be unsafe. Do not execute it unless you fully trust the source."

            # 6. Resolve safe path
            safe_path = get_safe_path(
                settings.TELEGRAM_DOWNLOAD_DIR,
                input_data.download_directory,
                filename
            )

            # 7. Perform download
            logger.info(f"Downloading media to {safe_path}...")
            downloaded_path = await self.client.download_media(message, file=str(safe_path))
            
            if not downloaded_path:
                return DownloadMediaResult(
                    success=False,
                    chat_id=input_data.chat_id,
                    message_id=input_data.message_id,
                    media_type=media_info['type'],
                    error_reason="Telegram API download failed"
                )

            # Get final size and extension if unknown before
            final_path = Path(downloaded_path)
            size_bytes = final_path.stat().st_size
            extension = final_path.suffix

            return DownloadMediaResult(
                success=True,
                chat_id=input_data.chat_id,
                message_id=input_data.message_id,
                media_type=media_info['type'],
                file_name=final_path.name,
                original_file_name=media_info['file_name'],
                file_path=str(final_path),
                mime_type=media_info['mime_type'],
                extension=extension,
                size_bytes=size_bytes,
                suspicious=suspicious,
                warning=warning,
                downloaded_at=datetime.now()
            )

        except errors.FloodWaitError as e:
            logger.error(f"Telegram rate limit: try again in {e.seconds} seconds")
            return DownloadMediaResult(
                success=False,
                chat_id=input_data.chat_id,
                message_id=input_data.message_id,
                media_type=MediaType.unknown,
                error_reason=f"Telegram rate limit: try again in {e.seconds} seconds"
            )
        except Exception as e:
            logger.exception(f"Unexpected error in download_media: {e}")
            return DownloadMediaResult(
                success=False,
                chat_id=input_data.chat_id,
                message_id=input_data.message_id,
                media_type=MediaType.unknown,
                error_reason=f"An unexpected error occurred: {str(e)}"
            )

    async def send_message(self, input_data: "SendMessageInput") -> "SendMessageResult":
        """
        Send a message or media to a Telegram chat.
        """
        from ..models.messages import SendMessageInput, SendMessageResult, ParseMode
        from ..core.file_utils import validate_safe_upload_path, is_suspicious, validate_upload_size
        import mimetypes

        logger.info(f"send_message request: chat='{input_data.chat}', has_message={bool(input_data.message)}, has_media={bool(input_data.media)}")

        try:
            await self.start()
            if not self.client or not await self.client.is_user_authorized():
                return SendMessageResult(ok=False, error={"code": "AUTH_REQUIRED", "message": "Telegram session is not authorized"})

            # Basic validation
            if not input_data.message and not input_data.media:
                return SendMessageResult(ok=False, error={"code": "INVALID_INPUT", "message": "Either 'message' or 'media' must be provided."})

            if input_data.media and input_data.media.url and input_data.media.path:
                return SendMessageResult(ok=False, error={"code": "INVALID_INPUT", "message": "Cannot provide both media path and url."})

            if input_data.media and input_data.media.url:
                return SendMessageResult(ok=False, error={"code": "MEDIA_URL_NOT_ALLOWED", "message": "Sending media by URL is not currently supported for security reasons."})

            # Resolve chat
            try:
                # Telethon get_entity can handle username, phone, or ID
                # If ID is string, try to convert to int if it's purely digits
                chat_identifier = input_data.chat
                if isinstance(chat_identifier, str) and chat_identifier.lstrip('-').isdigit():
                    chat_identifier = int(chat_identifier)
                entity = await self.client.get_entity(chat_identifier)
            except Exception as e:
                logger.error(f"Failed to resolve chat '{input_data.chat}': {e}")
                return SendMessageResult(ok=False, error={"code": "CHAT_NOT_FOUND", "message": f"Could not find chat '{input_data.chat}'", "details": {"error": str(e)}})

            parse_mode = None if input_data.parse_mode == ParseMode.plain else input_data.parse_mode.value

            # Handle Media
            if input_data.media and input_data.media.path:
                file_path_str = input_data.media.path
                safe_path = validate_safe_upload_path(file_path_str)
                
                if not safe_path or not safe_path.exists() or not safe_path.is_file():
                    return SendMessageResult(ok=False, error={"code": "FILE_NOT_FOUND", "message": f"File not found or unsafe path: {file_path_str}"})

                file_size = safe_path.stat().st_size
                if not validate_upload_size(file_size):
                    return SendMessageResult(ok=False, error={"code": "FILE_TOO_LARGE", "message": f"File exceeds maximum upload size of {settings.TELEGRAM_UPLOAD_MAX_FILE_SIZE_MB}MB."})

                suspicious, ext = is_suspicious(safe_path.name)
                if suspicious:
                    return SendMessageResult(ok=False, error={"code": "FILE_TYPE_BLOCKED", "message": f"Sending this file type is blocked for security reasons.", "details": {"extension": ext}})

                # Determine attributes based on media type
                attributes = []
                force_document = False
                media_type = input_data.media.type
                
                if media_type == MediaType.video_note:
                    attributes.append(types.DocumentAttributeVideo(duration=0, w=0, h=0, round_message=True))
                elif media_type == MediaType.voice:
                    attributes.append(types.DocumentAttributeAudio(duration=0, voice=True))
                elif media_type in (MediaType.document, MediaType.unknown):
                    force_document = True

                # Determine mime type if possible, though Telethon usually guesses well
                
                logger.info(f"Sending file {safe_path} to {input_data.chat}")
                sent_msg = await self.client.send_file(
                    entity,
                    file=str(safe_path),
                    caption=input_data.media.caption or input_data.message or "",
                    reply_to=input_data.reply_to_message_id,
                    parse_mode=parse_mode,
                    silent=input_data.silent,
                    attributes=attributes if attributes else None,
                    force_document=force_document
                )
            else:
                # Handle Text
                logger.info(f"Sending text message to {input_data.chat}")
                sent_msg = await self.client.send_message(
                    entity,
                    message=input_data.message or "",
                    reply_to=input_data.reply_to_message_id,
                    parse_mode=parse_mode,
                    silent=input_data.silent,
                    link_preview=not input_data.disable_link_preview
                )

            if not sent_msg:
                return SendMessageResult(ok=False, error={"code": "TELEGRAM_SEND_FAILED", "message": "Telegram API failed to send the message."})

            # Detect sent type
            sent_type = "text"
            if sent_msg.media:
                info = self._detect_media_info(sent_msg)
                sent_type = info['type'].value if info['type'] else "media"

            return SendMessageResult(
                ok=True,
                result={
                    "chat_id": str(entity.id),
                    "message_id": sent_msg.id,
                    "reply_to_message_id": sent_msg.reply_to_msg_id,
                    "type": sent_type,
                    "date": sent_msg.date.isoformat() if sent_msg.date else None,
                    "silent": input_data.silent
                }
            )

        except errors.FloodWaitError as e:
            logger.error(f"Telegram rate limit: try again in {e.seconds} seconds")
            return SendMessageResult(ok=False, error={"code": "RATE_LIMITED", "message": f"Telegram rate limit: try again in {e.seconds} seconds"})
        except Exception as e:
            logger.exception(f"Unexpected error in send_message: {e}")
            return SendMessageResult(ok=False, error={"code": "TELEGRAM_SEND_FAILED", "message": "An unexpected error occurred", "details": {"error": str(e)}})

    def _detect_media_info(self, message) -> dict:
        """
        Detect media type, name, size and mime from a Telethon message.
        """
        media = message.media
        info = {
            'type': MediaType.unknown,
            'file_name': None,
            'size_bytes': None,
            'mime_type': None,
            'extension': None
        }

        if isinstance(media, types.MessageMediaPhoto):
            info['type'] = MediaType.photo
            info['mime_type'] = "image/jpeg"
            info['extension'] = ".jpg"
            # Get largest photo size
            if isinstance(media.photo, types.Photo):
                info['size_bytes'] = media.photo.sizes[-1].size if hasattr(media.photo.sizes[-1], 'size') else None
        
        elif isinstance(media, types.MessageMediaDocument):
            doc = media.document
            info['size_bytes'] = doc.size
            info['mime_type'] = doc.mime_type
            
            # Extract filename from attributes
            for attr in doc.attributes:
                if isinstance(attr, types.DocumentAttributeFilename):
                    info['file_name'] = attr.file_name
                    info['extension'] = Path(attr.file_name).suffix
                    break
            
            # Determine type from attributes or mime
            is_sticker = any(isinstance(a, types.DocumentAttributeSticker) for a in doc.attributes)
            is_video = any(isinstance(a, types.DocumentAttributeVideo) for a in doc.attributes)
            is_audio = any(isinstance(a, types.DocumentAttributeAudio) for a in doc.attributes)
            is_animated = any(isinstance(a, types.DocumentAttributeAnimated) for a in doc.attributes)

            if is_sticker:
                info['type'] = MediaType.sticker
            elif is_animated:
                info['type'] = MediaType.animation
            elif is_video:
                # Video notes have Video attribute with round_message=True
                is_video_note = any(isinstance(a, types.DocumentAttributeVideo) and getattr(a, 'round_message', False) for a in doc.attributes)
                info['type'] = MediaType.video_note if is_video_note else MediaType.video
            elif is_audio:
                # Voice messages have Audio attribute with voice=True
                is_voice = any(isinstance(a, types.DocumentAttributeAudio) and getattr(a, 'voice', False) for a in doc.attributes)
                info['type'] = MediaType.voice if is_voice else MediaType.audio
            else:
                info['type'] = MediaType.document

        return info

    def _map_entity_to_chat_type(self, entity) -> Optional[ChatType]:
        if isinstance(entity, types.User):
            if entity.is_self:
                return ChatType.saved_messages
            elif entity.bot:
                return ChatType.bot
            else:
                return ChatType.user
        elif isinstance(entity, types.Chat):
            return ChatType.group
        elif isinstance(entity, types.Channel):
            if entity.megagroup:
                return ChatType.supergroup
            elif entity.broadcast:
                return ChatType.channel
            else:
                # Fallback for other channel types if any
                return ChatType.channel
        return None

    def _get_entity_title(self, entity) -> str:
        if isinstance(entity, types.User):
            first_name = entity.first_name or ""
            last_name = entity.last_name or ""
            title = f"{first_name} {last_name}".strip()
            if not title:
                title = f"User {entity.id}"
            return title
        elif hasattr(entity, 'title'):
            return entity.title or f"Chat {entity.id}"
        return f"Entity {entity.id}"

    async def stop(self):
        if self._is_initialized and self.client:
            logger.info("Stopping Telethon client...")
            await self.client.disconnect()
            self._is_initialized = False
            logger.info("Telethon client stopped.")

# Singleton instance
telegram_service = TelegramService()

__all__ = ["telegram_service", "TelegramService"]
