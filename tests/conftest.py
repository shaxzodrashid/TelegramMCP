import pytest


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("API_ID", "12345")
    monkeypatch.setenv("API_HASH", "mock_hash")
    monkeypatch.setenv("SESSION_NAME", "test_session")
