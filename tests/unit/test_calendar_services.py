"""Unit tests for calendar domain services."""

from app.api.models.calendar import Attendee, CalendarEvent
from app.domain.calendar.services import deduplicate_events


class TestDeduplicateEvents:
    """Tests for event deduplication logic."""

    def test_deduplicate_single_event(self) -> None:
        """Test that single event passes through unchanged."""
        events = [
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["alice"],
                attendees=[
                    Attendee(
                        email="alice@example.com",
                        display_name="Alice",
                        status="accepted",
                        color="#FF0000",
                    )
                ],
            )
        ]
        result = deduplicate_events(events)
        assert len(result) == 1
        assert result[0].id == "event1"

    def test_deduplicate_duplicate_events(self) -> None:
        """Test that duplicate events are merged."""
        events = [
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["alice"],
                attendees=[
                    Attendee(
                        email="alice@example.com",
                        display_name="Alice",
                        status="accepted",
                        color="#FF0000",
                    )
                ],
            ),
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["bob"],
                attendees=[
                    Attendee(
                        email="bob@example.com",
                        display_name="Bob",
                        status="accepted",
                        color="#00FF00",
                    )
                ],
            ),
        ]
        result = deduplicate_events(events)
        assert len(result) == 1
        assert set(result[0].members) == {"alice", "bob"}
        assert len(result[0].attendees) == 2

    def test_deduplicate_preserves_unique_events(self) -> None:
        """Test that unique events are preserved."""
        events = [
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["alice"],
            ),
            CalendarEvent(
                id="event2",
                title="Lunch",
                start="2026-01-15T12:00:00",
                end="2026-01-15T13:00:00",
                members=["bob"],
            ),
        ]
        result = deduplicate_events(events)
        assert len(result) == 2

    def test_deduplicate_sorts_by_start_time(self) -> None:
        """Test that deduplicated events are sorted by start time."""
        events = [
            CalendarEvent(
                id="event2",
                title="Lunch",
                start="2026-01-15T12:00:00",
                end="2026-01-15T13:00:00",
                members=["bob"],
            ),
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["alice"],
            ),
        ]
        result = deduplicate_events(events)
        assert result[0].id == "event1"
        assert result[1].id == "event2"

    def test_deduplicate_merges_attendees_by_email(self) -> None:
        """Test that attendees are merged by email address."""
        events = [
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["alice"],
                attendees=[
                    Attendee(
                        email="alice@example.com",
                        display_name="Alice",
                        status="accepted",
                        color="#FF0000",
                    ),
                    Attendee(
                        email="charlie@example.com",
                        display_name="Charlie",
                        status="tentative",
                        color="#0000FF",
                    ),
                ],
            ),
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["bob"],
                attendees=[
                    Attendee(
                        email="bob@example.com",
                        display_name="Bob",
                        status="accepted",
                        color="#00FF00",
                    ),
                    Attendee(
                        email="charlie@example.com",
                        display_name="Charlie",
                        status="declined",
                        color="#0000FF",
                    ),
                ],
            ),
        ]
        result = deduplicate_events(events)
        assert len(result) == 1
        # Should have 3 unique attendees (alice, bob, charlie)
        assert len(result[0].attendees) == 3
        emails = {a.email for a in result[0].attendees}
        assert emails == {"alice@example.com", "bob@example.com", "charlie@example.com"}

    def test_deduplicate_prefers_non_null_description(self) -> None:
        """Test that non-null description is preferred when merging."""
        events = [
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["alice"],
                description=None,
            ),
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["bob"],
                description="Important meeting",
            ),
        ]
        result = deduplicate_events(events)
        assert result[0].description == "Important meeting"

    def test_deduplicate_prefers_non_null_location(self) -> None:
        """Test that non-null location is preferred when merging."""
        events = [
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["alice"],
                location=None,
            ),
            CalendarEvent(
                id="event1",
                title="Meeting",
                start="2026-01-15T10:00:00",
                end="2026-01-15T11:00:00",
                members=["bob"],
                location="Conference Room A",
            ),
        ]
        result = deduplicate_events(events)
        assert result[0].location == "Conference Room A"
