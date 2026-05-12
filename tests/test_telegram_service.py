import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telethon import types
from telegram_mcp.service.telegram import TelegramService

@pytest.fixture
def telegram_service():
    service = TelegramService()
    # Mock the client and initialization to avoid actual connection
    service.client = AsyncMock()
    service._is_initialized = True
    return service

@pytest.mark.asyncio
async def test_get_me_unauthorized(telegram_service):
    # Setup: client says not authorized
    telegram_service.client.is_user_authorized.return_value = False

    result = await telegram_service.get_me()

    assert result is None
    telegram_service.client.is_user_authorized.assert_called_once()
    # Ensure get_me was NOT called on the client
    telegram_service.client.get_me.assert_not_called()

@pytest.mark.asyncio
async def test_get_me_cached(telegram_service):
    # Setup: authorized and value in cache
    telegram_service.client.is_user_authorized.return_value = True

    mock_me = MagicMock(spec=types.User)
    mock_me.id = 12345

    with patch.object(telegram_service._cache, 'get', AsyncMock(return_value=mock_me)) as mock_cache_get:
        result = await telegram_service.get_me()

        assert result == mock_me
        mock_cache_get.assert_called_once_with("telegram_me")
        # Ensure client.get_me was NOT called because it was cached
        telegram_service.client.get_me.assert_not_called()

@pytest.mark.asyncio
async def test_get_me_not_cached(telegram_service):
    # Setup: authorized, NOT in cache, client returns user
    telegram_service.client.is_user_authorized.return_value = True

    mock_me = MagicMock(spec=types.User)
    mock_me.id = 12345
    telegram_service.client.get_me.return_value = mock_me

    with patch.object(telegram_service._cache, 'get', AsyncMock(return_value=None)) as mock_cache_get:
        with patch.object(telegram_service._cache, 'set', AsyncMock()) as mock_cache_set:
            result = await telegram_service.get_me()

            assert result == mock_me
            mock_cache_get.assert_called_once_with("telegram_me")
            telegram_service.client.get_me.assert_called_once()
            # Verify it was cached
            mock_cache_set.assert_called_once_with("telegram_me", mock_me, ttl=300)

@pytest.mark.asyncio
async def test_get_me_client_returns_none(telegram_service):
    # Setup: authorized, NOT in cache, client returns None
    telegram_service.client.is_user_authorized.return_value = True
    telegram_service.client.get_me.return_value = None

    with patch.object(telegram_service._cache, 'get', AsyncMock(return_value=None)) as mock_cache_get:
        with patch.object(telegram_service._cache, 'set', AsyncMock()) as mock_cache_set:
            result = await telegram_service.get_me()

            assert result is None
            mock_cache_get.assert_called_once_with("telegram_me")
            telegram_service.client.get_me.assert_called_once()
            # Verify it was NOT cached since it was None
            mock_cache_set.assert_not_called()
