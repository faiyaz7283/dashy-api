"""Tests for cache layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.cache import Cache, close_cache, get_cache
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
        cache.get_stats = MagicMock()
        cache.get_stats.return_value.hits = 0
        cache.get_stats.return_value.misses = 0
        cache.get_stats.return_value.errors = 0
        cache.is_connected = True
        return cache

    async def test_weather_route_uses_cache(self, mock_cache):
        """Test weather route checks cache before fetching."""
        # Provide a complete valid WeatherResponse structure
        mock_cache.get.return_value = {
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
                mock_cache.get.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_calendar_route_uses_cache(self, mock_cache):
        """Test calendar route checks cache before fetching."""
        mock_cache.get.return_value = {
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
                mock_cache.get.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_weather_route_caches_result(self, mock_cache):
        """Test weather route caches API result."""
        mock_cache.get.return_value = None  # Cache miss

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
                mock_cache.set.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    async def test_calendar_route_caches_result(self, mock_cache):
        """Test calendar route caches API result."""
        mock_cache.get.return_value = None  # Cache miss

        # Override the dependency
        from app.api.deps import get_redis_cache

        app.dependency_overrides[get_redis_cache] = lambda: mock_cache

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/calendar")

                assert response.status_code == 200
                mock_cache.set.assert_called_once()
        finally:
            app.dependency_overrides.clear()


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
