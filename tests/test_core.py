import pytest
from telegram_mcp.core.cache import cache
from telegram_mcp.core.logger import logger

import time
from unittest.mock import patch

@pytest.mark.asyncio
async def test_cache():
    await cache.set("test_key", "test_value", ttl=1)
    value = await cache.get("test_key")
    assert value == "test_value"
    
    await cache.delete("test_key")
    value = await cache.get("test_key")
    assert value is None

@pytest.mark.asyncio
async def test_cache_expiry():
    # Test setting without TTL
    await cache.set("no_ttl_key", "no_ttl_value")
    assert await cache.get("no_ttl_key") == "no_ttl_value"

    # Test setting with TTL
    await cache.set("expiry_key", "expiry_value", ttl=1)
    assert await cache.get("expiry_key") == "expiry_value"

    # Mock time to simulate time passing beyond TTL
    with patch("telegram_mcp.core.cache.time.time", return_value=time.time() + 2):
        assert await cache.get("expiry_key") is None
        # Verify the no_ttl_key is unaffected
        assert await cache.get("no_ttl_key") == "no_ttl_value"

    await cache.clear()

def test_logger():
    # Just verify it doesn't crash
    logger.info("Testing logger")
    assert True

def test_is_suspicious_bypass():
    from telegram_mcp.core.file_utils import is_suspicious

    # Check trailing space bypass attempt
    suspicious, ext = is_suspicious("evil.exe ")
    assert suspicious is True
    assert ext == ".exe"

    # Check trailing period bypass attempt
    suspicious, ext = is_suspicious("evil.exe.")
    assert suspicious is True
    assert ext == ".exe"

    # Normal malicious
    suspicious, ext = is_suspicious("evil.exe")
    assert suspicious is True
    assert ext == ".exe"

    # Double extension malicious
    suspicious, ext = is_suspicious("evil.pdf.exe")
    assert suspicious is True
    assert ext == ".exe"

    # Safe file
    suspicious, ext = is_suspicious("good.pdf")
    assert suspicious is False
    assert ext == ".pdf"

def test_is_suspicious_bypass_alternating():
    from telegram_mcp.core.file_utils import is_suspicious

    # Check alternating bypass attempt
    suspicious, ext = is_suspicious("evil.exe .")
    assert suspicious is True
    assert ext == ".exe"

    suspicious, ext = is_suspicious("evil.exe. ")
    assert suspicious is True
    assert ext == ".exe"


def test_is_suspicious_leading_dot():
    from telegram_mcp.core.file_utils import is_suspicious

    suspicious, ext = is_suspicious(".exe")
    assert suspicious is True
    assert ext == ".exe"

    suspicious, ext = is_suspicious(" .exe")
    assert suspicious is True
    assert ext == ".exe"

def test_is_suspicious_control_char_bypass():
    from telegram_mcp.core.file_utils import is_suspicious

    # Control character bypass attempt using left-to-right mark (U+200E)
    suspicious, ext = is_suspicious("evil.exe\u200e")
    assert suspicious is True
    assert ext == ".exe"

    # With unsafe characters
    suspicious, ext = is_suspicious("evil?.exe")
    assert suspicious is True
    assert ext == ".exe"
