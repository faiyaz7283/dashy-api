---
name: add-provider-adapter
description: Implement a new provider adapter for an existing domain — e.g., a new weather API, calendar source, or other external integration.
---

# Add Provider Adapter

Implement a new provider adapter for an existing domain (weather, calendar, etc.).

## When to use

- Adding an alternative weather API (Visual Crossing, Tomorrow.io, etc.)
- Adding a new calendar source (Apple Calendar, CalDAV, etc.)
- Any new external integration that implements an existing Protocol

## When NOT to use

- Adding a completely new domain — use `/add-domain` instead
- Adding a repository for database persistence — use `/add-repository` instead

## Prerequisites

- Domain exists with Protocol defined in `app/domain/<domain>/ports.py`
- Understand the external API/service you're integrating
- API credentials or access method identified

## Steps

### 1. Review the Protocol

Read the existing Protocol to understand the contract:

```python
# app/domain/weather/ports.py
class WeatherProvider(Protocol):
    async def get_current_weather(self, location: str) -> dict:
        """Fetch current weather conditions."""
        ...

    async def get_forecast(self, location: str, days: int = 7) -> list[dict]:
        """Fetch weather forecast."""
        ...
```

**Note:** All Protocol methods must be `async def`.

### 2. Create adapter file

Create `app/infrastructure/<domain>/<name>_adapter.py`:

```python
"""<Name> adapter for <domain> provider.

Implements <Domain>Provider Protocol for <Name> API.
"""

import asyncio
from typing import Any

from app.domain.<domain>.ports import <Domain>Provider
from app.infrastructure.<domain>.http_client import get_http_client
from app.core.logging import get_logger

logger = get_logger(__name__)


class <Name><Domain>Adapter:
    """<Name> implementation of <Domain>Provider.

    Fetches data from <Name> API and maps to domain models.
    """

    def __init__(self, api_key: str, **kwargs: Any) -> None:
        """Initialize adapter.

        Args:
            api_key: API key for authentication.
            **kwargs: Additional configuration (base_url, etc.).
        """
        self.api_key = api_key
        self.base_url = kwargs.get("base_url", "https://api.example.com")

    async def get_current_weather(self, location: str) -> dict:
        """Fetch current weather from <Name> API.

        Args:
            location: Location identifier (city, coordinates, etc.).

        Returns:
            Dictionary with current weather data.

        Raises:
            httpx.HTTPStatusError: If API returns error status.
        """
        client = get_http_client()

        try:
            response = await client.get(
                f"{self.base_url}/current",
                params={"location": location},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()

            data = response.json()
            return self._parse_current_weather(data)

        except Exception as e:
            logger.error(
                "<name>_api_error",
                location=location,
                error=str(e)
            )
            raise

    def _parse_current_weather(self, data: dict) -> dict:
        """Parse API response to domain format.

        Args:
            data: Raw API response.

        Returns:
            Parsed weather data dictionary.
        """
        return {
            "temperature": data["temp"],
            "condition": data["weather"]["main"],
            "humidity": data["humidity"],
            # ... map all fields
        }
```

### 3. Handle sync→async boundary (if needed)

If the external SDK is synchronous, wrap with `run_in_executor`:

```python
# Example: Google Calendar API (sync SDK)
from googleapiclient.discovery import build


class GoogleCalendarAdapter:
    """Google Calendar implementation of CalendarProvider."""

    async def fetch_events(self, calendar_id: str, date_range: DateRange) -> list[dict]:
        """Fetch events from Google Calendar API.

        Offloads sync Google API call to thread pool.

        Args:
            calendar_id: Calendar identifier.
            date_range: Date range to query.

        Returns:
            List of event dictionaries.
        """
        loop = asyncio.get_running_loop()

        # Offload sync call to thread pool
        events = await loop.run_in_executor(
            None,
            self._fetch_events_sync,
            calendar_id,
            date_range
        )

        return events

    def _fetch_events_sync(self, calendar_id: str, date_range: DateRange) -> list[dict]:
        """Synchronous Google API call (runs in thread pool).

        Args:
            calendar_id: Calendar identifier.
            date_range: Date range to query.

        Returns:
            List of event dictionaries.
        """
        # Build Google Calendar service (sync)
        service = build('calendar', 'v3', credentials=self._get_credentials())

        # Make API calls (sync)
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=date_range.start.isoformat(),
            timeMax=date_range.end.isoformat(),
        ).execute()

        return events_result.get('items', [])
```

**Rules:**
- Only the external SDK call runs in executor
- Parsing can happen in async method or sync helper
- Never block the event loop with sync I/O

### 4. Create HTTP client (if needed)

If the adapter makes HTTP calls, create shared client:

```python
# app/infrastructure/<domain>/http_client.py
"""Shared HTTP client for <domain> adapters."""

import httpx
from functools import lru_cache


@lru_cache()
def get_http_client() -> httpx.AsyncClient:
    """Get shared async HTTP client with connection pooling.

    Returns:
        httpx.AsyncClient instance.
    """
    return httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
    )
```

**Why shared client?** Connection pooling reduces latency for frequent API calls.

### 5. Register in DI container

Add to `app/core/container.py`:

