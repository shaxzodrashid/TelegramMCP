from mcp.server.fastmcp import FastMCP, Context
from .core.config import settings
from .core.logger import logger
from .service.telegram import telegram_service
from .models.chats import ChatType, ListChatsInput, ListChatsResult
from .models.media import DownloadMediaInput, DownloadMediaResult
from .models.messages import SendMessageInput, SendMessageResult

# Initialize FastMCP server
mcp = FastMCP(
    settings.SERVER_NAME,
    instructions=f"{settings.SERVER_NAME} v{settings.SERVER_VERSION}",
)

@mcp.tool()
async def telegram_send_message(
    input_data: SendMessageInput,
    ctx: Context | None = None,
) -> SendMessageResult:
    """
    Send a message or media to a Telegram chat.
    Can be used to send normal text messages, reply to existing messages, or send files (photos, videos, documents, etc.).
    
    Safety rules:
    - Files are strictly validated against dangerous extensions (e.g., .exe, .sh) and path traversal.
    - Sending media by URL is currently not supported.
    - Media paths must be within configured safe upload/download directories.
    """
    logger.info("Executing telegram_send_message tool")
    return await telegram_service.send_message(input_data)

@mcp.tool()
async def get_account_info():
    """
    Returns information about the currently logged-in Telegram account.
    """
    logger.info("Executing get_account_info tool")
    try:
        me = await telegram_service.get_me()
        if not me:
            return "Not logged in to Telegram. Use the 'telegram-mcp auth' command to authenticate."
        return f"Logged in as: {me.first_name} (@{me.username or 'N/A'}) [ID: {me.id}]"
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return "An error occurred while getting account info."

@mcp.tool()
async def list_chats(
    search: str | None = None,
    type_filters: list[ChatType] | None = None,
    limit: int = 50,
    offset: int = 0,
    include_archived: bool = False,
    ctx: Context | None = None,
) -> ListChatsResult:
    """
    List Telegram chats/dialogs available to the authenticated user.
    Supports optional case-insensitive search by chat title/username and optional filtering by chat type.
    Returns chat metadata only and does not read message history.
    """
    logger.info("Executing list_chats tool")

    # Trim search
    if search:
        search = search.strip()
        if not search:
            search = None

    args = ListChatsInput(
        search=search,
        type_filters=type_filters,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
    )
    return await telegram_service.list_chats(args)

@mcp.tool()
async def download_telegram_media(
    chat_id: str | int,
    message_id: int,
    download_directory: str | None = None,
    preferred_file_name: str | None = None,
    allow_suspicious_files: bool = False,
    ctx: Context | None = None,
) -> DownloadMediaResult:
    """
    Download media (photo, video, audio, voice, document, etc.) from a Telegram message.
    The file is saved to a safe local storage directory.
    Suspicious file types (executables, archives) are blocked by default unless allow_suspicious_files is true.
    """
    logger.info("Executing download_telegram_media tool")
    
    args = DownloadMediaInput(
        chat_id=chat_id,
        message_id=message_id,
        download_directory=download_directory,
        preferred_file_name=preferred_file_name,
        allow_suspicious_files=allow_suspicious_files
    )
    return await telegram_service.download_media(args)

if __name__ == "__main__":
    # Note: FastMCP usually runs via its own CLI or as an ASGI app.
    # To run as a standalone server for debugging:
    logger.info(f"Starting {settings.SERVER_NAME} v{settings.SERVER_VERSION}...")

    # Configuration validation
    if settings.API_ID == 0 or settings.API_HASH == "placeholder":
        logger.warning("Telegram API credentials are not configured!")
        logger.warning("Please create a .env file with API_ID and API_HASH.")
        logger.warning("Tools requiring Telegram access will not work.")
    else:
        logger.info("Telegram configuration found.")

    logger.info("Server is running on stdio transport")
    logger.info("Waiting for MCP messages...")

    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
