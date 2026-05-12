import os
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
