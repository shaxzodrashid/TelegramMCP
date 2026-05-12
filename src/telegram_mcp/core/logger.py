import os
import sys
from loguru import logger


def setup_logger(level: str = "INFO"):
    """
    Configures the global logger with a professional format.
    """
    # Ensure logs directory has secure permissions
    os.makedirs("logs", mode=0o700, exist_ok=True)
    logger.remove()  # Remove default handler

    # Custom format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stderr,
        level=level,
        format=log_format,
        colorize=True,
    )

    # Optionally add a file logger
    logger.add(
        "logs/telegram_mcp.log",
        rotation="10 MB",
        retention="1 week",
        level="INFO",
        format=log_format,
        compression="zip",
    )


# Pre-configure with default level
setup_logger()

__all__ = ["logger", "setup_logger"]
