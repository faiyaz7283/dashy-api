---
name: add-calendar-source
description: Add a new calendar provider (Apple Calendar, CalDAV, etc.) — implement CalendarProvider Protocol with authentication and event fetching.
---

# Add Calendar Source

Add a new calendar provider integration (Apple Calendar, CalDAV, etc.).

## When to use

- Adding Apple Calendar (iCloud) support
- Adding CalDAV protocol support
- Adding any new calendar API (Exchange, etc.)
- Not for adding new calendar features — that's domain work

## Prerequisites

- `CalendarProvider` Protocol exists in `app/domain/calendar/ports.py`
- Understand the calendar API/protocol you're integrating
- Authentication method identified (OAuth, API key, service account, etc.)

## Steps

### 1. Review the Protocol

Read the existing Protocol:

```python
# app/domain/calendar/ports.py
from app.domain.calendar.models import DateRange


class CalendarProvider(Protocol):
    """Protocol for calendar data providers."""

    async def fetch_events(
        self,
        calendar_id: str,
        date_range: DateRange,
    ) -> list[dict]:
        """Fetch calendar events within date range.

        Args:
            calendar_id: Calendar identifier.
            date_range: Date range to query.

        Returns:
            List of event dictionaries.
        """
        ...
```

### 2. Create adapter file

Create `app/infrastructure/calendar/<name>_adapter.py`:

```python
"""<Name> calendar adapter.

Implements CalendarProvider Protocol for <Name> calendar service.
"""

import asyncio
from datetime import datetime
from typing import Any

from app.domain.calendar.models import DateRange
from app.domain.calendar.ports import CalendarProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


class <Name>CalendarAdapter:
    """<Name> implementation of CalendarProvider.

    Fetches events from <Name> calendar API.
    """

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize adapter.

        Args:
            credentials: Authentication credentials.
        """
        self.credentials = credentials
        self.client = self._create_client()

    def _create_client(self) -> Any:
        """Create calendar API client.

        Returns:
            Calendar API client instance.
        """
        # Initialize client based on calendar service
        # Example: CalDAV, iCloud API, Exchange, etc.
        pass

    async def fetch_events(
        self,
        calendar_id: str,
        date_range: DateRange,
    ) -> list[dict]:
        """Fetch events from <Name> calendar.

        Args:
            calendar_id: Calendar identifier.
            date_range: Date range to query.

        Returns:
            List of event dictionaries.

        Raises:
            Exception: If API call fails.
        """
        try:
            # Offload sync API call to thread pool
            loop = asyncio.get_running_loop()
            events = await loop.run_in_executor(
                None,
                self._fetch_events_sync,
                calendar_id,
                date_range
            )

            logger.info(
                "<name>_events_fetched",
                calendar_id=calendar_id,
                event_count=len(events)
            )

            return events

        except Exception as e:
            logger.error(
                "<name>_calendar_error",
                calendar_id=calendar_id,
                error=str(e)
            )
            raise

    def _fetch_events_sync(
        self,
        calendar_id: str,
        date_range: DateRange,
    ) -> list[dict]:
        """Synchronous calendar API call (runs in thread pool).

        Args:
            calendar_id: Calendar identifier.
            date_range: Date range to query.

        Returns:
            List of event dictionaries.
        """
        # Make sync API calls here
        # This runs in a thread pool, so it won't block the event loop

        events = []

        # Example: Fetch events from API
        # raw_events = self.client.get_events(
        #     calendar_id=calendar_id,
        #     start=date_range.start,
        #     end=date_range.end
        # )

        # for event in raw_events:
        #     events.append(self._parse_event(event))

        return events

    def _parse_event(self, raw_event: dict) -> dict:
        """Parse raw API event to domain format.

        Args:
            raw_event: Raw event from API.

        Returns:
            Parsed event dictionary.
        """
        return {
            "id": raw_event["id"],
            "title": raw_event["summary"],
            "start_time": raw_event["start"],
            "end_time": raw_event["end"],
            "all_day": raw_event.get("all_day", False),
            "location": raw_event.get("location"),
            "description": raw_event.get("description"),
            "recurrence": raw_event.get("recurrence"),
        }
```

