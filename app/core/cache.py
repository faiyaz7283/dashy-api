"""Cache layer with TTL support and fail-open design.

Provides caching for weather and calendar data to reduce API calls.
Uses Redis for distributed caching with automatic fallback on failures.
"""

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import redis.asyncio as redis
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import UpstreamServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior with exponential backoff.

    Attributes:
        max_attempts: Maximum number of retry attempts (including initial attempt).
        backoff_seconds: List of delay seconds between attempts. Length should be max_attempts - 1.
        transient_errors: Tuple of exception types that are considered transient and worth retrying.
    """

    max_attempts: int = 3
    backoff_seconds: list[float] = field(default_factory=lambda: [1.0, 2.0, 4.0])
    transient_errors: tuple[type[Exception], ...] = (ConnectionError, TimeoutError, OSError)


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

    async def get_with_metadata(self, key: str) -> dict[str, Any] | None:
        """Get value from cache with metadata (TTL remaining).

        Args:
            key: Cache key.

        Returns:
            Dict with 'value', 'ttl_remaining', and 'created_at' keys, or None if not found.
        """
        if not self._client:
            return None

        try:
            # Get value and TTL in parallel
            value, ttl = await asyncio.gather(
                self._client.get(key),
                self._client.ttl(key),
            )

            if value is None:
                return None

            # TTL is in seconds, -2 means key doesn't exist, -1 means no expiry
            ttl_remaining = ttl if ttl > 0 else 0

            return {
                "value": json.loads(value),
                "ttl_remaining": ttl_remaining,
            }
        except Exception as e:
            logger.warning("cache_get_with_metadata_failed", key=key, error=str(e))
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

    async def fetch(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
        fresh_ttl: int,
        stale_ttl: int,
        retry_config: RetryConfig | None = None,
        service_name: str = "upstream",
    ) -> Any:
        """Fetch data with stale-while-revalidate pattern and retry logic.

        Implements the SWR pattern: check fresh cache → check stale cache → fetch with retry.
        On successful fetch, writes both fresh and stale cache keys.

        Args:
            key: Base cache key (will be suffixed with :fresh and :stale).
            fetcher: Async callable that fetches fresh data from the source.
            fresh_ttl: TTL in seconds for the fresh cache entry.
            stale_ttl: TTL in seconds for the stale cache entry (longer than fresh_ttl).
            retry_config: Retry configuration. Defaults to RetryConfig() if None.
            service_name: Name of the upstream service for error reporting.

        Returns:
            Fresh or stale cached data, or freshly fetched data.

        Raises:
            UpstreamServiceError: When all retry attempts fail and no stale cache exists.
        """
        if retry_config is None:
            retry_config = RetryConfig()

        fresh_key = f"{key}:fresh"
        stale_key = f"{key}:stale"

        # 1. Check fresh cache
        fresh_data = await self.get(fresh_key)
        if fresh_data is not None:
            return fresh_data

        # 2. Check stale cache
        stale_data = await self.get(stale_key)
        if stale_data is not None:
            logger.warning(
                "serving_stale_data",
                key=key,
                service_name=service_name,
                msg="Fresh cache expired, serving stale data",
            )
            # Trigger background refresh (don't wait for it)
            asyncio.create_task(
                self._background_refresh(key, fetcher, fresh_ttl, stale_ttl, retry_config, service_name)
            )
            return stale_data

        # 3. Fetch with retry
        last_error: Exception | None = None
        for attempt in range(retry_config.max_attempts):
            try:
                result = await fetcher()

                # Write both fresh and stale cache entries
                await self.set(fresh_key, result, fresh_ttl)
                await self.set(stale_key, result, stale_ttl)

                logger.info(
                    "cache_fetch_success",
                    key=key,
                    service_name=service_name,
                    attempt=attempt + 1,
                )
                return result

            except retry_config.transient_errors as e:
                last_error = e
                logger.warning(
                    "cache_fetch_retry",
                    key=key,
                    service_name=service_name,
                    attempt=attempt + 1,
                    max_attempts=retry_config.max_attempts,
                    error=str(e),
                )

                # Wait before next retry (if not the last attempt)
                if attempt < retry_config.max_attempts - 1:
                    delay = (
                        retry_config.backoff_seconds[attempt]
                        if attempt < len(retry_config.backoff_seconds)
                        else retry_config.backoff_seconds[-1]
                    )
                    await asyncio.sleep(delay)

            except Exception as e:
                # Non-transient error — don't retry
                logger.error(
                    "cache_fetch_non_transient_error",
                    key=key,
                    service_name=service_name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise UpstreamServiceError(
                    f"{service_name} request failed: {e}",
                    service_name=service_name,
                    detail=str(e),
                ) from e

        # 4. All retries failed
        logger.error(
            "cache_fetch_all_retries_failed",
            key=key,
            service_name=service_name,
            max_attempts=retry_config.max_attempts,
            error=str(last_error) if last_error else "unknown",
        )
        raise UpstreamServiceError(
            f"{service_name} unavailable after {retry_config.max_attempts} attempts",
            service_name=service_name,
            detail=str(last_error) if last_error else None,
        ) from last_error

    async def _background_refresh(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
        fresh_ttl: int,
        stale_ttl: int,
        retry_config: RetryConfig,
        service_name: str,
    ) -> None:
        """Background task to refresh stale cache data.

        This is triggered when serving stale data to ensure fresh data is fetched
        for the next request. Errors are logged but don't affect the current request.

        Args:
            key: Base cache key.
            fetcher: Async callable that fetches fresh data.
            fresh_ttl: TTL for fresh cache entry.
            stale_ttl: TTL for stale cache entry.
            retry_config: Retry configuration.
            service_name: Name of the upstream service.
        """
        fresh_key = f"{key}:fresh"
        stale_key = f"{key}:stale"

        try:
            result = await fetcher()
            await self.set(fresh_key, result, fresh_ttl)
            await self.set(stale_key, result, stale_ttl)
            logger.info(
                "background_refresh_success",
                key=key,
                service_name=service_name,
            )
        except Exception as e:
            logger.warning(
                "background_refresh_failed",
                key=key,
                service_name=service_name,
                error=str(e),
            )

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
