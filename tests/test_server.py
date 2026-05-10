import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from telegram_mcp.server import get_account_info

@pytest.fixture
def mock_telegram_service():
    with patch('telegram_mcp.server.telegram_service') as mock:
        yield mock

@pytest.mark.asyncio
async def test_get_account_info_success(mock_telegram_service):
    # Mock user
    me = MagicMock()
    me.first_name = "John"
    me.username = "johndoe"
    me.id = 12345

    mock_telegram_service.get_me = AsyncMock(return_value=me)

    result = await get_account_info()
    assert result == "Logged in as: John (@johndoe) [ID: 12345]"

@pytest.mark.asyncio
async def test_get_account_info_success_no_username(mock_telegram_service):
    # Mock user
    me = MagicMock()
    me.first_name = "John"
    me.username = None
    me.id = 12345

    mock_telegram_service.get_me = AsyncMock(return_value=me)

    result = await get_account_info()
    assert result == "Logged in as: John (@N/A) [ID: 12345]"

@pytest.mark.asyncio
async def test_get_account_info_not_logged_in(mock_telegram_service):
    mock_telegram_service.get_me = AsyncMock(return_value=None)

    result = await get_account_info()
    assert result == "Not logged in to Telegram. Use the 'telegram-mcp auth' command to authenticate."

@pytest.mark.asyncio
async def test_get_account_info_exception(mock_telegram_service):
    mock_telegram_service.get_me = AsyncMock(side_effect=Exception("API Error"))

    result = await get_account_info()
    assert result == "An error occurred while getting account info."
