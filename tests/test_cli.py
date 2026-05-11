import os
import pytest
from telegram_mcp.cli import update_env_file

def test_update_env_file_sanitizes_newlines(tmp_path, monkeypatch):
    # Change working directory to a temporary path where a mock .env will be created
    monkeypatch.chdir(tmp_path)

    # Write initial .env file
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING_VAR=hello\n")

    # Try to inject a new variable through a newline
    malicious_value = "myvalue\nINJECTED_VAR=hacked"
    update_env_file("SAFE_VAR", malicious_value)

    # Read the content
    content = env_file.read_text()

    # Verify the value was sanitized and no new line was injected
    assert "SAFE_VAR=myvaluemyvalue\n" not in content  # shouldn't be duplicate myvalue, should just have newline removed
    assert "\nINJECTED_VAR=hacked" not in content

    # Verify the actual resulting value
    assert "SAFE_VAR=myvalueINJECTED_VAR=hacked" in content
    assert "EXISTING_VAR=hello" in content
