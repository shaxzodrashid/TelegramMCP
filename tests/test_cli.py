import os
import stat
import pytest
from unittest.mock import patch
from telegram_mcp.cli import update_env_file

def test_update_env_file_creates_new_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    update_env_file("TEST_KEY", "test_value")

    env_path = tmp_path / ".env"
    assert env_path.exists()

    content = env_path.read_text()
    assert content == "TEST_KEY=test_value\n"

    # Check permissions (should be 0o600, owner read/write)
    st = os.stat(env_path)
    # The permissions might be masked by umask if os.chmod fails, but
    # update_env_file sets mode=0o600 in os.open and also explicitly calls os.chmod
    assert stat.S_IMODE(st.st_mode) == 0o600

def test_update_env_file_appends_to_existing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    env_path = tmp_path / ".env"
    env_path.write_text("EXISTING_KEY=123\n")

    update_env_file("TEST_KEY", "test_value")

    content = env_path.read_text()
    assert content == "EXISTING_KEY=123\nTEST_KEY=test_value\n"

def test_update_env_file_updates_existing_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    env_path = tmp_path / ".env"
    env_path.write_text("TEST_KEY=old_value\nOTHER_KEY=456\n")

    update_env_file("TEST_KEY", "new_value")

    content = env_path.read_text()
    assert content == "TEST_KEY=new_value\nOTHER_KEY=456\n"

def test_update_env_file_chmod_failure_handled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Mock os.chmod to raise an exception, verifying that update_env_file handles it gracefully
    with patch("os.chmod", side_effect=PermissionError("Mocked permission error")):
        update_env_file("TEST_KEY", "test_value")

    env_path = tmp_path / ".env"
    assert env_path.exists()
    content = env_path.read_text()
    assert content == "TEST_KEY=test_value\n"
