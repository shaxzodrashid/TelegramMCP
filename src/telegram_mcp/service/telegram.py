import os
import time
from typing import Optional
from telethon import TelegramClient, errors, types
from ..core.config import settings
from ..core.logger import logger
from ..models.chats import ListChatsInput, ListChatsResult, ChatSummary, ChatType, ListChatsMeta

class TelegramService:
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self._is_initialized = False

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
                except Exception as e:
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
            return await self.client.get_me()
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
