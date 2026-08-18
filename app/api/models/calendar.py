"""Calendar API models.

Pydantic models for calendar API requests and responses.
"""

from typing import Literal

from pydantic import BaseModel


class Attendee(BaseModel):
    """An event attendee with optional family member association.

    Attributes:
        member_key: Associated family member key, null for external guests.
        email: Attendee's email address.
        display_name: Name to display for this attendee.
        status: RSVP response status.
        color: Color code for this attendee (member color or default grey).
    """

    member_key: str | None = None
    email: str
    display_name: str
    status: Literal["accepted", "declined", "tentative", "needsAction"]
    color: str


class CalendarEvent(BaseModel):
    """A calendar event with full details.

    Attributes:
        id: Unique event identifier.
        title: Event title/summary.
        start: Event start time (ISO format).
        end: Event end time (ISO format).
        all_day: Whether this is an all-day event.
        members: List of family member keys associated with this event.
        description: Event description, if any.
        location: Event location, if any.
        organizer: Family member key of the event organizer, if any.
        attendees: List of event attendees.
        recurring_event_id: ID of the recurring event series, if any.
        is_recurring_instance: Whether this is an instance of a recurring event.
        recurrence_rule: Recurrence rule (RRULE), if any.
    """

    id: str
    title: str
    start: str
    end: str
    all_day: bool = False
    members: list[str] = []
    description: str | None = None
    location: str | None = None
    organizer: str | None = None
    attendees: list[Attendee] = []
    recurring_event_id: str | None = None
    is_recurring_instance: bool = False
    recurrence_rule: str | None = None


class WeekCalendar(BaseModel):
    """Calendar events for a specific week.

    Attributes:
        week_start: Start date of the week (ISO date, Monday).
        week_end: End date of the week (ISO date, Sunday).
        events: List of calendar events in this week.
    """

    week_start: str
    week_end: str
    events: list[CalendarEvent]
