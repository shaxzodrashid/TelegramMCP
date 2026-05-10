import pytest
from unittest.mock import AsyncMock, MagicMock
from telethon import types

from telegram_mcp.service.telegram import TelegramService

@pytest.fixture
def telegram_service():
    return TelegramService()

@pytest.mark.asyncio
async def test_get_me_happy_path(telegram_service, monkeypatch):
    # Mock the start method
    mock_start = AsyncMock()
    monkeypatch.setattr(telegram_service, "start", mock_start)

    # Mock the client
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = True

    # Mock get_me to return a mock user
    mock_user = MagicMock(spec=types.User)
    mock_user.id = 123
    mock_user.first_name = "Test"
    telegram_service.client.get_me.return_value = mock_user

    result = await telegram_service.get_me()

    mock_start.assert_awaited_once()
    telegram_service.client.is_user_authorized.assert_awaited_once()
    telegram_service.client.get_me.assert_awaited_once()
    assert result == mock_user

@pytest.mark.asyncio
async def test_get_me_unauthorized(telegram_service, monkeypatch):
    # Mock the start method
    mock_start = AsyncMock()
    monkeypatch.setattr(telegram_service, "start", mock_start)

    # Mock the client
    telegram_service.client = AsyncMock()
    telegram_service.client.is_user_authorized.return_value = False

    result = await telegram_service.get_me()

    mock_start.assert_awaited_once()
    telegram_service.client.is_user_authorized.assert_awaited_once()
    telegram_service.client.get_me.assert_not_called()
    assert result is None

@pytest.mark.asyncio
async def test_get_me_no_client(telegram_service, monkeypatch):
    # Mock the start method
    mock_start = AsyncMock()
    monkeypatch.setattr(telegram_service, "start", mock_start)

    # Simulate client being None
    telegram_service.client = None

    result = await telegram_service.get_me()

    mock_start.assert_awaited_once()
    assert result is None
