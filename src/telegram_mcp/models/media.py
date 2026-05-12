from enum import Enum
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MediaType(str, Enum):
    photo = "photo"
    video = "video"
    audio = "audio"
    voice = "voice"
    document = "document"
    animation = "animation"
    sticker = "sticker"
    video_note = "video_note"
    unknown = "unknown"


class DownloadMediaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat_id: str | int = Field(..., description="The ID or username of the chat")
    message_id: int = Field(
        ..., description="The ID of the message containing the media", ge=1
    )
    download_directory: str | None = Field(
        None, description="Optional subdirectory within the safe storage"
    )
    preferred_file_name: str | None = Field(
        None, description="Optional preferred name for the downloaded file"
    )
    allow_suspicious_files: bool = Field(
        False, description="Whether to allow downloading potentially unsafe file types"
    )


class DownloadMediaResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    chat_id: str | int
    message_id: int
    media_type: MediaType
    file_name: str | None = None
    original_file_name: str | None = None
    file_path: str | None = None
    mime_type: str | None = None
    extension: str | None = None
    size_bytes: int | None = None
    suspicious: bool = False
    downloaded_at: datetime | None = None
    error_reason: str | None = None
    warning: str | None = None
