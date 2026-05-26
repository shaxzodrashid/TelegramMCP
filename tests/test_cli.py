import os
from telegram_mcp.cli import update_env_file

def test_update_env_file_creates_new(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    update_env_file("TEST_KEY", "test_value")

    env_path = tmp_path / ".env"
    assert env_path.exists()
    assert env_path.read_text() == "TEST_KEY=test_value\n"

    # Check permissions
    st = os.stat(env_path)
    assert oct(st.st_mode)[-3:] == "600"

def test_update_env_file_appends_to_existing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env_path = tmp_path / ".env"
    env_path.write_text("OTHER_KEY=other_value\n")

    update_env_file("TEST_KEY", "test_value")

    content = env_path.read_text()
    assert "OTHER_KEY=other_value\n" in content
    assert "TEST_KEY=test_value\n" in content

def test_update_env_file_updates_existing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env_path = tmp_path / ".env"
    env_path.write_text("TEST_KEY=old_value\nOTHER_KEY=other_value\n")

    update_env_file("TEST_KEY", "new_value")

    content = env_path.read_text()
    assert "TEST_KEY=new_value\n" in content
    assert "TEST_KEY=old_value\n" not in content
    assert "OTHER_KEY=other_value\n" in content

import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_logout_flow_server_side_revoke(tmp_path, monkeypatch):
    from telegram_mcp.cli import logout_flow
    from telegram_mcp.core.config import settings
    monkeypatch.chdir(tmp_path)

    session_file = tmp_path / f"{settings.SESSION_NAME}.session"
    session_file.write_text("dummy session")

    monkeypatch.setattr(settings, "API_ID", 12345)
    monkeypatch.setattr(settings, "API_HASH", "secret")

    with patch("telegram_mcp.cli.TelegramClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.is_user_authorized.return_value = True

        await logout_flow()

        mock_client.connect.assert_called_once()
        mock_client.log_out.assert_called_once()
        mock_client.disconnect.assert_called_once()

        assert not session_file.exists()

@pytest.mark.asyncio
async def test_logout_flow_fallback_if_unauthorized(tmp_path, monkeypatch):
    from telegram_mcp.cli import logout_flow
    from telegram_mcp.core.config import settings
    monkeypatch.chdir(tmp_path)

    session_file = tmp_path / f"{settings.SESSION_NAME}.session"
    session_file.write_text("dummy session")

    monkeypatch.setattr(settings, "API_ID", 12345)
    monkeypatch.setattr(settings, "API_HASH", "secret")

    with patch("telegram_mcp.cli.TelegramClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.is_user_authorized.return_value = False

        await logout_flow()

        mock_client.connect.assert_called_once()
        mock_client.log_out.assert_not_called()
        mock_client.disconnect.assert_called_once()

        assert not session_file.exists()
