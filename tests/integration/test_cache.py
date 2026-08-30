"""Tests for cache layer."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.cache import Cache, RetryConfig, close_cache, get_cache
from app.core.exceptions import UpstreamServiceError
from app.main import app


class TestCache:
    """Test cache operations."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        client = AsyncMock()
        client.ping = AsyncMock()
        client.get = AsyncMock()
        client.set = AsyncMock()
        client.delete = AsyncMock()
        client.flushdb = AsyncMock()
        client.aclose = AsyncMock()
        return client

    @pytest.fixture
    def cache(self, mock_redis):
        """Create a cache instance with mock Redis."""
        cache = Cache()
        cache._client = mock_redis
        return cache

    async def test_cache_get_hit(self, cache, mock_redis):
        """Test cache get returns cached value."""
        mock_redis.get.return_value = '{"test": "data"}'

        result = await cache.get("test_key")

        assert result == {"test": "data"}
        mock_redis.get.assert_called_once_with("test_key")
        assert cache._stats.hits == 1
        assert cache._stats.misses == 0

    async def test_cache_get_miss(self, cache, mock_redis):
        """Test cache get returns None on miss."""
        mock_redis.get.return_value = None

        result = await cache.get("test_key")

        assert result is None
        mock_redis.get.assert_called_once_with("test_key")
        assert cache._stats.hits == 0
        assert cache._stats.misses == 1

    async def test_cache_set(self, cache, mock_redis):
        """Test cache set stores value with TTL."""
        await cache.set("test_key", {"test": "data"}, ttl=300)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "test_key"
        assert call_args[1]["ex"] == 300

    async def test_cache_delete(self, cache, mock_redis):
        """Test cache delete removes key."""
        await cache.delete("test_key")

        mock_redis.delete.assert_called_once_with("test_key")

    async def test_cache_fail_open_on_get_error(self, cache, mock_redis):
        """Test cache returns None on get error (fail-open)."""
        mock_redis.get.side_effect = Exception("Redis error")

        result = await cache.get("test_key")

        assert result is None
        assert cache._stats.errors == 1

    async def test_cache_fail_open_on_set_error(self, cache, mock_redis):
        """Test cache doesn't raise on set error (fail-open)."""
        mock_redis.set.side_effect = Exception("Redis error")

        # Should not raise
        await cache.set("test_key", {"test": "data"}, ttl=300)

        assert cache._stats.errors == 1

    async def test_cache_stats_tracking(self, cache, mock_redis):
        """Test cache tracks hit/miss/error statistics."""
        # Simulate various operations
        mock_redis.get.side_effect = [
            '{"data": 1}',  # hit
            None,  # miss
            '{"data": 2}',  # hit
        ]

        await cache.get("key1")
        await cache.get("key2")
        await cache.get("key3")

        stats = cache.get_stats()
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.errors == 0

    async def test_cache_clear(self, cache, mock_redis):
        """Test cache clear removes all keys."""
        await cache.clear()

        mock_redis.flushdb.assert_called_once()


