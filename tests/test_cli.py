import os
from unittest.mock import AsyncMock, patch

import pytest

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


@pytest.mark.asyncio
async def test_logout_flow_authorized_revokes_server_session(tmp_path, monkeypatch):
    from telegram_mcp.cli import _logout_flow
    from telegram_mcp.core.config import settings

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "SESSION_NAME", "test_logout")
    monkeypatch.setattr(settings, "API_ID", 12345)
    monkeypatch.setattr(settings, "API_HASH", "test_hash")

    session_file = tmp_path / "test_logout.session"
    session_file.write_text("dummy")

    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = True

    with patch("telegram_mcp.cli.TelegramClient", return_value=mock_client):
        with patch("telegram_mcp.cli.console.print"):
            await _logout_flow()

    mock_client.connect.assert_called_once()
    mock_client.is_user_authorized.assert_called_once()
    mock_client.log_out.assert_called_once()
    mock_client.disconnect.assert_called_once()
    assert not session_file.exists()


@pytest.mark.asyncio
async def test_logout_flow_not_authorized_deletes_local_session(tmp_path, monkeypatch):
    from telegram_mcp.cli import _logout_flow
    from telegram_mcp.core.config import settings

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "SESSION_NAME", "test_logout_not_auth")
    monkeypatch.setattr(settings, "API_ID", 12345)
    monkeypatch.setattr(settings, "API_HASH", "test_hash")

    session_file = tmp_path / "test_logout_not_auth.session"
    session_file.write_text("dummy")

    mock_client = AsyncMock()
    mock_client.is_user_authorized.return_value = False

    with patch("telegram_mcp.cli.TelegramClient", return_value=mock_client):
        with patch("telegram_mcp.cli.console.print"):
            await _logout_flow()

    mock_client.connect.assert_called_once()
    mock_client.is_user_authorized.assert_called_once()
    mock_client.log_out.assert_not_called()
    mock_client.disconnect.assert_called_once()
    assert not session_file.exists()


@pytest.mark.asyncio
async def test_logout_flow_exception_fallback_deletes_local_session(tmp_path, monkeypatch):
    from telegram_mcp.cli import _logout_flow
    from telegram_mcp.core.config import settings

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "SESSION_NAME", "test_logout_exc")
    monkeypatch.setattr(settings, "API_ID", 12345)
    monkeypatch.setattr(settings, "API_HASH", "test_hash")

    session_file = tmp_path / "test_logout_exc.session"
    session_file.write_text("dummy")

    mock_client = AsyncMock()
    mock_client.connect.side_effect = Exception("Network Error")

    with patch("telegram_mcp.cli.TelegramClient", return_value=mock_client):
        with patch("telegram_mcp.cli.console.print"):
            await _logout_flow()

    mock_client.connect.assert_called_once()
    mock_client.disconnect.assert_called_once()
    assert not session_file.exists()


@pytest.mark.asyncio
async def test_logout_flow_missing_credentials_deletes_local_only(tmp_path, monkeypatch):
    from telegram_mcp.cli import _logout_flow
    from telegram_mcp.core.config import settings

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "SESSION_NAME", "test_logout_missing_creds")
    monkeypatch.setattr(settings, "API_ID", 0)
    monkeypatch.setattr(settings, "API_HASH", "placeholder")

    session_file = tmp_path / "test_logout_missing_creds.session"
    session_file.write_text("dummy")

    with patch("telegram_mcp.cli.TelegramClient") as mock_client_cls:
        with patch("telegram_mcp.cli.console.print"):
            await _logout_flow()

    mock_client_cls.assert_not_called()
    assert not session_file.exists()


@pytest.mark.asyncio
async def test_logout_flow_no_session_file(tmp_path, monkeypatch):
    from telegram_mcp.cli import _logout_flow
    from telegram_mcp.core.config import settings

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "SESSION_NAME", "test_logout_no_file")

    with patch("telegram_mcp.cli.TelegramClient") as mock_client_cls:
        with patch("telegram_mcp.cli.console.print") as mock_print:
            await _logout_flow()

    mock_client_cls.assert_not_called()
    mock_print.assert_called_with("[yellow]No active session found.[/yellow]")


def test_logout_command_requires_confirmation_before_running_flow(monkeypatch):
    from telegram_mcp.cli import logout

    monkeypatch.setattr("telegram_mcp.cli.typer.confirm", lambda _: False)

    with patch("telegram_mcp.cli.asyncio.run") as mock_run:
        logout()

    mock_run.assert_not_called()


def test_logout_command_runs_secure_flow_after_confirmation(monkeypatch):
    from telegram_mcp.cli import logout

    sentinel_flow = object()
    monkeypatch.setattr("telegram_mcp.cli.typer.confirm", lambda _: True)
    monkeypatch.setattr("telegram_mcp.cli._logout_flow", lambda: sentinel_flow)

    with patch("telegram_mcp.cli.asyncio.run") as mock_run:
        logout()

    mock_run.assert_called_once_with(sentinel_flow)

@pytest.mark.asyncio
async def test_logout_flow_handles_rich_markup_injection(tmp_path, monkeypatch):
    from telegram_mcp.cli import _logout_flow
    from telegram_mcp.core.config import settings
    from rich.errors import MarkupError

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "SESSION_NAME", "test_logout_markup")
    monkeypatch.setattr(settings, "API_ID", 12345)
    monkeypatch.setattr(settings, "API_HASH", "test_hash")

    session_file = tmp_path / "test_logout_markup.session"
    session_file.write_text("dummy")

    mock_client = AsyncMock()
    # Provide an exception with a string that triggers MarkupError if unescaped
    mock_client.connect.side_effect = Exception("Network Error [/]")

    with patch("telegram_mcp.cli.TelegramClient", return_value=mock_client):
        try:
            await _logout_flow()
        except MarkupError:
            pytest.fail("MarkupError was raised. Exception message was not properly escaped.")

    mock_client.connect.assert_called_once()
    assert not session_file.exists()
