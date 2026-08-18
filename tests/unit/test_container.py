"""Tests for dependency injection container."""

import contextlib
from unittest.mock import AsyncMock, patch

import pytest

from app.core.container import (
    get_calendar_provider,
    get_family_repository,
    get_weather_provider,
    reset_container,
)
from app.infrastructure.calendar.google_adapter import GoogleCalendarAdapter
from app.infrastructure.calendar.mock_adapter import MockCalendarAdapter
from app.infrastructure.persistence.family_repository import FamilyRepositoryImpl
from app.infrastructure.weather.mock_adapter import MockWeatherAdapter
from app.infrastructure.weather.owm_adapter import OWMWeatherAdapter


class TestWeatherProvider:
    """Tests for weather provider injection."""

    def test_returns_mock_when_use_mock_true(self):
        """Container returns MockWeatherAdapter when WEATHER_USE_MOCK is True."""
        reset_container()
        with patch("app.core.container.settings") as mock_settings:
            mock_settings.WEATHER_USE_MOCK = True
            provider = get_weather_provider()
            assert isinstance(provider, MockWeatherAdapter)

    def test_returns_owm_when_use_mock_false(self):
        """Container returns OWMWeatherAdapter when WEATHER_USE_MOCK is False."""
        reset_container()
        with patch("app.core.container.settings") as mock_settings:
            mock_settings.WEATHER_USE_MOCK = False
            mock_settings.OPENWEATHERMAP_API_KEY = "test-key"
            mock_settings.OPENWEATHERMAP_LAT = 40.7128
            mock_settings.OPENWEATHERMAP_LON = -74.0060
            provider = get_weather_provider()
            assert isinstance(provider, OWMWeatherAdapter)

    def test_provider_is_cached(self):
        """Container returns the same instance on multiple calls."""
        reset_container()
        with patch("app.core.container.settings") as mock_settings:
            mock_settings.WEATHER_USE_MOCK = True
            provider1 = get_weather_provider()
            provider2 = get_weather_provider()
            assert provider1 is provider2

    def test_reset_clears_cache(self):
        """Reset clears the cached provider."""
        reset_container()
        with patch("app.core.container.settings") as mock_settings:
            mock_settings.WEATHER_USE_MOCK = True
            get_weather_provider()

            # Change config
            mock_settings.WEATHER_USE_MOCK = False
            mock_settings.OPENWEATHERMAP_API_KEY = "test-key"
            mock_settings.OPENWEATHERMAP_LAT = 40.7128
            mock_settings.OPENWEATHERMAP_LON = -74.0060

            # Should still return cached mock
            provider2 = get_weather_provider()
            assert isinstance(provider2, MockWeatherAdapter)

            # After reset, should return new provider
            reset_container()
            provider3 = get_weather_provider()
            assert isinstance(provider3, OWMWeatherAdapter)


class TestCalendarProvider:
    """Tests for calendar provider injection."""

    def test_returns_mock_when_use_mock_true(self):
        """Container returns MockCalendarAdapter when CALENDAR_USE_MOCK is True."""
        reset_container()
        with patch("app.core.container.settings") as mock_settings:
            mock_settings.CALENDAR_USE_MOCK = True
            provider = get_calendar_provider()
            assert isinstance(provider, MockCalendarAdapter)

    def test_returns_google_when_use_mock_false(self):
        """Container returns GoogleCalendarAdapter when CALENDAR_USE_MOCK is False."""
        reset_container()
        with patch("app.core.container.settings") as mock_settings:
            mock_settings.CALENDAR_USE_MOCK = False
            mock_settings.GOOGLE_SERVICE_ACCOUNT_JSON = "/path/to/creds.json"
            provider = get_calendar_provider()
            assert isinstance(provider, GoogleCalendarAdapter)

    def test_provider_is_cached(self):
        """Container returns the same instance on multiple calls."""
        reset_container()
        with patch("app.core.container.settings") as mock_settings:
            mock_settings.CALENDAR_USE_MOCK = True
            provider1 = get_calendar_provider()
            provider2 = get_calendar_provider()
            assert provider1 is provider2


class TestFamilyRepository:
    """Tests for family repository injection."""

    @pytest.mark.asyncio
    async def test_returns_family_repository(self):
        """Container yields FamilyRepositoryImpl."""
        with patch("app.core.container.get_async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value = mock_session

            # Get the generator and verify it yields a FamilyRepositoryImpl
            gen = get_family_repository()
            repository = await gen.__anext__()

            assert isinstance(repository, FamilyRepositoryImpl)

            # Generator cleanup may fail with mocks — that's expected in tests
            with contextlib.suppress(TypeError, RuntimeError):
                await gen.aclose()


class TestResetContainer:
    """Tests for container reset functionality."""

    def test_reset_clears_all_caches(self):
        """Reset clears all provider caches."""
        reset_container()
        with patch("app.core.container.settings") as mock_settings:
            mock_settings.WEATHER_USE_MOCK = True
            mock_settings.CALENDAR_USE_MOCK = True

            # Get providers to cache them
            weather1 = get_weather_provider()
            calendar1 = get_calendar_provider()

            # Reset
            reset_container()

            # Get again - should be new instances
            weather2 = get_weather_provider()
            calendar2 = get_calendar_provider()

            # They should be different instances (cache was cleared)
            assert weather1 is not weather2
            assert calendar1 is not calendar2
