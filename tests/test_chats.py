import pytest
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock
from telethon import types
from telegram_mcp.models.chats import ListChatsInput, ChatType
from telegram_mcp.service.telegram import TelegramService

@pytest.fixture
def telegram_service():
    return TelegramService()

def test_list_chats_input_validation():
    # Default input works
    input_data = ListChatsInput()
    assert input_data.limit == 50
    assert input_data.offset == 0
    assert input_data.include_archived is False

    # Limit validation
    with pytest.raises(ValidationError):
        ListChatsInput(limit=0)
    with pytest.raises(ValidationError):
        ListChatsInput(limit=101)

    # Offset validation
    with pytest.raises(ValidationError):
        ListChatsInput(offset=-1)

    # Unknown type filter
    with pytest.raises(ValidationError):
        ListChatsInput(type_filters=["invalid_type"])

    # Extra fields rejected
    with pytest.raises(ValidationError):
        ListChatsInput(extra_field="rejected")

def test_get_entity_title(telegram_service):
    # User with first and last name
    user1 = MagicMock(spec=types.User)
    user1.first_name = "Alice"
    user1.last_name = "Smith"
    assert telegram_service._get_entity_title(user1) == "Alice Smith"

    # User with only first name
    user2 = MagicMock(spec=types.User)
    user2.first_name = "Bob"
    user2.last_name = None
    assert telegram_service._get_entity_title(user2) == "Bob"

    # User with only last name
    user3 = MagicMock(spec=types.User)
    user3.first_name = None
    user3.last_name = "Jones"
    assert telegram_service._get_entity_title(user3) == "Jones"

    # User with neither name
    user4 = MagicMock(spec=types.User)
    user4.id = 123
    user4.first_name = None
    user4.last_name = None
    assert telegram_service._get_entity_title(user4) == "User 123"

    # Entity with a title
    chat1 = MagicMock()
    chat1.title = "Cool Group"
    assert telegram_service._get_entity_title(chat1) == "Cool Group"

    # Entity with an empty title
    chat2 = MagicMock()
    chat2.id = 456
    chat2.title = ""
    assert telegram_service._get_entity_title(chat2) == "Chat 456"

    # Entity without a title attribute
    class EntityWithoutTitle:
        id = 789

    assert telegram_service._get_entity_title(EntityWithoutTitle()) == "Entity 789"


@pytest.mark.asyncio
async def test_map_entity_to_chat_type(telegram_service):
    # User -> user
    user = MagicMock(spec=types.User)
    user.is_self = False
    user.bot = False
    assert telegram_service._map_entity_to_chat_type(user) == ChatType.user

    # Bot -> bot
    bot = MagicMock(spec=types.User)
    bot.is_self = False
    bot.bot = True
    assert telegram_service._map_entity_to_chat_type(bot) == ChatType.bot

    # Self -> saved_messages
    me = MagicMock(spec=types.User)
    me.is_self = True
    me.bot = False
    assert telegram_service._map_entity_to_chat_type(me) == ChatType.saved_messages

    # Chat -> group
    group = MagicMock(spec=types.Chat)
    assert telegram_service._map_entity_to_chat_type(group) == ChatType.group

    # Channel -> channel
    channel = MagicMock(spec=types.Channel)
    channel.megagroup = False
    channel.broadcast = True
    assert telegram_service._map_entity_to_chat_type(channel) == ChatType.channel

    # Megagroup -> supergroup
    supergroup = MagicMock(spec=types.Channel)
    supergroup.megagroup = True
    supergroup.broadcast = False
    assert telegram_service._map_entity_to_chat_type(supergroup) == ChatType.supergroup

@pytest.mark.asyncio
async def test_list_chats_filtering(telegram_service):
    # Mock Telethon client and dialogs
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True
    
    # Create mock dialogs
    dialog1 = MagicMock()
    dialog1.entity = MagicMock(spec=types.User)
    dialog1.entity.id = 1
    dialog1.entity.first_name = "Alice"
    dialog1.entity.last_name = "Smith"
    dialog1.entity.username = "alice123"
    dialog1.entity.is_self = False
    dialog1.entity.bot = False
    dialog1.unread_count = 5
    dialog1.pinned = False
    dialog1.archived = False

    dialog2 = MagicMock()
    dialog2.entity = MagicMock(spec=types.Channel)
    dialog2.entity.id = 2
    dialog2.entity.title = "Tech News"
    dialog2.entity.username = "technews"
    dialog2.entity.megagroup = False
    dialog2.entity.broadcast = True
    dialog2.unread_count = 0
    dialog2.pinned = True
    dialog2.archived = False

    dialog3 = MagicMock()
    dialog3.entity = MagicMock(spec=types.User)
    dialog3.entity.id = 3
    dialog3.entity.first_name = "Bob"
    dialog3.entity.last_name = ""
    dialog3.entity.username = None
    dialog3.entity.is_self = False
    dialog3.entity.bot = False
    dialog3.unread_count = 1
    dialog3.pinned = False
    dialog3.archived = True

    telegram_service.client.get_dialogs.return_value = [dialog1, dialog2, dialog3]

    # Test Search: case-insensitive
    result = await telegram_service.list_chats(ListChatsInput(search="ALICE"))
    assert len(result.data) == 1
    assert result.data[0].title == "Alice Smith"

    # Test Search: username
    result = await telegram_service.list_chats(ListChatsInput(search="technews"))
    assert len(result.data) == 1
    assert result.data[0].id == 2

    # Test Type Filtering
    result = await telegram_service.list_chats(ListChatsInput(type_filters=[ChatType.channel]))
    assert len(result.data) == 1
    assert result.data[0].type == ChatType.channel

    # Test include_archived=False (default)
    result = await telegram_service.list_chats(ListChatsInput())
    assert len(result.data) == 2 # Alice and Tech News
    assert all(not d.is_archived for d in result.data)

    # Test include_archived=True
    result = await telegram_service.list_chats(ListChatsInput(include_archived=True))
    assert len(result.data) == 3

    # Test Pagination (offset/limit)
    result = await telegram_service.list_chats(ListChatsInput(limit=1, offset=0))
    assert len(result.data) == 1
    assert result.meta.has_more is True

    result = await telegram_service.list_chats(ListChatsInput(limit=1, offset=1))
    assert len(result.data) == 1
    assert result.meta.has_more is False

@pytest.mark.asyncio
async def test_list_chats_error_handling(telegram_service):
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    # Test FloodWaitError
    from telethon import errors
    class MockRequest:
        pass
    telegram_service.client.get_dialogs.side_effect = errors.FloodWaitError(request=MockRequest(), capture=42)

    with pytest.raises(ValueError, match="Telegram rate limit: try again in 42 seconds"):
        await telegram_service.list_chats(ListChatsInput())

    # Test ValueError
    telegram_service.client.get_dialogs.side_effect = ValueError("Test ValueError")

    with pytest.raises(ValueError, match="Test ValueError"):
        await telegram_service.list_chats(ListChatsInput())

    # Test generic Exception
    telegram_service.client.get_dialogs.side_effect = Exception("Test generic Exception")

    with pytest.raises(ValueError, match="An unexpected error occurred"):
        await telegram_service.list_chats(ListChatsInput())
