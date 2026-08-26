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
from app.domain.chores.condition_evaluator import ConditionEvaluator
from app.domain.chores.ports import ChoresRepository
from app.domain.chores.services import ChoresService
from app.domain.family.ports import FamilyRepository
from app.domain.family.services import FamilyService
from app.domain.weather.ports import WeatherProvider
from app.infrastructure.calendar.google_adapter import GoogleCalendarAdapter
from app.infrastructure.calendar.mock_adapter import MockCalendarAdapter
from app.infrastructure.chores.mock_adapter import MockChoresRepository
from app.infrastructure.persistence.chores_repository import ChoresRepositoryImpl
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


async def get_chores_repository() -> ChoresRepository:
    """Get the chores repository based on configuration.

    Returns MockChoresAdapter if CHORES_USE_MOCK is True,
    otherwise returns ChoresRepositoryImpl with a fresh database session.
    """
    if settings.CHORES_USE_MOCK:
        yield MockChoresRepository()
        return

    async_session_factory = get_async_session_factory()
    session = async_session_factory()
    try:
        yield ChoresRepositoryImpl(session)
    finally:
        await session.close()


async def get_condition_evaluator(
    weather_provider: WeatherProvider = Depends(get_weather_provider),
    calendar_provider: CalendarProvider = Depends(get_calendar_provider),
) -> ConditionEvaluator:
    """Get the condition evaluator for conditional chores.

    Uses the first family member's email as the default calendar ID.

    Args:
        weather_provider: Injected weather provider.
        calendar_provider: Injected calendar provider.

    Returns:
        ConditionEvaluator instance.
    """
    family_members = settings.get_family_members()
    calendar_id = family_members[0].email if family_members else ""
    return ConditionEvaluator(
        weather_provider=weather_provider,
        calendar_provider=calendar_provider,
        calendar_id=calendar_id,
    )


async def get_chores_service(
    chores_repository: ChoresRepository = Depends(get_chores_repository),
    condition_evaluator: ConditionEvaluator = Depends(get_condition_evaluator),
) -> ChoresService:
    """Get the chores service wrapping the repository.

    Args:
        chores_repository: Injected chores repository.
        condition_evaluator: Injected condition evaluator.

    Returns:
        ChoresService instance.
    """
    return ChoresService(
        repository=chores_repository,
        condition_evaluator=condition_evaluator,
    )


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
