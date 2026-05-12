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
