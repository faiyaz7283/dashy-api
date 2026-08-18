"""Google Calendar adapter implementing CalendarProvider protocol.

Fetches events from Google Calendar API using service account authentication.
Wraps synchronous Google API calls in async using run_in_executor.
"""

import asyncio
from datetime import datetime
from functools import partial

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings
from app.core.logging import get_logger
from app.domain.calendar.models import DateRange

logger = get_logger(__name__)

# Scopes for read-only access to Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class GoogleCalendarAdapter:
    """Google Calendar API adapter.

    Implements CalendarProvider protocol for fetching events from Google Calendar
    using service account authentication.
    """

    def __init__(self, credentials_path: str | None = None) -> None:
        """Initialize Google Calendar adapter.

        Args:
            credentials_path: Path to service account JSON file.
                Defaults to settings.GOOGLE_SERVICE_ACCOUNT_JSON.
        """
        self.credentials_path = credentials_path or settings.GOOGLE_SERVICE_ACCOUNT_JSON

    def _get_credentials(self) -> service_account.Credentials | None:
        """Load service account credentials from JSON file.

        Returns:
            Service account credentials or None if file doesn't exist.
        """
        if not self.credentials_path:
            return None
        try:
            return service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
        except Exception as e:
            logger.error("credentials_load_error", error=str(e))
            return None

    def _fetch_events_sync(
        self, calendar_id: str, time_min: datetime, time_max: datetime
    ) -> list[dict]:
        """Synchronously fetch events from Google Calendar API.

        Args:
            calendar_id: Google Calendar ID (email address).
            time_min: Start of date range.
            time_max: End of date range.

        Returns:
            List of raw event dicts from Google Calendar API.
        """
        credentials = self._get_credentials()
        if not credentials:
            logger.warning("no_credentials", calendar_id=calendar_id)
            return []

        try:
            service = build("calendar", "v3", credentials=credentials)

            # Fetch master recurring events to get RRULE definitions
            recurring_rules = self._fetch_recurring_rules_sync(
                service, calendar_id, time_min, time_max
            )

            # Fetch expanded instances
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min.isoformat() + "Z",
                    timeMax=time_max.isoformat() + "Z",
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            # Attach recurring rules to events
            for event in events:
                recurring_event_id = event.get("recurringEventId")
                if recurring_event_id and recurring_event_id in recurring_rules:
                    event["_recurring_rule"] = recurring_rules[recurring_event_id]

            return events

        except HttpError as e:
            logger.error("google_calendar_api_error", calendar_id=calendar_id, error=str(e))
            return []
        except Exception as e:
            logger.error("google_calendar_unexpected_error", calendar_id=calendar_id, error=str(e))
            return []

    def _fetch_recurring_rules_sync(
        self, service, calendar_id: str, time_min: datetime, time_max: datetime
    ) -> dict[str, str]:
        """Fetch master recurring events to extract RRULE definitions.

        Args:
            service: Google Calendar API service instance.
            calendar_id: The calendar ID to fetch from.
            time_min: Start of the date range.
            time_max: End of the date range.

        Returns:
            Dict mapping recurring_event_id to RRULE string.
        """
        recurring_rules: dict[str, str] = {}

        try:
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=time_min.isoformat() + "Z",
                    timeMax=time_max.isoformat() + "Z",
                    singleEvents=False,
                    orderBy="startTime",
                )
                .execute()
            )

            for event in events_result.get("items", []):
                recurrence_rules = event.get("recurrence", [])
                if recurrence_rules:
                    event_id = event.get("id", "")
                    recurring_rules[event_id] = recurrence_rules[0]

        except HttpError as e:
            logger.error("fetch_recurring_rules_error", calendar_id=calendar_id, error=str(e))

        return recurring_rules

    async def fetch_events(
        self,
        calendar_id: str,
        date_range: DateRange,
    ) -> list[dict]:
        """Fetch calendar events within date range.

        Wraps synchronous Google API call in async using run_in_executor.

        Args:
            calendar_id: Calendar identifier (e.g., email address).
            date_range: Date range to query.

        Returns:
            List of dictionaries containing event data.
        """
        loop = asyncio.get_running_loop()
        fetch_func = partial(
            self._fetch_events_sync,
            calendar_id,
            date_range.start,
            date_range.end,
        )
        return await loop.run_in_executor(None, fetch_func)
