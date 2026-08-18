---
name: add-cache-layer
description: Add Redis caching to an API endpoint — implement cache-aside pattern with TTL and fail-open design.
---

# Add Cache Layer

Add Redis caching to an API endpoint to reduce API calls and improve performance.

## When to use

- Adding caching to a new endpoint that calls external APIs
- Endpoint makes frequent external API calls (weather, calendar, etc.)
- Not for database caching — that's handled by repositories

## Prerequisites

- Redis service running (configured via Docker Compose in the orchestrator)
- `Cache` class exists in `app/core/cache.py`
- Endpoint exists and is working without caching

## Steps

### 1. Add cache dependency to route

Edit `app/api/routes/<domain>.py`:

```python
from fastapi import APIRouter, Depends
from app.api.deps import CacheDep, ProviderDep
from app.config import settings

router = APIRouter(prefix="/<domain>", tags=["<domain>"])


@router.get("", response_model=<Domain>Response)
async def get_<domain>(
    provider: ProviderDep,
    cache: CacheDep,  # Add cache dependency
) -> <Domain>Response:
    """Get <domain> data with caching.

    Args:
        provider: Injected data provider.
        cache: Injected cache instance.

    Returns:
        <Domain>Response with data.
    """
    # Generate cache key
    cache_key = "<domain>:all"

    # Try cache first
    cached = await cache.get(cache_key)
    if cached is not None:
        return <Domain>Response(**cached)

    # Fetch from provider
    try:
        result = await provider.get_data()

        # Cache the result
        await cache.set(
            cache_key,
            result.model_dump(),
            settings.<DOMAIN>_CACHE_TTL
        )

        return result

    except Exception as e:
        # Fail-open: return cached data on error if available
        logger.error("<domain>_fetch_failed", error=str(e))
        raise
```

### 2. Define cache TTL in settings

Edit `app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings

    # Cache TTLs (in seconds)
    WEATHER_CACHE_TTL: int = 600  # 10 minutes
    CALENDAR_CACHE_TTL: int = 120  # 2 minutes
    <DOMAIN>_CACHE_TTL: int = 300  # 5 minutes (example)
```

Add to `.env.example`:

```bash
# Cache TTLs
WEATHER_CACHE_TTL=600
CALENDAR_CACHE_TTL=120
<DATABASE>_CACHE_TTL=300
```

### 3. Design cache key strategy

Cache keys should be unique per query parameters:

```python
# Simple key (no parameters)
cache_key = "<domain>:all"

# Key with parameters
cache_key = f"<domain>:{param1}:{param2}"

# Example: Weather with units
cache_key = f"weather:{units}"  # "weather:imperial"

# Example: Calendar with date range
cache_key = f"calendar:{start_date}:{end_date}"

# Example: Family member by ID
cache_key = f"family:{member_id}"
```

**Rules:**
- Use colons as separators
- Include all query parameters that affect the response
- Keep keys readable for debugging

### 4. Implement fail-open design

Cache failures should never break the endpoint:

```python
@router.get("", response_model=<Domain>Response)
async def get_<domain>(
    provider: ProviderDep,
    cache: CacheDep,
) -> <Domain>Response:
    """Get <domain> data with fail-open caching."""
    cache_key = "<domain>:all"

    # Try cache (fail-open)
    try:
        cached = await cache.get(cache_key)
        if cached is not None:
            return <Domain>Response(**cached)
    except Exception as e:
        logger.warning("cache_get_failed", error=str(e))
        # Continue to provider

    # Fetch from provider
    result = await provider.get_data()

    # Cache result (fail-open)
    try:
        await cache.set(cache_key, result.model_dump(), settings.<DOMAIN>_CACHE_TTL)
    except Exception as e:
        logger.warning("cache_set_failed", error=str(e))
        # Don't raise — endpoint still works

    return result
```

**Why fail-open?** If Redis is down, the endpoint should still work (just slower).

### 5. Add cache invalidation (if needed)

For mutable data, invalidate cache on updates:

```python
@router.put("/{id}", response_model=<Domain>Response)
async def update_<domain>(
    id: str,
    request: Update<Domain>Request,
    repository: <Domain>RepositoryDep,
    cache: CacheDep,
) -> <Domain>Response:
    """Update <domain> and invalidate cache."""
    # Update data
    entity = await repository.get_by_id(id)
    # ... update logic
    await repository.save(entity)

    # Invalidate cache
    cache_key = f"<domain>:{id}"
    await cache.delete(cache_key)

    # Also invalidate list cache
    await cache.delete("<domain>:all")

    return <Domain>Response.from_entity(entity)
```

### 6. Add cache stats to health endpoint

