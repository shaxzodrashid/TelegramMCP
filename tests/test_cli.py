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


from unittest.mock import AsyncMock, patch
from telegram_mcp.cli import logout

def test_logout_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session_file = tmp_path / "test_session.session"
    session_file.write_text("dummy")

    with patch("telegram_mcp.cli.typer.confirm", return_value=True), \
         patch("telegram_mcp.cli.settings.SESSION_NAME", "test_session"), \
         patch("telegram_mcp.cli.TelegramClient") as mock_client_cls:

        mock_client = AsyncMock()
        mock_client.is_connected = lambda: True
        mock_client_cls.return_value = mock_client

        logout()

        mock_client.connect.assert_called_once()
        mock_client.log_out.assert_called_once()
        mock_client.disconnect.assert_called_once()

def test_logout_fallback(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session_file = tmp_path / "test_session.session"
    session_file.write_text("dummy")

    with patch("telegram_mcp.cli.typer.confirm", return_value=True), \
         patch("telegram_mcp.cli.settings.SESSION_NAME", "test_session"), \
         patch("telegram_mcp.cli.TelegramClient") as mock_client_cls:

        mock_client = AsyncMock()
        mock_client.log_out.side_effect = Exception("Network Error")
        mock_client.is_connected = lambda: True
        mock_client_cls.return_value = mock_client

        logout()

        mock_client.connect.assert_called_once()
        mock_client.log_out.assert_called_once()
        mock_client.disconnect.assert_called_once()

        # Check fallback deleted the file
        assert not session_file.exists()
