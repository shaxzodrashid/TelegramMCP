import os
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Set secure umask for the entire process.
# This prevents Telethon/SQLite from temporarily creating world-readable files
# (e.g. .session or .session-wal) during initialization.
os.umask(0o077)

class Settings(BaseSettings):
    # Telegram Credentials
    API_ID: int = 0
    API_HASH: str = "placeholder"
    
    # Session Persistence
    SESSION_NAME: str = "telegram_mcp_session"
    
    @field_validator("SESSION_NAME")
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        if "/" in v or "\\" in v or ".." in v:
            raise ValueError("SESSION_NAME must not contain path separators")
        return v

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # MCP Settings
    SERVER_NAME: str = "Telegram MCP Server"
    SERVER_VERSION: str = "0.1.0"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

# Singleton instance
settings = Settings(_env_file=".env")

__all__ = ["settings"]
