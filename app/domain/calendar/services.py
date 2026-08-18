"""Calendar domain services.

Pure business logic for calendar data processing.
"""

from datetime import datetime, timedelta

from app.api.models.calendar import Attendee, CalendarEvent
from app.domain.calendar.models import DateRange, RecurrenceRule


def get_default_week_dates() -> tuple[datetime, datetime]:
    """Get Monday 00:00 and Sunday 23:59 of the current week.

    Returns:
        Tuple of (monday, sunday) datetimes for the current week.
    """
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59)
    return monday, sunday


def parse_iso_date(date_str: str) -> datetime:
    """Parse an ISO format date string to datetime.

    Args:
        date_str: ISO format date string (e.g. "2026-08-08" or "2026-08-08T00:00:00").

    Returns:
        Parsed datetime object.
    """
    if "T" in date_str:
        return datetime.fromisoformat(date_str.replace("Z", ""))
    return datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def parse_date_range(start_str: str, end_str: str) -> DateRange:
    """Parse date strings into DateRange.

    Args:
        start_str: Start date string (ISO format).
        end_str: End date string (ISO format).

    Returns:
        DateRange instance.
    """
    start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
    return DateRange(start=start, end=end)


def parse_recurrence_rule(rrule: str) -> RecurrenceRule:
    """Parse RRULE string into RecurrenceRule.

    Args:
        rrule: RRULE string (e.g., "RRULE:FREQ=WEEKLY;BYDAY=MO,WE").

    Returns:
        RecurrenceRule instance.
    """
    return RecurrenceRule.from_rrule_string(rrule)


def parse_attendees(gcal_event: dict, family_members: dict) -> tuple[list[Attendee], str | None]:
    """Extract attendee information from Google Calendar event.

    Args:
        gcal_event: Raw Google Calendar event dict.
        family_members: Dict mapping member_id to member info dicts with 'email', 'key', 'color'.

    Returns:
        Tuple of (attendees list, organizer member key or None).
    """
    attendees = []
    organizer_email = gcal_event.get("organizer", {}).get("email", "")
    organizer_member_key = None

    # Build email-to-member mapping from dict structure
    email_to_member = {
        m["email"]: m["key"] for m in family_members.values() if "email" in m and "key" in m
    }

    for attendee_data in gcal_event.get("attendees", []):
        email = attendee_data.get("email", "")
        display_name = attendee_data.get("displayName", email.split("@")[0])
        status = attendee_data.get("responseStatus", "needsAction")

        member_key = email_to_member.get(email)

        if member_key:
            color = family_members[member_key]["color"]
            if email == organizer_email:
                organizer_member_key = member_key
        else:
            color = "#9ca3af"

        attendees.append(
            Attendee(
                member_key=member_key,
                email=email,
                display_name=display_name,
                status=status,
                color=color,
            )
        )

    return attendees, organizer_member_key


def parse_recurring_info(
    gcal_event: dict, recurring_rules: dict[str, str]
) -> tuple[str | None, bool, str | None]:
    """Extract recurring event metadata.

    Args:
        gcal_event: Raw Google Calendar event dict.
        recurring_rules: Map of recurring_event_id -> RRULE string.

    Returns:
        Tuple of (recurring_event_id, is_recurring_instance, recurrence_rule).
    """
    recurring_event_id = gcal_event.get("recurringEventId")
    recurrence_rules = gcal_event.get("recurrence", [])

    if recurrence_rules:
        recurrence_rule = recurrence_rules[0]
    elif recurring_event_id and recurring_event_id in recurring_rules:
        recurrence_rule = recurring_rules[recurring_event_id]
    else:
        recurrence_rule = None

    is_instance = recurring_event_id is not None

    return recurring_event_id, is_instance, recurrence_rule


def parse_event(
    gcal_event: dict,
    member_key: str,
    family_members: dict,
    recurring_rules: dict[str, str],
) -> CalendarEvent | None:
    """Convert Google Calendar event to CalendarEvent model.

    Args:
        gcal_event: Raw Google Calendar event dict.
        member_key: Family member key whose calendar this came from.
        family_members: Dict of family member configs.
        recurring_rules: Map of recurring_event_id -> RRULE string.

    Returns:
        CalendarEvent with full details, or None if event is cancelled.
    """
    if gcal_event.get("status") == "cancelled":
        return None

    start = gcal_event.get("start", {})
    end = gcal_event.get("end", {})

    if "dateTime" in start:
        start_iso = start["dateTime"]
        end_iso = end.get("dateTime", "")
        all_day = False
    else:
        start_iso = start.get("date", "") + "T00:00:00"
        end_iso = end.get("date", "") + "T23:59:00"
        all_day = True

    attendees, organizer_key = parse_attendees(gcal_event, family_members)
    recurring_event_id, is_instance, recurrence_rule = parse_recurring_info(
        gcal_event, recurring_rules
    )

    return CalendarEvent(
        id=gcal_event.get("id", ""),
        title=gcal_event.get("summary", "Untitled"),
        start=start_iso,
        end=end_iso,
        all_day=all_day,
        members=[member_key],
        description=gcal_event.get("description"),
        location=gcal_event.get("location"),
        organizer=organizer_key,
        attendees=attendees,
        recurring_event_id=recurring_event_id,
        is_recurring_instance=is_instance,
        recurrence_rule=recurrence_rule,
    )


def deduplicate_events(events: list[CalendarEvent]) -> list[CalendarEvent]:
    """Merge duplicate events from multiple family member calendars.

    Args:
        events: List of CalendarEvent objects (may contain duplicates).

    Returns:
        Deduplicated list of events with merged attendees.
    """
    from collections import defaultdict

    events_by_id: dict[str, list[CalendarEvent]] = defaultdict(list)

    for event in events:
        events_by_id[event.id].append(event)

    deduplicated = []

    for event_group in events_by_id.values():
        if len(event_group) == 1:
            deduplicated.append(event_group[0])
        else:
            base_event = event_group[0]

            all_members = set()
            for event in event_group:
                all_members.update(event.members)

            all_attendees_dict: dict[str, Attendee] = {}
            for event in event_group:
                for attendee in event.attendees:
                    all_attendees_dict[attendee.email] = attendee

            description = next((e.description for e in event_group if e.description), None)
            location = next((e.location for e in event_group if e.location), None)
            organizer = next((e.organizer for e in event_group if e.organizer), None)

            merged_event = CalendarEvent(
                id=base_event.id,
                title=base_event.title,
                start=base_event.start,
                end=base_event.end,
                all_day=base_event.all_day,
                members=sorted(all_members),
                description=description,
                location=location,
                organizer=organizer,
                attendees=list(all_attendees_dict.values()),
                recurring_event_id=base_event.recurring_event_id,
                is_recurring_instance=base_event.is_recurring_instance,
                recurrence_rule=base_event.recurrence_rule,
            )

            deduplicated.append(merged_event)

    deduplicated.sort(key=lambda e: e.start)

    return deduplicated
