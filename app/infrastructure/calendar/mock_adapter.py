"""Mock calendar adapter implementing CalendarProvider protocol.

Returns mock calendar data for development and testing.
"""

from app.domain.calendar.models import DateRange
from app.infrastructure.mock_data import get_mock_calendar_events


class MockCalendarAdapter:
    """Mock calendar adapter.

    Implements CalendarProvider protocol for returning mock calendar data.
    Used in development and testing environments.
    """

    async def fetch_events(
        self,
        calendar_id: str,
        date_range: DateRange,
    ) -> list[dict]:
        """Fetch mock calendar events within date range.

        Args:
            calendar_id: Calendar identifier (ignored for mock data).
            date_range: Date range to query.

        Returns:
            List of dictionaries containing mock event data in Google Calendar API format.
        """
        start_date = date_range.start.strftime("%Y-%m-%d")
        end_date = date_range.end.strftime("%Y-%m-%d")

        return get_mock_calendar_events(start_date, end_date)
