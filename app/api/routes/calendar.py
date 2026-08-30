"""Calendar API routes.

Provides endpoints for fetching calendar events.
"""

from fastapi import APIRouter, Depends
from googleapiclient.errors import HttpError

from app.api.deps import CacheDep, CalendarProviderDep, FamilyServiceDep
from app.api.models.calendar import WeekCalendar
from app.api.models.requests import CalendarQuery
from app.config import settings
from app.core.cache import RetryConfig
from app.core.logging import get_logger
from app.domain.calendar.services import (
    deduplicate_events,
    get_default_week_dates,
    parse_event,
    parse_iso_date,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/calendar", tags=["calendar"])

# Retry config for calendar API calls
CALENDAR_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    backoff_seconds=[1.0, 2.0, 4.0],
    transient_errors=(HttpError, ConnectionError, TimeoutError, OSError),
)


@router.get("", response_model=WeekCalendar)
async def get_calendar(
    calendar_provider: CalendarProviderDep,
    family_service: FamilyServiceDep,
    cache: CacheDep,
    query: CalendarQuery = Depends(),
) -> WeekCalendar:
    """Get calendar events for a date range.

    Uses stale-while-revalidate pattern: fresh cache → stale cache → fetch with retry.
    On success, caches result with both fresh and stale TTLs.

    If start_date and end_date are not provided, defaults to the current week.

    Args:
        calendar_provider: Injected calendar provider instance.
        family_service: Injected family service for reading members from DB.
        cache: Injected cache instance.
        query: Validated query parameters.

    Returns:
        WeekCalendar with events for the specified date range.

    Raises:
        UpstreamServiceError: When all retries fail and no stale cache exists.
    """
    # Determine date range
    if query.start_date and query.end_date:
        time_min = parse_iso_date(query.start_date.isoformat())
        time_max = parse_iso_date(query.end_date.isoformat())
        if "T" not in query.end_date.isoformat():
            time_max = time_max.replace(hour=23, minute=59, second=59)
    else:
        time_min, time_max = get_default_week_dates()

    from app.domain.calendar.models import DateRange

    date_range = DateRange(start=time_min, end=time_max)

    # Build cache key from date range
    start_date_str = query.start_date.isoformat() if query.start_date else None
    end_date_str = query.end_date.isoformat() if query.end_date else None
    cache_key = f"calendar:{start_date_str or 'default'}:{end_date_str or 'default'}"

    async def fetch_calendar_events() -> dict:
        """Fetch fresh calendar events from all family members."""
        # Get family members from database
        family_members_list = await family_service.get_all_members()
        if not family_members_list:
            logger.warning("no_family_members_configured")
            # Return empty calendar
            return WeekCalendar(
                week_start=time_min.strftime("%Y-%m-%d"),
                week_end=time_max.strftime("%Y-%m-%d"),
                events=[],
            ).model_dump()

        # Build family members dict for quick lookup
        family_members = {
            m.id: {"email": m.email, "key": m.id, "color": m.color} for m in family_members_list
        }

        # Fetch events from all family member calendars
        all_events = []

        for member in family_members_list:
            try:
                raw_events = await calendar_provider.fetch_events(member.email, date_range)

                for event in raw_events:
                    recurring_rules = {}
                    if "_recurring_rule" in event:
                        event_id = event.get("recurringEventId", event.get("id"))
                        recurring_rules[event_id] = event["_recurring_rule"]

                    parsed_event = parse_event(event, member.id, family_members, recurring_rules)
                    if parsed_event:
                        all_events.append(parsed_event)

            except Exception as e:
                logger.error("calendar_fetch_error", member=member.name, error=str(e))
                continue

        # Deduplicate events (merge shared events from multiple calendars)
        deduplicated_events = deduplicate_events(all_events)

        result = WeekCalendar(
            week_start=time_min.strftime("%Y-%m-%d"),
            week_end=time_max.strftime("%Y-%m-%d"),
            events=deduplicated_events,
        )

        return result.model_dump()

    cached_data = await cache.fetch(
        key=cache_key,
        fetcher=fetch_calendar_events,
        fresh_ttl=settings.CALENDAR_CACHE_TTL,
        stale_ttl=settings.CALENDAR_STALE_TTL,
        retry_config=CALENDAR_RETRY_CONFIG,
        service_name="google-calendar",
    )

    return WeekCalendar(**cached_data)
