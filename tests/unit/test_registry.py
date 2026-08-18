"""Tests for provider registry."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.registry import registry
from app.infrastructure.calendar.mock_adapter import MockCalendarAdapter
from app.infrastructure.persistence.family_repository import FamilyRepositoryImpl
from app.infrastructure.weather.mock_adapter import MockWeatherAdapter


class TestRegistry:
    """Tests for provider registry."""

    def test_get_weather_provider(self):
        """Registry returns weather provider from container."""
        with patch("app.core.registry.get_weather_provider") as mock_get:
            mock_provider = MagicMock(spec=MockWeatherAdapter)
            mock_get.return_value = mock_provider

            provider = registry.get_weather_provider()

            assert provider is mock_provider
            mock_get.assert_called_once()

    def test_get_calendar_provider(self):
        """Registry returns calendar provider from container."""
        with patch("app.core.registry.get_calendar_provider") as mock_get:
            mock_provider = MagicMock(spec=MockCalendarAdapter)
            mock_get.return_value = mock_provider

            provider = registry.get_calendar_provider()

            assert provider is mock_provider
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_family_repository(self):
        """Registry returns family repository from container."""
        with patch("app.core.registry.get_family_repository") as mock_get:
            mock_repo = MagicMock(spec=FamilyRepositoryImpl)

            # Create an async generator that yields the mock repo
            async def mock_gen():
                yield mock_repo

            mock_get.return_value = mock_gen()

            # Get the generator from registry and iterate it
            async for repository in registry.get_family_repository():
                assert repository is mock_repo
                break


class TestRegistryVerification:
    """Tests for registry verification functionality."""

    def test_verify_providers_all_available(self):
        """Verify returns True for all providers when available."""
        with (
            patch("app.core.registry.get_weather_provider") as mock_weather,
            patch("app.core.registry.get_calendar_provider") as mock_calendar,
        ):
            mock_weather.return_value = MagicMock()
            mock_calendar.return_value = MagicMock()

            status = registry.verify_providers()

            assert status["weather"] is True
            assert status["calendar"] is True

    def test_verify_providers_weather_unavailable(self):
        """Verify returns False for weather when provider raises exception."""
        with (
            patch("app.core.registry.get_weather_provider") as mock_weather,
            patch("app.core.registry.get_calendar_provider") as mock_calendar,
        ):
            mock_weather.side_effect = Exception("Config error")
            mock_calendar.return_value = MagicMock()

            status = registry.verify_providers()

            assert status["weather"] is False
            assert status["calendar"] is True

    def test_verify_providers_calendar_unavailable(self):
        """Verify returns False for calendar when provider raises exception."""
        with (
            patch("app.core.registry.get_weather_provider") as mock_weather,
            patch("app.core.registry.get_calendar_provider") as mock_calendar,
        ):
            mock_weather.return_value = MagicMock()
            mock_calendar.side_effect = Exception("Config error")

            status = registry.verify_providers()

            assert status["weather"] is True
            assert status["calendar"] is False

    def test_verify_providers_all_unavailable(self):
        """Verify returns False for all providers when both raise exceptions."""
        with (
            patch("app.core.registry.get_weather_provider") as mock_weather,
            patch("app.core.registry.get_calendar_provider") as mock_calendar,
        ):
            mock_weather.side_effect = Exception("Config error")
            mock_calendar.side_effect = Exception("Config error")

            status = registry.verify_providers()

            assert status["weather"] is False
            assert status["calendar"] is False

    def test_verify_providers_returns_dict(self):
        """Verify returns a dictionary with expected keys."""
        with (
            patch("app.core.registry.get_weather_provider") as mock_weather,
            patch("app.core.registry.get_calendar_provider") as mock_calendar,
        ):
            mock_weather.return_value = MagicMock()
            mock_calendar.return_value = MagicMock()

            status = registry.verify_providers()

            assert isinstance(status, dict)
            assert "weather" in status
            assert "calendar" in status
            assert len(status) == 2