The health endpoint already includes cache stats. Verify it works:

```python
# app/main.py
@app.get("/health")
async def health_check() -> dict:
    """Return service health status including cache stats."""
    cache = await get_cache()
    stats = cache.get_stats()

    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "cache": {
            "connected": cache.is_connected,
            "hits": stats.hits,
            "misses": stats.misses,
            "errors": stats.errors,
        },
    }
```

### 7. Add integration tests

```python
# tests/integration/test_cache.py
import pytest
from app.core.cache import Cache


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Test basic cache operations."""
    cache = Cache(redis_url="redis://localhost:6379")

    # Set value
    await cache.set("test:key", {"data": "value"}, ttl=60)

    # Get value
    result = await cache.get("test:key")

    assert result is not None
    assert result["data"] == "value"

    # Cleanup
    await cache.delete("test:key")


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test cache TTL expiration."""
    cache = Cache(redis_url="redis://localhost:6379")

    # Set with 1 second TTL
    await cache.set("test:ttl", {"data": "value"}, ttl=1)

    # Should exist immediately
    result = await cache.get("test:ttl")
    assert result is not None

    # Wait for expiration
    import asyncio
    await asyncio.sleep(1.5)

    # Should be gone
    result = await cache.get("test:ttl")
    assert result is None


@pytest.mark.asyncio
async def test_cache_handles_redis_down():
    """Test cache fails open when Redis is down."""
    cache = Cache(redis_url="redis://invalid:6379")

    # Should not raise
    result = await cache.get("test:key")
    assert result is None

    # Should not raise
    await cache.set("test:key", {"data": "value"}, ttl=60)
```

### 8. Add API tests

```python
# tests/api/test_<domain>_api.py
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_<domain>_returns_cached_data():
    """Test endpoint returns cached data on cache hit."""
    # Arrange
    mock_cache = AsyncMock()
    mock_cache.get.return_value = {
        "id": "123",
        "name": "Cached Item"
    }

    with patch("app.api.deps.get_redis_cache", return_value=mock_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/<domain>")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Cached Item"

            # Provider should not be called
            # (verify via mock or logs)


@pytest.mark.asyncio
async def test_<domain>_caches_provider_response():
    """Test endpoint caches provider response on cache miss."""
    # Arrange
    mock_cache = AsyncMock()
    mock_cache.get.return_value = None  # Cache miss

    with patch("app.api.deps.get_redis_cache", return_value=mock_cache):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/<domain>")

            # Assert
            assert response.status_code == 200

            # Cache.set should be called
            mock_cache.set.assert_called_once()
```

### 9. Run quality gate

```bash
uv run ruff check app/ tests/ && uv run python -m compileall app/ && uv run pytest tests/ -v
```

## Cache key patterns

| Scenario | Key Pattern | Example |
|----------|-------------|---------|
| All items | `<domain>:all` | `weather:all` |
| With parameters | `<domain>:<param>` | `weather:imperial` |
| Multiple params | `<domain>:<p1>:<p2>` | `calendar:2026-08-17:2026-08-24` |
| By ID | `<domain>:<id>` | `family:dad` |
| User-specific | `<domain>:<user>:<id>` | `tasks:user123:456` |

## TTL guidelines

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Weather (current) | 10 min | Changes slowly, frontend refreshes every 10 min |
| Weather (forecast) | 30 min | Forecast changes even slower |
| Calendar events | 2 min | Events can change, need fresh data |
| Family members | 5 min | Rarely changes |
| Static config | 1 hour | Almost never changes |

## Checklist

- [ ] Cache dependency added to route
- [ ] Cache TTL defined in settings
- [ ] Cache key strategy designed
- [ ] Fail-open design implemented
- [ ] Cache invalidation added (if mutable data)
- [ ] Integration tests added
- [ ] API tests added
- [ ] Quality gate passes

## Example: Caching weather endpoint

```python
@router.get("", response_model=WeatherResponse)
async def get_weather(
    provider: WeatherProviderDep,
    cache: CacheDep,
    query: WeatherQuery = Depends(),
) -> WeatherResponse:
    """Get weather with caching."""
    cache_key = f"weather:{query.units}"

    # Try cache
    cached = await cache.get(cache_key)
    if cached:
        return WeatherResponse(**cached)

    # Fetch
    result = await provider.get_weather(query.units)

    # Cache
    await cache.set(cache_key, result.model_dump(), settings.WEATHER_CACHE_TTL)

    return result
```

## Notes

- Always use fail-open design
- Cache keys must include all query parameters
- TTL should match data freshness requirements
- Invalidate cache on data updates
- Monitor cache hit/miss ratio via `/health` endpoint
- Test both cache hit and miss scenarios
