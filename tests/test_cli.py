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
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_logout_flow_authorized(tmp_path, monkeypatch):
    from telegram_mcp.cli import _perform_logout
    from telegram_mcp.core.config import settings

    monkeypatch.chdir(tmp_path)
    session_name = "test_logout"
    settings.SESSION_NAME = session_name

    session_file = tmp_path / f"{session_name}.session"
    session_file.write_text("dummy")

    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True

    with patch("telegram_mcp.cli.TelegramClient", return_value=mock_client):
        with patch("telegram_mcp.cli.console.print") as mock_print:
            await _perform_logout()

            mock_client.connect.assert_called_once()
            mock_client.is_user_authorized.assert_called_once()
            mock_client.log_out.assert_called_once()
            mock_print.assert_called_with("[bold green]Successfully logged out from server and session file deleted.[/bold green]")

@pytest.mark.asyncio
async def test_logout_flow_not_authorized(tmp_path, monkeypatch):
    from telegram_mcp.cli import _perform_logout
    from telegram_mcp.core.config import settings

    monkeypatch.chdir(tmp_path)
    session_name = "test_logout_not_auth"
    settings.SESSION_NAME = session_name

    session_file = tmp_path / f"{session_name}.session"
    session_file.write_text("dummy")

    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = False

    with patch("telegram_mcp.cli.TelegramClient", return_value=mock_client):
        with patch("telegram_mcp.cli.console.print") as mock_print:
            await _perform_logout()

            mock_client.connect.assert_called_once()
            mock_client.is_user_authorized.assert_called_once()
            mock_client.disconnect.assert_called_once()
            mock_client.log_out.assert_not_called()

            # Local file should be deleted
            assert not session_file.exists()
            mock_print.assert_called_with("[bold green]Session file deleted locally (was not authorized).[/bold green]")

@pytest.mark.asyncio
async def test_logout_flow_exception_fallback(tmp_path, monkeypatch):
    from telegram_mcp.cli import _perform_logout
    from telegram_mcp.core.config import settings

    monkeypatch.chdir(tmp_path)
    session_name = "test_logout_exc"
    settings.SESSION_NAME = session_name

    session_file = tmp_path / f"{session_name}.session"
    session_file.write_text("dummy")

    mock_client = AsyncMock()
    mock_client.connect.side_effect = Exception("Network Error")
    mock_client.is_connected = MagicMock(return_value=False)

    with patch("telegram_mcp.cli.TelegramClient", return_value=mock_client):
        with patch("telegram_mcp.cli.console.print") as mock_print:
            await _perform_logout()

            # Local file should be deleted despite exception
            assert not session_file.exists()
            mock_print.assert_called_with("[bold yellow]Failed to logout from server (Network Error), but local session file deleted.[/bold yellow]")

@pytest.mark.asyncio
async def test_logout_flow_no_session_file(tmp_path, monkeypatch):
    from telegram_mcp.cli import _perform_logout
    from telegram_mcp.core.config import settings

    monkeypatch.chdir(tmp_path)
    session_name = "test_logout_no_file"
    settings.SESSION_NAME = session_name

    # Do not create session file

    with patch("telegram_mcp.cli.TelegramClient") as mock_client_cls:
        with patch("telegram_mcp.cli.console.print") as mock_print:
            await _perform_logout()

            mock_client_cls.assert_not_called()
            mock_print.assert_called_with("[yellow]No active session found.[/yellow]")
