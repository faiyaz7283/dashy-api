"""Tests for calendar domain services and mock data."""

from datetime import datetime

from app.api.models.calendar import Attendee, CalendarEvent
from app.domain.calendar.services import (
    deduplicate_events,
    parse_iso_date,
    parse_recurring_info,
)
from app.infrastructure.mock_data import get_mock_calendar_events


class TestParseIsoDate:
    """Tests for ISO date parsing utility."""

    def test_parse_date_only(self):
        """Test parsing date-only format (YYYY-MM-DD)."""
        result = parse_iso_date("2026-08-15")
        assert result == datetime(2026, 8, 15, 0, 0, 0)

    def test_parse_datetime_format(self):
        """Test parsing datetime format (YYYY-MM-DDTHH:MM:SS)."""
        result = parse_iso_date("2026-08-15T14:30:00")
        assert result == datetime(2026, 8, 15, 14, 30, 0)

    def test_parse_datetime_with_z_suffix(self):
        """Test parsing datetime with Z suffix."""
        result = parse_iso_date("2026-08-15T14:30:00Z")
        assert result == datetime(2026, 8, 15, 14, 30, 0)


class TestMockCalendarEvents:
    """Tests for mock calendar generation with date ranges."""

    def test_default_range(self):
        """Test mock calendar with no dates defaults to current week."""
        result = get_mock_calendar_events()
        assert len(result) > 0
        # Check that events are in Google Calendar API format
        assert "id" in result[0]
        assert "summary" in result[0]
        assert "start" in result[0]
        assert "end" in result[0]

    def test_custom_date_range(self):
        """Test mock calendar with custom date range."""
        result = get_mock_calendar_events("2026-09-01", "2026-09-07")
        assert len(result) > 0

    def test_single_day_range(self):
        """Test mock calendar with single day range."""
        result = get_mock_calendar_events("2026-08-15", "2026-08-15")
        # Single day may or may not have events depending on templates
        assert isinstance(result, list)

    def test_month_range(self):
        """Test mock calendar with full month range."""
        result = get_mock_calendar_events("2026-08-01", "2026-08-31")
        assert len(result) > 10  # Should have many events for a month

    def test_year_range(self):
        """Test mock calendar with full year range."""
        result = get_mock_calendar_events("2026-01-01", "2026-12-31")
        assert len(result) > 100  # Should have many events for a year

    def test_events_sorted_by_start_time(self):
        """Test that mock events are sorted by start time."""
        result = get_mock_calendar_events("2026-08-01", "2026-08-31")
        start_times = []
        for e in result:
            if "dateTime" in e["start"]:
                start_times.append(e["start"]["dateTime"])
            else:
                start_times.append(e["start"]["date"] + "T00:00:00")
        assert start_times == sorted(start_times)

    def test_events_have_attendees(self):
        """Test that all mock events have attendees."""
        result = get_mock_calendar_events("2026-08-01", "2026-08-07")
        for event in result:
            assert "attendees" in event
            assert isinstance(event["attendees"], list)
            assert len(event["attendees"]) > 0

    def test_all_day_events_flagged(self):
        """Test that all-day events are properly flagged."""
        result = get_mock_calendar_events("2026-08-01", "2026-08-31")
        all_day_events = [e for e in result if "date" in e["start"]]
        timed_events = [e for e in result if "dateTime" in e["start"]]
        assert len(all_day_events) > 0  # Should have some all-day events
        assert len(timed_events) > 0  # Should have some timed events


class TestDeduplicateEvents:
    """Tests for event deduplication logic."""

    def test_no_duplicates(self):
        """Test deduplication with no duplicates."""
        event1 = CalendarEvent(
            id="1",
            title="Event 1",
            start="2026-08-15T10:00:00",
            end="2026-08-15T11:00:00",
            all_day=False,
            members=["faiyaz"],
            attendees=[],
        )
        event2 = CalendarEvent(
            id="2",
            title="Event 2",
            start="2026-08-15T14:00:00",
            end="2026-08-15T15:00:00",
            all_day=False,
            members=["trisha"],
            attendees=[],
        )
        result = deduplicate_events([event1, event2])
        assert len(result) == 2

    def test_merge_duplicates(self):
        """Test deduplication merges events with same ID."""
        event1 = CalendarEvent(
            id="1",
            title="Shared Event",
            start="2026-08-15T10:00:00",
            end="2026-08-15T11:00:00",
            all_day=False,
            members=["faiyaz"],
            attendees=[
                Attendee(
                    member_key="faiyaz",
                    email="faiyaz@gmail.com",
                    display_name="Faiyaz",
                    status="accepted",
                    color="#4A90E2",
                )
            ],
        )
        event2 = CalendarEvent(
            id="1",
            title="Shared Event",
            start="2026-08-15T10:00:00",
            end="2026-08-15T11:00:00",
            all_day=False,
            members=["trisha"],
            attendees=[
                Attendee(
                    member_key="trisha",
                    email="trisha@gmail.com",
                    display_name="Trisha",
                    status="accepted",
                    color="#E24A8D",
                )
            ],
        )
        result = deduplicate_events([event1, event2])
        assert len(result) == 1
        assert "faiyaz" in result[0].members
        assert "trisha" in result[0].members
        assert len(result[0].attendees) == 2

    def test_prefer_non_null_values(self):
        """Test deduplication prefers non-null description/location."""
        event1 = CalendarEvent(
            id="1",
            title="Event",
            start="2026-08-15T10:00:00",
            end="2026-08-15T11:00:00",
            all_day=False,
            members=["faiyaz"],
            description="Description from event 1",
            location=None,
            attendees=[],
        )
        event2 = CalendarEvent(
            id="1",
            title="Event",
            start="2026-08-15T10:00:00",
            end="2026-08-15T11:00:00",
            all_day=False,
            members=["trisha"],
            description=None,
            location="Location from event 2",
            attendees=[],
        )
        result = deduplicate_events([event1, event2])
        assert result[0].description == "Description from event 1"
        assert result[0].location == "Location from event 2"


class TestParseRecurringInfo:
    """Tests for recurring event metadata parsing."""

    def test_parse_recurring_info_with_direct_rule(self):
        """Test parsing recurring info when rule is directly on event."""
        gcal_event = {
            "id": "event1",
            "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"],
        }
        recurring_rules = {}
        recurring_id, is_instance, rule = parse_recurring_info(gcal_event, recurring_rules)
        assert recurring_id is None
        assert is_instance is False
        assert rule == "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"

    def test_parse_recurring_info_with_lookup(self):
        """Test parsing recurring info from lookup map."""
        gcal_event = {
            "id": "instance1",
            "recurringEventId": "master1",
        }
        recurring_rules = {"master1": "RRULE:FREQ=DAILY"}
        recurring_id, is_instance, rule = parse_recurring_info(gcal_event, recurring_rules)
        assert recurring_id == "master1"
        assert is_instance is True
        assert rule == "RRULE:FREQ=DAILY"

    def test_parse_recurring_info_non_recurring(self):
        """Test parsing recurring info for non-recurring event."""
        gcal_event = {"id": "event1"}
        recurring_rules = {}
        recurring_id, is_instance, rule = parse_recurring_info(gcal_event, recurring_rules)
        assert recurring_id is None
        assert is_instance is False
        assert rule is None