**Key patterns:**
- Wrap sync SDK calls in `run_in_executor`
- Parse API response to domain format
- Log important operations
- Handle errors gracefully

### 3. Handle authentication

Different calendar services have different auth methods:

#### OAuth 2.0 (Apple Calendar, Google Calendar)

```python
class AppleCalendarAdapter:
    """Apple Calendar adapter with OAuth 2.0."""

    def __init__(self, access_token: str) -> None:
        """Initialize with OAuth access token.

        Args:
            access_token: OAuth 2.0 access token.
        """
        self.access_token = access_token

    def _create_client(self) -> Any:
        """Create authenticated CalDAV client."""
        from caldav import CalDAVClient

        return CalDAVClient(
            url="https://caldav.icloud.com",
            token=self.access_token
        )
```

#### Service Account (Google Calendar)

```python
class GoogleCalendarAdapter:
    """Google Calendar adapter with service account."""

    def __init__(self, credentials_path: str) -> None:
        """Initialize with service account credentials.

        Args:
            credentials_path: Path to service account JSON file.
        """
        self.credentials_path = credentials_path

    def _create_client(self) -> Any:
        """Create Google Calendar API client."""
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path,
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )

        return build('calendar', 'v3', credentials=credentials)
```

#### API Key (some services)

```python
class SomeCalendarAdapter:
    """Calendar adapter with API key."""

    def __init__(self, api_key: str) -> None:
        """Initialize with API key.

        Args:
            api_key: API key for authentication.
        """
        self.api_key = api_key
```

### 4. Add configuration

Edit `app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings

    # Calendar provider settings
    CALENDAR_PROVIDER: str = "google"  # "google", "apple", "caldav", "mock"

    # Apple Calendar settings
    APPLE_CALENDAR_TOKEN: str = ""

    # CalDAV settings
    CALDAV_URL: str = ""
    CALDAV_USERNAME: str = ""
    CALDAV_PASSWORD: str = ""
```

### 5. Register in DI container

Edit `app/core/container.py`:

```python
from app.infrastructure.calendar.apple_adapter import AppleCalendarAdapter
from app.infrastructure.calendar.caldav_adapter import CalDAVCalendarAdapter


@lru_cache
def get_calendar_provider() -> CalendarProvider:
    """Get calendar provider based on configuration.

    Returns:
        CalendarProvider instance.
    """
    provider_name = settings.CALENDAR_PROVIDER

    if provider_name == "google":
        return GoogleCalendarAdapter(
            credentials_path=settings.GOOGLE_SERVICE_ACCOUNT_JSON
        )
    elif provider_name == "apple":
        return AppleCalendarAdapter(
            access_token=settings.APPLE_CALENDAR_TOKEN
        )
    elif provider_name == "caldav":
        return CalDAVCalendarAdapter(
            url=settings.CALDAV_URL,
            username=settings.CALDAV_USERNAME,
            password=settings.CALDAV_PASSWORD
        )
    elif provider_name == "mock":
        return MockCalendarAdapter()
    else:
        raise ValueError(f"Unknown calendar provider: {provider_name}")
```

### 6. Update environment files

Add to `.env.example`:

```bash
# Calendar Provider
CALENDAR_PROVIDER=apple  # google, apple, caldav, mock

# Apple Calendar (if using Apple)
APPLE_CALENDAR_TOKEN=your_oauth_token_here

# CalDAV (if using CalDAV)
CALDAV_URL=https://caldav.example.com
CALDAV_USERNAME=user@example.com
CALDAV_PASSWORD=your_password_here
```

### 7. Add integration tests

Create `tests/integration/test_<name>_adapter.py`:

