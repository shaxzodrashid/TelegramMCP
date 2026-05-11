import pytest
import os
from pathlib import Path
from pydantic import ValidationError
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from telegram_mcp.models.messages import SendMessageInput, SendMediaInput, ParseMode
from telegram_mcp.models.media import MediaType
from telegram_mcp.service.telegram import TelegramService
from telegram_mcp.core.config import settings

@pytest.fixture
def telegram_service():
    return TelegramService()

def test_send_message_input_validation():
    # Valid text message
    input_data = SendMessageInput(chat="test_chat", message="Hello")
    assert input_data.chat == "test_chat"
    assert input_data.message == "Hello"

    # Valid reply
    input_data = SendMessageInput(chat="test_chat", message="Hello", reply_to_message_id=123)
    assert input_data.reply_to_message_id == 123

    # Valid media
    input_data = SendMessageInput(chat="test_chat", media=SendMediaInput(path="test.jpg"))
    assert input_data.media.path == "test.jpg"

    # Extra fields
    with pytest.raises(ValidationError):
        SendMessageInput(chat="test_chat", message="Hello", extra="extra")

@pytest.mark.asyncio
async def test_reject_empty_request(telegram_service):
    # Missing both message and media
    input_data = SendMessageInput(chat="test_chat")
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    result = await telegram_service.send_message(input_data)
    assert result.ok is False
    assert result.error["code"] == "INVALID_INPUT"

@pytest.mark.asyncio
async def test_reject_both_path_and_url(telegram_service):
    input_data = SendMessageInput(
        chat="test_chat", 
        media=SendMediaInput(path="test.jpg", url="http://example.com/test.jpg")
    )
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    result = await telegram_service.send_message(input_data)
    assert result.ok is False
    assert result.error["code"] == "INVALID_INPUT"

@pytest.mark.asyncio
async def test_reject_url(telegram_service):
    input_data = SendMessageInput(
        chat="test_chat", 
        media=SendMediaInput(url="http://example.com/test.jpg")
    )
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    result = await telegram_service.send_message(input_data)
    assert result.ok is False
    assert result.error["code"] == "MEDIA_URL_NOT_ALLOWED"

@pytest.mark.asyncio
async def test_reject_unsafe_path(telegram_service):
    # Path traversal outside allowed dirs
    input_data = SendMessageInput(
        chat="test_chat", 
        media=SendMediaInput(path="../../../etc/passwd")
    )
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    result = await telegram_service.send_message(input_data)
    assert result.ok is False
    assert result.error["code"] == "FILE_NOT_FOUND" # or unsafe path

@pytest.mark.asyncio
async def test_reject_blocked_extension(telegram_service):
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    input_data = SendMessageInput(
        chat="test_chat", 
        media=SendMediaInput(path="C:/safe/dir/virus.exe")
    )

    with patch('telegram_mcp.core.file_utils.validate_safe_upload_path', return_value=Path("C:/safe/dir/virus.exe")), \
         patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.is_file', return_value=True), \
         patch('pathlib.Path.stat', return_value=MagicMock(st_size=1024)), \
         patch('telegram_mcp.core.file_utils.validate_upload_size', return_value=True), \
         patch('telegram_mcp.core.file_utils.is_suspicious', return_value=(True, ".exe")):
            
        result = await telegram_service.send_message(input_data)
        assert result.ok is False
        assert result.error["code"] == "FILE_TYPE_BLOCKED"

@pytest.mark.asyncio
async def test_reject_missing_file(telegram_service):
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    input_data = SendMessageInput(
        chat="test_chat", 
        media=SendMediaInput(path="C:/safe/dir/does_not_exist.jpg")
    )

    with patch('telegram_mcp.core.file_utils.validate_safe_upload_path', return_value=Path("C:/safe/dir/does_not_exist.jpg")), \
         patch('pathlib.Path.exists', return_value=False):
            
        result = await telegram_service.send_message(input_data)
        assert result.ok is False
        assert result.error["code"] == "FILE_NOT_FOUND"

@pytest.mark.asyncio
async def test_reject_too_large_file(telegram_service):
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    input_data = SendMessageInput(
        chat="test_chat", 
        media=SendMediaInput(path="C:/safe/dir/large.jpg")
    )

    with patch('telegram_mcp.core.file_utils.validate_safe_upload_path', return_value=Path("C:/safe/dir/large.jpg")), \
         patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.is_file', return_value=True), \
         patch('pathlib.Path.stat'), \
         patch('telegram_mcp.core.file_utils.validate_upload_size', return_value=False):
            
        result = await telegram_service.send_message(input_data)
        assert result.ok is False
        assert result.error["code"] == "FILE_TOO_LARGE"

@pytest.mark.asyncio
async def test_send_text_success(telegram_service):
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    entity = MagicMock()
    entity.id = 123
    telegram_service.client.get_entity.return_value = entity

    sent_msg = MagicMock()
    sent_msg.id = 456
    sent_msg.reply_to_msg_id = None
    sent_msg.media = None
    sent_msg.date = datetime.now()
    telegram_service.client.send_message.return_value = sent_msg

    input_data = SendMessageInput(chat="test_chat", message="Hello")
    result = await telegram_service.send_message(input_data)

    assert result.ok is True
    assert result.result["message_id"] == 456
    assert result.result["type"] == "text"
    
    telegram_service.client.send_message.assert_called_once_with(
        entity,
        message="Hello",
        reply_to=None,
        parse_mode=None,
        silent=False,
        link_preview=True
    )

@pytest.mark.asyncio
async def test_send_reply_success(telegram_service):
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    entity = MagicMock()
    entity.id = 123
    telegram_service.client.get_entity.return_value = entity

    sent_msg = MagicMock()
    sent_msg.id = 457
    sent_msg.reply_to_msg_id = 456
    sent_msg.media = None
    sent_msg.date = datetime.now()
    telegram_service.client.send_message.return_value = sent_msg

    input_data = SendMessageInput(chat="test_chat", message="Reply text", reply_to_message_id=456)
    result = await telegram_service.send_message(input_data)

    assert result.ok is True
    assert result.result["reply_to_message_id"] == 456
    
    telegram_service.client.send_message.assert_called_once_with(
        entity,
        message="Reply text",
        reply_to=456,
        parse_mode=None,
        silent=False,
        link_preview=True
    )

@pytest.mark.asyncio
async def test_send_client_failure(telegram_service):
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service._is_initialized = True

    telegram_service.client.get_entity.return_value = MagicMock()
    telegram_service.client.send_message.side_effect = Exception("API error")

    input_data = SendMessageInput(chat="test_chat", message="Hello")
    result = await telegram_service.send_message(input_data)

    assert result.ok is False
    assert result.error["code"] == "TELEGRAM_SEND_FAILED"
