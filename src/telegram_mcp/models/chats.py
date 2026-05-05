from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class ChatType(str, Enum):
    user = "user"
    bot = "bot"
    group = "group"
    supergroup = "supergroup"
    channel = "channel"
    saved_messages = "saved_messages"

class ListChatsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search: str | None = None
    type_filters: list[ChatType] | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_archived: bool = False

class ChatSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    access_hash: int | None = None
    title: str
    username: str | None = None
    type: ChatType
    unread_count: int | None = None
    is_pinned: bool | None = None
    is_archived: bool | None = None

class ListChatsMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_returned: int
    limit: int
    offset: int
    search: str | None
    type_filters: list[ChatType] | None
    has_more: bool

class ListChatsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[ChatSummary]
    meta: ListChatsMeta