```python
from app.infrastructure.<domain>.<name>_adapter import <Name><Domain>Adapter


@lru_cache
def get_<domain>_provider() -> <Domain>Provider:
    """Get <domain> provider based on configuration.

    Returns:
        <Domain>Provider instance.
    """
    provider_name = settings.<DOMAIN>_PROVIDER  # e.g., "owm", "visual_crossing"

    if provider_name == "<name>":
        return <Name><Domain>Adapter(
            api_key=settings.<DOMAIN>_API_KEY,
            base_url=settings.<DOMAIN>_BASE_URL
        )
    elif provider_name == "mock":
        return Mock<Domain>Adapter()
    else:
        # Default provider
        return Default<Domain>Adapter(...)
```

Add configuration to `app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings

    <DOMAIN>_PROVIDER: str = "default"  # "default", "<name>", "mock"
    <DOMAIN>_API_KEY: str = ""
    <DOMAIN>_BASE_URL: str = "https://api.example.com"
```

### 6. Update environment files

Add to `.env.example`:

```bash
# <Name> <Domain> Provider
<DATABASE>_PROVIDER=<name>
<DATABASE>_API_KEY=your_api_key_here
<DATABASE>_BASE_URL=https://api.example.com
```

Add to `.env.test`:

```bash
<DATABASE>_PROVIDER=mock
```

### 7. Add integration tests

Create `tests/integration/test_<name>_adapter.py`:

```python
import pytest
from httpx import AsyncClient
from app.infrastructure.<domain>.<name>_adapter import <Name><Domain>Adapter


@pytest.mark.asyncio
async def test_<name>_adapter_parses_current_weather(httpx_mock):
    """Test adapter correctly parses API response."""
    # Arrange
    httpx_mock.add_response(
        url="https://api.example.com/current?location=NewYork",
        json={
            "temp": 22.5,
            "weather": {"main": "Clear"},
            "humidity": 65
        }
    )

    adapter = <Name><Domain>Adapter(api_key="test_key")

    # Act
    result = await adapter.get_current_weather("NewYork")

    # Assert
    assert result["temperature"] == 22.5
    assert result["condition"] == "Clear"
    assert result["humidity"] == 65


@pytest.mark.asyncio
async def test_<name>_adapter_handles_api_error(httpx_mock):
    """Test adapter handles API errors gracefully."""
    # Arrange
    httpx_mock.add_response(
        url="https://api.example.com/current?location=Invalid",
        status_code=404,
        json={"error": "Location not found"}
    )

    adapter = <Name><Domain>Adapter(api_key="test_key")

    # Act & Assert
    with pytest.raises(Exception):  # Or specific exception type
        await adapter.get_current_weather("Invalid")
```

**Use pytest-httpx** to mock HTTP calls without hitting real API.

### 8. Add unit tests (optional)

If adapter has complex parsing logic, add unit tests:

```python
# tests/unit/infrastructure/test_<name>_adapter.py
import pytest
from app.infrastructure.<domain>.<name>_adapter import <Name><Domain>Adapter


def test_parse_current_weather():
    """Test response parsing logic."""
    adapter = <Name><Domain>Adapter(api_key="test")

    raw_data = {
        "temp": 22.5,
        "weather": {"main": "Clear"},
        "humidity": 65
    }

    result = adapter._parse_current_weather(raw_data)

    assert result["temperature"] == 22.5
    assert result["condition"] == "Clear"
```

### 9. Update registry (optional)

If using registry pattern, add to `app/core/registry.py`:

```python
class ProviderRegistry:
    # ... existing code

    @staticmethod
    def get_<name>_<domain>_adapter():
        """Get <Name> adapter for <domain>."""
        from app.core.container import get_settings
        settings = get_settings()
        return <Name><Domain>Adapter(
            api_key=settings.<DOMAIN>_API_KEY,
            base_url=settings.<DOMAIN>_BASE_URL
        )
```

### 10. Run quality gate

```bash
uv run ruff check app/ tests/ && uv run python -m compileall app/ && uv run pytest tests/ -v
```

### 11. Update documentation

- Add new provider option to `README.md`
- Document API setup instructions
- Update `.env.example` with new variables

## Checklist

- [ ] Adapter file created implementing Protocol
- [ ] All Protocol methods implemented as `async def`
- [ ] Sync SDK calls wrapped in `run_in_executor` (if needed)
- [ ] HTTP client created (if making HTTP calls)
- [ ] DI container updated with provider selection logic
- [ ] Configuration added to `Settings`
- [ ] Environment files updated (`.env.example`, `.env.test`)
- [ ] Integration tests added with pytest-httpx
- [ ] Unit tests added (if complex parsing)
- [ ] Quality gate passes
- [ ] Documentation updated

## Example: Adding Visual Crossing weather provider

1. Create `app/infrastructure/weather/visual_crossing_adapter.py`
2. Implement `WeatherProvider` Protocol
3. Parse Visual Crossing API response format
4. Add `WEATHER_PROVIDER=visual_crossing` option to container
5. Add `VISUAL_CROSSING_API_KEY` to config
6. Integration tests with mocked API responses
7. Update README with setup instructions

## Notes

- Adapter should handle API-specific errors and map to domain exceptions
- Use structured logging (`get_logger`) for error tracking
- Follow Google-style docstrings
- Keep parsing logic in private methods (`_parse_*`)
- Test both success and error paths
