from mcp.server.fastmcp import FastMCP
from .core.config import settings
from .core.logger import logger
from .service.telegram import telegram_service

# Initialize FastMCP server
mcp = FastMCP(
    settings.SERVER_NAME,
    instructions=f"{settings.SERVER_NAME} v{settings.SERVER_VERSION}",
)

@mcp.tool()
async def get_account_info():
    """
    Returns information about the currently logged-in Telegram account.
    """
    logger.info("Executing get_account_info tool")
    me = await telegram_service.get_me()
    return f"Logged in as: {me.first_name} (@{me.username}) [ID: {me.id}]"

if __name__ == "__main__":
    # Note: FastMCP usually runs via its own CLI or as an ASGI app.
    # To run as a standalone server for debugging:
    mcp.run()
