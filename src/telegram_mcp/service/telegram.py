from typing import Optional
from telethon import TelegramClient
from ..core.config import settings
from ..core.logger import logger

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
            await self.client.start()
            self._is_initialized = True
            logger.info("Telethon client started successfully.")

    async def stop(self):
        if self._is_initialized and self.client:
            logger.info("Stopping Telethon client...")
            await self.client.disconnect()
            self._is_initialized = False
            logger.info("Telethon client stopped.")

    async def get_me(self):
        await self.start()
        if self.client:
            return await self.client.get_me()
        return None

# Singleton instance
telegram_service = TelegramService()

__all__ = ["telegram_service", "TelegramService"]
