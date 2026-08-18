"""Calendar domain ports (interfaces).

Defines the contracts for calendar data providers and repositories.
"""

from typing import Protocol

from app.domain.calendar.models import DateRange


class CalendarProvider(Protocol):
    """Protocol for calendar data providers.

    Implementations fetch calendar events from external APIs or mock sources.
    """

    async def fetch_events(
        self,
        calendar_id: str,
        date_range: DateRange,
    ) -> list[dict]:
        """Fetch calendar events within date range.

        Args:
            calendar_id: Calendar identifier (e.g., email address).
            date_range: Date range to query.

        Returns:
            List of dictionaries containing event data.
        """
        ...


class CalendarRepository(Protocol):
    """Protocol for calendar data persistence.

    Implementations store and retrieve cached calendar data.
    """

    async def save_events(
        self,
        calendar_id: str,
        date_range: DateRange,
        events: list[dict],
    ) -> None:
        """Save calendar events to cache.

        Args:
            calendar_id: Calendar identifier.
            date_range: Date range for the events.
            events: Event data to cache.
        """
        ...

    async def get_events(
        self,
        calendar_id: str,
        date_range: DateRange,
    ) -> list[dict] | None:
        """Retrieve cached calendar events.

        Args:
            calendar_id: Calendar identifier.
            date_range: Date range to query.

        Returns:
            Cached event data or None if not found/expired.
        """
        ...