class TestCacheIntegration:
    """Test cache integration with services."""

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache."""
        cache = AsyncMock(spec=Cache)
        cache.get = AsyncMock()
        cache.set = AsyncMock()
        cache.fetch = AsyncMock()
        cache.get_stats = MagicMock()
        cache.get_stats.return_value.hits = 0
        cache.get_stats.return_value.misses = 0
        cache.get_stats.return_value.errors = 0
        cache.is_connected = True
        return cache

    async def test_weather_route_uses_cache(self, mock_cache):
        """Test weather route uses cache.fetch() for SWR pattern."""
        # Provide a complete valid WeatherResponse structure
        mock_cache.fetch.return_value = {
            "current": {
                "temperature": 72,
                "feels_like": 75,
                "condition": "clear",
                "icon": "01d",
                "humidity": 50,
                "wind_speed": 5.0,
                "wind_direction": "NW",
                "pressure": 1013,
                "uv_index": 5,
                "visibility": 10000,
                "cloud_cover": 0,
            },
            "forecast": [],
        }

        # Override the dependency
        from app.api.deps import get_redis_cache

        app.dependency_overrides[get_redis_cache] = lambda: mock_cache

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/weather")

                assert response.status_code == 200
                mock_cache.fetch.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_calendar_route_uses_cache(self, mock_cache):
        """Test calendar route uses cache.fetch() for SWR pattern."""
        mock_cache.fetch.return_value = {
            "events": [],
            "week_start": "2026-01-01",
            "week_end": "2026-01-07",
        }

        # Override the dependency
        from app.api.deps import get_redis_cache

        app.dependency_overrides[get_redis_cache] = lambda: mock_cache

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/calendar")

                assert response.status_code == 200
                mock_cache.fetch.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_weather_route_caches_result(self, mock_cache):
        """Test weather route uses cache.fetch() which handles caching internally."""
        # Create a proper WeatherResponse object
        from app.api.models.weather import WeatherCurrent, WeatherResponse

        mock_weather_response = WeatherResponse(
            current=WeatherCurrent(
                temperature=72,
                feels_like=75,
                condition="clear",
                icon="01d",
                humidity=50,
                wind_speed=5.0,
                sunrise="06:00",
                sunset="20:00",
            ),
            forecast=[],
        )

        # Mock cache.fetch to return the dumped response
        mock_cache.fetch.return_value = mock_weather_response.model_dump()

        # Create a mock weather provider that returns valid data
        mock_weather_provider = AsyncMock()
        mock_weather_provider.get_weather.return_value = mock_weather_response

        # Override both dependencies
        from app.api.deps import get_redis_cache, get_weather_provider

        app.dependency_overrides[get_redis_cache] = lambda: mock_cache
        app.dependency_overrides[get_weather_provider] = lambda: mock_weather_provider

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/weather")

                assert response.status_code == 200
                # cache.fetch is called (it handles caching internally)
                mock_cache.fetch.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_calendar_route_caches_result(self, mock_cache):
        """Test calendar route uses cache.fetch() which handles caching internally."""
        mock_cache.fetch.return_value = {
            "events": [],
            "week_start": "2026-01-01",
            "week_end": "2026-01-07",
        }

        # Override the dependency
        from app.api.deps import get_redis_cache

        app.dependency_overrides[get_redis_cache] = lambda: mock_cache

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/calendar")

                assert response.status_code == 200
                # cache.fetch is called (it handles caching internally)
                mock_cache.fetch.assert_called_once()
        finally:
            app.dependency_overrides.clear()


class TestCacheFetch:
    """Test Cache.fetch() stale-while-revalidate pattern."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        client = AsyncMock()
        client.ping = AsyncMock()
        client.get = AsyncMock()
        client.set = AsyncMock()
        client.delete = AsyncMock()
        client.flushdb = AsyncMock()
        client.aclose = AsyncMock()
        return client

    @pytest.fixture
    def cache(self, mock_redis):
        """Create a cache instance with mock Redis."""
        cache = Cache()
        cache._client = mock_redis
        return cache

    async def test_fetch_returns_fresh_cache(self, cache, mock_redis):
        """Test fetch returns fresh cache without calling fetcher."""
        mock_redis.get.side_effect = [json.dumps({"fresh": "data"}), None]
        fetcher = AsyncMock()

        result = await cache.fetch("test", fetcher, fresh_ttl=60, stale_ttl=3600)

        assert result == {"fresh": "data"}
        fetcher.assert_not_called()
        mock_redis.set.assert_not_called()

    async def test_fetch_returns_stale_cache_when_fresh_missing(self, cache, mock_redis):
        """Test fetch returns stale cache when fresh is missing."""
        # First call (fresh) returns None, second call (stale) returns data
        mock_redis.get.side_effect = [None, json.dumps({"stale": "data"})]
        fetcher = AsyncMock()

        result = await cache.fetch("test", fetcher, fresh_ttl=60, stale_ttl=3600)

        assert result == {"stale": "data"}
        fetcher.assert_not_called()
        mock_redis.set.assert_not_called()

    async def test_fetch_calls_fetcher_when_no_cache(self, cache, mock_redis):
        """Test fetch calls fetcher and writes both fresh and stale keys."""
        # Both fresh and stale cache miss
        mock_redis.get.side_effect = [None, None]
        fetcher = AsyncMock(return_value={"fresh": "data"})

        result = await cache.fetch(
            "test",
            fetcher,
            fresh_ttl=60,
            stale_ttl=3600,
            service_name="test-service",
        )

        assert result == {"fresh": "data"}
        fetcher.assert_called_once()
        # Verify both keys were written
        assert mock_redis.set.call_count == 2
        calls = mock_redis.set.call_args_list
        assert calls[0][0][0] == "test:fresh"
        assert calls[0][1]["ex"] == 60
        assert calls[1][0][0] == "test:stale"
        assert calls[1][1]["ex"] == 3600

    async def test_fetch_retries_on_transient_error(self, cache, mock_redis):
        """Test fetch retries on transient errors and succeeds."""
        mock_redis.get.side_effect = [None, None]
        # Fail twice with transient error, then succeed
        fetcher = AsyncMock(
            side_effect=[
                ConnectionError("Connection refused"),
                TimeoutError("Timeout"),
                {"fresh": "data"},
            ]
        )
        retry_config = RetryConfig(
            max_attempts=3,
            backoff_seconds=[0.01, 0.01],  # Fast backoff for tests
            transient_errors=(ConnectionError, TimeoutError),
        )

        result = await cache.fetch(
            "test",
            fetcher,
            fresh_ttl=60,
            stale_ttl=3600,
            retry_config=retry_config,
        )

        assert result == {"fresh": "data"}
        assert fetcher.call_count == 3
        assert mock_redis.set.call_count == 2

    async def test_fetch_raises_after_all_retries_fail(self, cache, mock_redis):
        """Test fetch raises UpstreamServiceError after all retries fail."""
        mock_redis.get.side_effect = [None, None]
        fetcher = AsyncMock(side_effect=ConnectionError("Connection refused"))
        retry_config = RetryConfig(
            max_attempts=3,
            backoff_seconds=[0.01, 0.01],
            transient_errors=(ConnectionError,),
        )

        with pytest.raises(UpstreamServiceError) as exc_info:
            await cache.fetch(
                "test",
                fetcher,
                fresh_ttl=60,
                stale_ttl=3600,
                retry_config=retry_config,
                service_name="test-service",
            )

        assert "test-service unavailable after 3 attempts" in str(exc_info.value)
        assert exc_info.value.service_name == "test-service"
        assert fetcher.call_count == 3
        mock_redis.set.assert_not_called()

    async def test_fetch_raises_immediately_on_non_transient_error(self, cache, mock_redis):
        """Test fetch raises immediately on non-transient errors without retry."""
        mock_redis.get.side_effect = [None, None]

        class PermanentError(Exception):
            pass

        fetcher = AsyncMock(side_effect=PermanentError("Auth failed"))
        retry_config = RetryConfig(
            max_attempts=3,
            backoff_seconds=[0.01, 0.01],
            transient_errors=(ConnectionError,),  # PermanentError not in list
        )

        with pytest.raises(UpstreamServiceError) as exc_info:
            await cache.fetch(
                "test",
                fetcher,
                fresh_ttl=60,
                stale_ttl=3600,
                retry_config=retry_config,
            )

        assert "Auth failed" in str(exc_info.value)
        assert fetcher.call_count == 1  # No retries
        mock_redis.set.assert_not_called()

    async def test_fetch_uses_default_retry_config(self, cache, mock_redis):
        """Test fetch uses default RetryConfig when none provided."""
        mock_redis.get.side_effect = [None, None]
        fetcher = AsyncMock(return_value={"data": "value"})

        result = await cache.fetch("test", fetcher, fresh_ttl=60, stale_ttl=3600)

        assert result == {"data": "value"}
        assert fetcher.call_count == 1


class TestCacheLifecycle:
    """Test cache lifecycle management."""

    async def test_get_cache_creates_singleton(self):
        """Test get_cache returns the same instance."""
        # Close any existing cache
        await close_cache()

        cache1 = await get_cache()
        cache2 = await get_cache()

        assert cache1 is cache2

        # Cleanup
        await close_cache()

    async def test_close_cache_disconnects(self):
        """Test close_cache properly disconnects."""
        cache = await get_cache()
        await close_cache()

        # Getting cache again should create new instance
        cache2 = await get_cache()
        assert cache2 is not cache

        # Cleanup
        await close_cache()
