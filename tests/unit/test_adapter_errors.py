"""Tests for adapter error handling — verify adapters raise instead of returning mock/empty data."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from googleapiclient.errors import HttpError

from app.core.exceptions import UpstreamServiceError
from app.infrastructure.calendar.google_adapter import GoogleCalendarAdapter
from app.infrastructure.weather.owm_adapter import OWMWeatherAdapter


class TestOWMWeatherAdapterErrors:
    """Test OWMWeatherAdapter raises UpstreamServiceError on failures."""

    @pytest.fixture
    def adapter(self):
        """Create OWM adapter with test config."""
        return OWMWeatherAdapter(api_key="test-key", lat=40.71, lon=-74.00)

    @pytest.mark.asyncio
    async def test_raises_when_current_returns_none(self, adapter):
        """Adapter raises UpstreamServiceError when current weather returns None."""
        # Mock _fetch_current to return None (simulates API failure)
        with patch.object(adapter, "_fetch_current", return_value=None):
            with pytest.raises(UpstreamServiceError) as exc_info:
                await adapter.get_weather()

            assert "current conditions unavailable" in str(exc_info.value)
            assert exc_info.value.service_name == "openweathermap"

    @pytest.mark.asyncio
    async def test_raises_when_both_daily_and_hourly_fail(self, adapter):
        """Adapter raises UpstreamServiceError when both daily and hourly forecasts fail."""
        # Mock current to succeed, but daily and hourly to fail
        with (
            patch.object(adapter, "_fetch_current", return_value={"data": [{}]}),
            patch.object(adapter, "_fetch_daily", return_value=None),
            patch.object(adapter, "_fetch_hourly", return_value=None),
        ):
            with pytest.raises(UpstreamServiceError) as exc_info:
                await adapter.get_weather()

            assert "forecast data unavailable" in str(exc_info.value)
            assert exc_info.value.service_name == "openweathermap"

    @pytest.mark.asyncio
    async def test_raises_on_http_error_in_fetch_current(self, adapter):
        """Adapter raises UpstreamServiceError when HTTP error occurs in _fetch_current."""
        with patch("app.infrastructure.weather.owm_adapter.get_http_client") as mock_client:
            mock_http = AsyncMock()
            mock_client.return_value = mock_http
            mock_http.get.side_effect = httpx.HTTPError("Network error")

            with pytest.raises(UpstreamServiceError):
                await adapter.get_weather()


class TestGoogleCalendarAdapterErrors:
    """Test GoogleCalendarAdapter raises UpstreamServiceError on failures."""

    @pytest.fixture
    def adapter(self):
        """Create Google Calendar adapter with test config."""
        return GoogleCalendarAdapter(credentials_path="/fake/path.json")

    @pytest.mark.asyncio
    async def test_raises_on_http_error_in_fetch_events_sync(self, adapter):
        """Adapter raises UpstreamServiceError when Google API returns HttpError."""
        # Mock credentials to succeed
        mock_creds = MagicMock()
        with patch.object(adapter, "_get_credentials", return_value=mock_creds):
            # Mock the Google API service to raise HttpError
            mock_service = MagicMock()
            mock_events = MagicMock()
            mock_service.events.return_value = mock_events
            mock_events.list.return_value.execute.side_effect = HttpError(
                resp=MagicMock(status=500),
                content=b'{"error": {"message": "Internal server error"}}',
            )

            with patch(
                "app.infrastructure.calendar.google_adapter.build",
                return_value=mock_service,
            ):
                with pytest.raises(UpstreamServiceError) as exc_info:
                    # Call the sync method directly to test error handling
                    from datetime import datetime

                    adapter._fetch_events_sync(
                        "test@example.com",
                        datetime(2026, 1, 1),
                        datetime(2026, 1, 7),
                    )

                assert "google-calendar" in str(exc_info.value.service_name)
                assert "Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raises_on_unexpected_error_in_fetch_events_sync(self, adapter):
        """Adapter raises UpstreamServiceError on unexpected errors."""
        # Mock credentials to succeed
        mock_creds = MagicMock()
        with patch.object(adapter, "_get_credentials", return_value=mock_creds):
            # Mock the Google API service to raise unexpected error
            mock_service = MagicMock()
            mock_events = MagicMock()
            mock_service.events.return_value = mock_events
            mock_events.list.return_value.execute.side_effect = RuntimeError(
                "Unexpected failure"
            )

            with patch(
                "app.infrastructure.calendar.google_adapter.build",
                return_value=mock_service,
            ):
                with pytest.raises(UpstreamServiceError) as exc_info:
                    # Call the sync method directly to test error handling
                    from datetime import datetime

                    adapter._fetch_events_sync(
                        "test@example.com",
                        datetime(2026, 1, 1),
                        datetime(2026, 1, 7),
                    )

                assert "google-calendar" in str(exc_info.value.service_name)
                assert "Unexpected failure" in str(exc_info.value)
