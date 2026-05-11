import pytest
from telegram_mcp.core.cache import cache
from telegram_mcp.core.logger import logger

@pytest.mark.asyncio
async def test_cache():
    await cache.set("test_key", "test_value", ttl=1)
    value = await cache.get("test_key")
    assert value == "test_value"
    
    await cache.delete("test_key")
    value = await cache.get("test_key")
    assert value is None

@pytest.mark.asyncio
async def test_cache_clear():
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")

    assert await cache.get("key1") == "value1"
    assert await cache.get("key2") == "value2"

    await cache.clear()

    assert await cache.get("key1") is None
    assert await cache.get("key2") is None

def test_logger():
    # Just verify it doesn't crash
    logger.info("Testing logger")
    assert True
