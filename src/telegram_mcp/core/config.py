from pathlib import Path
from pydantic import field_validator
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

    @field_validator(
        "SESSION_NAME", "TELEGRAM_DOWNLOAD_DIR", "TELEGRAM_UPLOAD_DIR", mode="after"
    )
    @classmethod
    def resolve_to_absolute_path(cls, v: str) -> str:
        """Resolves relative paths to absolute ones based on the current working directory."""
        path = Path(v)
        if not path.is_absolute():
            # We assume relative paths are relative to the project root (CWD)
            return str(path.absolute())
        return str(path)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


# Singleton instance
settings = Settings(_env_file=".env")

__all__ = ["settings"]
