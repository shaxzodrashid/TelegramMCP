import time
from typing import Any, Dict, Optional, TypeVar

T = TypeVar("T")


class AsyncCache:
    """
    A simple in-memory cache with TTL (Time To Live).
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None

        item = self._cache[key]
        if item["expiry"] and item["expiry"] < time.time():
            del self._cache[key]
            return None

        return item["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        expiry = time.time() + ttl if ttl else None
        self._cache[key] = {"value": value, "expiry": expiry}

    async def delete(self, key: str):
        if key in self._cache:
            del self._cache[key]

    async def clear(self):
        self._cache.clear()


# Global cache instance
cache = AsyncCache()

__all__ = ["cache", "AsyncCache"]
