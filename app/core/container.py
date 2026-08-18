"""Dependency injection container for Dashy.

Centralizes all dependency creation and lifecycle management.
Uses FastAPI's Depends() for request-scoped dependencies.
"""

from functools import lru_cache

from fastapi import Depends

from app.config import settings
from app.core.cache import Cache, get_cache
from app.core.database import get_async_session_factory
from app.domain.calendar.ports import CalendarProvider
from app.domain.family.ports import FamilyRepository
from app.domain.family.services import FamilyService
from app.domain.weather.ports import WeatherProvider
from app.infrastructure.calendar.google_adapter import GoogleCalendarAdapter
from app.infrastructure.calendar.mock_adapter import MockCalendarAdapter
from app.infrastructure.persistence.family_repository import FamilyRepositoryImpl
from app.infrastructure.weather.mock_adapter import MockWeatherAdapter
from app.infrastructure.weather.owm_adapter import OWMWeatherAdapter


@lru_cache
def get_weather_provider() -> WeatherProvider:
    """Get the weather provider based on configuration.

    Returns MockWeatherAdapter if WEATHER_USE_MOCK is True,
    otherwise returns OWMWeatherAdapter.
    """
    if settings.WEATHER_USE_MOCK:
        return MockWeatherAdapter()
    return OWMWeatherAdapter(
        api_key=settings.OPENWEATHERMAP_API_KEY,
        lat=settings.OPENWEATHERMAP_LAT,
        lon=settings.OPENWEATHERMAP_LON,
    )


@lru_cache
def get_calendar_provider() -> CalendarProvider:
    """Get the calendar provider based on configuration.

    Returns MockCalendarAdapter if CALENDAR_USE_MOCK is True,
    otherwise returns GoogleCalendarAdapter.
    """
    if settings.CALENDAR_USE_MOCK:
        return MockCalendarAdapter()
    return GoogleCalendarAdapter(
        credentials_path=settings.GOOGLE_SERVICE_ACCOUNT_JSON,
    )


async def get_family_repository() -> FamilyRepository:
    """Get the family repository with async database session.

    Returns FamilyRepositoryImpl with a fresh database session.
    The session lifecycle is managed by FastAPI's dependency injection.
    """
    async_session_factory = get_async_session_factory()
    session = async_session_factory()
    try:
        yield FamilyRepositoryImpl(session)
    finally:
        await session.close()


async def get_family_service(
    family_repository: FamilyRepository = Depends(get_family_repository),
) -> FamilyService:
    """Get the family service wrapping the repository.

    Uses ``Depends(get_family_repository)`` explicitly to avoid a circular
    import with ``app.api.deps``.

    Args:
        family_repository: Injected family repository.

    Returns:
        FamilyService instance.
    """
    return FamilyService(repository=family_repository)


async def get_redis_cache() -> Cache:
    """Get the Redis cache instance.

    Returns:
        Cache instance with Redis connection.
    """
    return await get_cache()


def reset_container() -> None:
    """Reset the DI container cache.

    Useful for testing to ensure fresh instances.
    """
    get_weather_provider.cache_clear()
    get_calendar_provider.cache_clear()