```python
import pytest
from datetime import datetime, timedelta
from app.domain.calendar.models import DateRange
from app.infrastructure.calendar.<name>_adapter import <Name>CalendarAdapter


@pytest.mark.asyncio
async def test_<name>_adapter_fetches_events():
    """Test adapter fetches events from calendar."""
    # Arrange
    adapter = <Name>CalendarAdapter(credentials={...})
    date_range = DateRange(
        start=datetime.now(),
        end=datetime.now() + timedelta(days=7)
    )

    # Act
    events = await adapter.fetch_events("calendar_id", date_range)

    # Assert
    assert isinstance(events, list)
    # Check event structure
    if events:
        event = events[0]
        assert "id" in event
        assert "title" in event
        assert "start_time" in event
        assert "end_time" in event


@pytest.mark.asyncio
async def test_<name>_adapter_handles_empty_calendar():
    """Test adapter handles calendar with no events."""
    adapter = <Name>CalendarAdapter(credentials={...})
    date_range = DateRange(
        start=datetime.now(),
        end=datetime.now() + timedelta(days=7)
    )

    events = await adapter.fetch_events("empty_calendar", date_range)

    assert events == []
```

### 8. Add unit tests for parsing

```python
# tests/unit/infrastructure/test_<name>_adapter.py
from app.infrastructure.calendar.<name>_adapter import <Name>CalendarAdapter


def test_parse_event():
    """Test event parsing logic."""
    adapter = <Name>CalendarAdapter(credentials={})

    raw_event = {
        "id": "123",
        "summary": "Team Meeting",
        "start": "2026-08-17T10:00:00Z",
        "end": "2026-08-17T11:00:00Z",
        "location": "Conference Room",
        "description": "Weekly sync"
    }

    result = adapter._parse_event(raw_event)

    assert result["id"] == "123"
    assert result["title"] == "Team Meeting"
    assert result["location"] == "Conference Room"
```

### 9. Run quality gate

```bash
uv run ruff check app/ tests/ && uv run python -m compileall app/ && uv run pytest tests/ -v
```

### 10. Update documentation

- Add setup instructions to `README.md`
- Document authentication method
- Add to `.env.example` with comments

## Checklist

- [ ] Adapter file created implementing CalendarProvider Protocol
- [ ] All Protocol methods implemented as `async def`
- [ ] Sync SDK calls wrapped in `run_in_executor`
- [ ] Authentication implemented (OAuth, service account, API key)
- [ ] Event parsing logic implemented
- [ ] Configuration added to Settings
- [ ] DI container updated with provider selection
- [ ] Environment files updated
- [ ] Integration tests added
- [ ] Unit tests added for parsing
- [ ] Quality gate passes
- [ ] Documentation updated

## Example: Adding Apple Calendar

1. Create `app/infrastructure/calendar/apple_adapter.py`
2. Use `caldav` library for CalDAV protocol
3. Implement OAuth 2.0 authentication
4. Wrap sync CalDAV calls in `run_in_executor`
5. Parse CalDAV events to domain format
6. Add `CALENDAR_PROVIDER=apple` option
7. Add `APPLE_CALENDAR_TOKEN` to config
8. Integration tests
9. Update README with OAuth setup instructions

## Example: Adding CalDAV (generic)

1. Create `app/infrastructure/calendar/caldav_adapter.py`
2. Use `caldav` library
3. Support username/password authentication
4. Parse CalDAV XML to domain format
5. Add `CALENDAR_PROVIDER=caldav` option
6. Add `CALDAV_URL`, `CALDAV_USERNAME`, `CALDAV_PASSWORD` to config
7. Integration tests with mock CalDAV server
8. Update README

## Notes

- All calendar SDKs are sync — always use `run_in_executor`
- Handle authentication token refresh if needed
- Parse recurring events correctly
- Handle timezone conversions
- Log errors but don't crash — calendar failures shouldn't break the app
- Follow Google-style docstrings
