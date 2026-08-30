"""Weather API routes.

Provides endpoints for fetching current weather and forecast data.
"""

import httpx
from fastapi import APIRouter, Depends

from app.api.deps import CacheDep, WeatherProviderDep
from app.api.models.requests import WeatherQuery
from app.api.models.weather import WeatherResponse
from app.config import settings
from app.core.cache import RetryConfig

router = APIRouter(prefix="/weather", tags=["weather"])

# Retry config for weather API calls
WEATHER_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    backoff_seconds=[1.0, 2.0, 4.0],
    transient_errors=(httpx.HTTPError, ConnectionError, TimeoutError, OSError),
)


@router.get("", response_model=WeatherResponse)
async def get_weather_endpoint(
    weather_provider: WeatherProviderDep,
    cache: CacheDep,
    query: WeatherQuery = Depends(),
) -> WeatherResponse:
    """Get current weather and 19-day forecast.

    Uses stale-while-revalidate pattern: fresh cache → stale cache → fetch with retry.
    On success, caches result with both fresh and stale TTLs.

    Args:
        weather_provider: Injected weather provider instance.
        cache: Injected cache instance.
        query: Validated query parameters.

    Returns:
        WeatherResponse with current conditions and forecast.

    Raises:
        UpstreamServiceError: When all retries fail and no stale cache exists.
    """
    cache_key = f"weather:{query.units}"

    async def fetch_weather() -> dict:
        """Fetch fresh weather data from provider."""
        result = await weather_provider.get_weather(query.units)
        return result.model_dump()

    cached_data = await cache.fetch(
        key=cache_key,
        fetcher=fetch_weather,
        fresh_ttl=settings.WEATHER_CACHE_TTL,
        stale_ttl=settings.WEATHER_STALE_TTL,
        retry_config=WEATHER_RETRY_CONFIG,
        service_name="openweathermap",
    )

    return WeatherResponse(**cached_data)
