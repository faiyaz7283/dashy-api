"""Cache layer with TTL support and fail-open design.

Provides caching for weather and calendar data to reduce API calls.
Uses Redis for distributed caching with automatic fallback on failures.
"""

import contextlib
import json
from typing import Any

import redis.asyncio as redis
from pydantic import BaseModel

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheStats(BaseModel):
    """Cache statistics for monitoring."""

    hits: int = 0
    misses: int = 0
    errors: int = 0


class Cache:
    """Async cache with TTL support and fail-open design.

    Cache failures (connection errors, serialization errors) are logged
    but don't break the application - requests fall through to the data source.
    """

    def __init__(self, redis_url: str | None = None):
        """Initialize cache with Redis connection.

        Args:
            redis_url: Redis connection URL. Defaults to settings.REDIS_URL.
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._client: redis.Redis | None = None
        self._stats = CacheStats()

    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            logger.info("cache_connected", redis_url=self.redis_url)
        except Exception as e:
            logger.warning("cache_connection_failed", error=str(e))
            self._client = None

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            with contextlib.suppress(RuntimeError):
                # Event loop is closed, ignore
                await self._client.aclose()
            self._client = None
            logger.info("cache_disconnected")

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found/expired/error.
        """
        if not self._client:
            self._stats.misses += 1
            return None

        try:
            value = await self._client.get(key)
            if value is None:
                self._stats.misses += 1
                return None

            self._stats.hits += 1
            return json.loads(value)
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
            self._stats.errors += 1
            self._stats.misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key.
            value: Value to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds.
        """
        if not self._client:
            return

        try:
            serialized = json.dumps(value, default=str)
            await self._client.set(key, serialized, ex=ttl)
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))
            self._stats.errors += 1

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key.
        """
        if not self._client:
            return

        try:
            await self._client.delete(key)
        except Exception as e:
            logger.warning("cache_delete_failed", key=key, error=str(e))
            self._stats.errors += 1

    async def clear(self) -> None:
        """Clear all cache entries."""
        if not self._client:
            return

        try:
            await self._client.flushdb()
            logger.info("cache_cleared")
        except Exception as e:
            logger.warning("cache_clear_failed", error=str(e))
            self._stats.errors += 1

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Cache statistics (hits, misses, errors).
        """
        return self._stats

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._stats = CacheStats()

    @property
    def is_connected(self) -> bool:
        """Check if cache is connected.

        Returns:
            True if connected, False otherwise.
        """
        return self._client is not None


# Global cache instance
_cache: Cache | None = None


async def get_cache() -> Cache:
    """Get or create global cache instance.

    Returns:
        Cache instance.
    """
    global _cache
    if _cache is None:
        _cache = Cache()
        await _cache.connect()
    return _cache


async def close_cache() -> None:
    """Close global cache instance."""
    global _cache
    if _cache:
        await _cache.disconnect()
        _cache = None
