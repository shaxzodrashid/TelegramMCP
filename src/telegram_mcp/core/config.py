from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Telegram Credentials
    API_ID: int = 0
    API_HASH: str = "placeholder"

    # Session Persistence
    SESSION_NAME: str = "telegram_mcp_session"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # MCP Settings
    SERVER_NAME: str = "Telegram MCP Server"
    SERVER_VERSION: str = "0.1.0"

    # Download Settings
    TELEGRAM_DOWNLOAD_DIR: str = "storage/downloads/telegram"
    TELEGRAM_DOWNLOAD_MAX_FILE_SIZE_MB: int = 100

    # Upload Settings
    TELEGRAM_UPLOAD_DIR: str = "storage/uploads/telegram"
    TELEGRAM_UPLOAD_MAX_FILE_SIZE_MB: int = 100

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


# Singleton instance
settings = Settings(_env_file=".env")

__all__ = ["settings"]
