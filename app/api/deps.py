"""FastAPI dependencies for Dashy.

Provides dependency injection functions for route handlers.
"""

from typing import Annotated

from fastapi import Depends

from app.core.cache import Cache
from app.core.container import (
    get_calendar_provider,
    get_family_repository,
    get_family_service,
    get_redis_cache,
    get_weather_provider,
)
from app.domain.calendar.ports import CalendarProvider
from app.domain.family.ports import FamilyRepository
from app.domain.family.services import FamilyService
from app.domain.weather.ports import WeatherProvider

# Type aliases for cleaner dependency injection
WeatherProviderDep = Annotated[WeatherProvider, Depends(get_weather_provider)]
CalendarProviderDep = Annotated[CalendarProvider, Depends(get_calendar_provider)]
FamilyRepositoryDep = Annotated[FamilyRepository, Depends(get_family_repository)]
FamilyServiceDep = Annotated[FamilyService, Depends(get_family_service)]
CacheDep = Annotated[Cache, Depends(get_redis_cache)]
