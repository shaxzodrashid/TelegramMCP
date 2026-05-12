from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from .media import MediaType


class ParseMode(str, Enum):
    plain = "plain"
    markdown = "markdown"
    html = "html"


class SendMediaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str | None = Field(None, description="Local path to the file to send")
    url: str | None = Field(
        None, description="URL of the media to send (not currently supported)"
    )
    type: MediaType = Field(
        default=MediaType.unknown, description="Declared media type"
    )
    caption: str | None = Field(None, description="Optional caption for the media")
    mime_type: str | None = Field(None, description="Optional MIME type hint")
    file_name: str | None = Field(None, description="Optional file name override")


class SendMessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat: str | int = Field(..., description="Username, phone number, or chat ID")
    message: str | None = Field(None, description="The text of the message")
    reply_to_message_id: int | None = Field(
        None, description="Optional message ID to reply to"
    )
    media: SendMediaInput | None = Field(None, description="Optional media to send")
    parse_mode: ParseMode = Field(
        default=ParseMode.plain, description="Formatting mode for the message text"
    )
    silent: bool = Field(
        default=False, description="Whether to send the message without notification"
    )
    disable_link_preview: bool = Field(
        default=False, description="Whether to disable link previews for text messages"
    )


class SendMessageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    result: dict | None = None
    error: dict | None = None


# Example success result:
# {
#   "ok": true,
#   "result": {
#     "chat_id": "...",
#     "message_id": 123,
#     "reply_to_message_id": 456,
#     "type": "text | photo | ...",
#     "date": "...",
#     "silent": false
#   }
# }

# Example error result:
# {
#   "ok": false,
#   "error": {
#     "code": "STRING_CODE",
#     "message": "Human-readable message",
#     "details": {}
#   }
# }
