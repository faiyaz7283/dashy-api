"""Unit tests for calendar domain models."""

from datetime import datetime

import pytest

from app.domain.calendar.models import DateRange, RecurrenceRule


class TestDateRange:
    """Tests for DateRange value object."""

    def test_overlapping_ranges(self) -> None:
        """Test that overlapping ranges are detected."""
        range1 = DateRange(start=datetime(2026, 1, 1), end=datetime(2026, 1, 10))
        range2 = DateRange(start=datetime(2026, 1, 5), end=datetime(2026, 1, 15))
        assert range1.overlaps(range2)
        assert range2.overlaps(range1)

    def test_non_overlapping_ranges(self) -> None:
        """Test that non-overlapping ranges are not detected as overlapping."""
        range1 = DateRange(start=datetime(2026, 1, 1), end=datetime(2026, 1, 10))
        range2 = DateRange(start=datetime(2026, 1, 11), end=datetime(2026, 1, 20))
        assert not range1.overlaps(range2)
        assert not range2.overlaps(range1)

    def test_adjacent_ranges_do_not_overlap(self) -> None:
        """Test that adjacent ranges (touching but not overlapping) don't overlap."""
        range1 = DateRange(start=datetime(2026, 1, 1), end=datetime(2026, 1, 10))
        range2 = DateRange(start=datetime(2026, 1, 10), end=datetime(2026, 1, 20))
        # They share the boundary point, so they do overlap
        assert range1.overlaps(range2)

    def test_contains_datetime(self) -> None:
        """Test that contains() correctly identifies datetime within range."""
        date_range = DateRange(start=datetime(2026, 1, 1), end=datetime(2026, 1, 31))
        assert date_range.contains(datetime(2026, 1, 15))
        assert not date_range.contains(datetime(2026, 2, 1))

    def test_contains_boundary_dates(self) -> None:
        """Test that contains() includes boundary dates."""
        date_range = DateRange(start=datetime(2026, 1, 1), end=datetime(2026, 1, 31))
        assert date_range.contains(datetime(2026, 1, 1))
        assert date_range.contains(datetime(2026, 1, 31))

    def test_date_range_is_immutable(self) -> None:
        """Test that DateRange is immutable (frozen dataclass)."""
        date_range = DateRange(start=datetime(2026, 1, 1), end=datetime(2026, 1, 31))
        with pytest.raises(AttributeError):
            date_range.start = datetime(2026, 2, 1)  # type: ignore


class TestRecurrenceRule:
    """Tests for RecurrenceRule value object."""

    def test_parse_simple_weekly_rule(self) -> None:
        """Test parsing simple weekly recurrence rule."""
        rule = RecurrenceRule.from_rrule_string("RRULE:FREQ=WEEKLY")
        assert rule.frequency == "WEEKLY"
        assert rule.interval == 1
        assert rule.by_day == ()
        assert rule.count is None
        assert rule.until is None

    def test_parse_weekly_with_days(self) -> None:
        """Test parsing weekly rule with specific days."""
        rule = RecurrenceRule.from_rrule_string("RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR")
        assert rule.frequency == "WEEKLY"
        assert rule.by_day == ("MO", "WE", "FR")

    def test_parse_daily_with_interval(self) -> None:
        """Test parsing daily rule with interval."""
        rule = RecurrenceRule.from_rrule_string("RRULE:FREQ=DAILY;INTERVAL=2")
        assert rule.frequency == "DAILY"
        assert rule.interval == 2

    def test_parse_with_count(self) -> None:
        """Test parsing rule with count."""
        rule = RecurrenceRule.from_rrule_string("RRULE:FREQ=WEEKLY;COUNT=10")
        assert rule.frequency == "WEEKLY"
        assert rule.count == 10

    def test_parse_with_until(self) -> None:
        """Test parsing rule with until date."""
        rule = RecurrenceRule.from_rrule_string("RRULE:FREQ=WEEKLY;UNTIL=20261231T235959Z")
        assert rule.frequency == "WEEKLY"
        assert rule.until is not None
        assert rule.until.year == 2026
        assert rule.until.month == 12
        assert rule.until.day == 31

    def test_to_rrule_string_simple(self) -> None:
        """Test converting simple rule to RRULE string."""
        rule = RecurrenceRule(frequency="WEEKLY")
        assert rule.to_rrule_string() == "RRULE:FREQ=WEEKLY"

    def test_to_rrule_string_with_days(self) -> None:
        """Test converting rule with days to RRULE string."""
        rule = RecurrenceRule(frequency="WEEKLY", by_day=("MO", "WE", "FR"))
        assert rule.to_rrule_string() == "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"

    def test_to_rrule_string_with_interval(self) -> None:
        """Test converting rule with interval to RRULE string."""
        rule = RecurrenceRule(frequency="DAILY", interval=2)
        assert rule.to_rrule_string() == "RRULE:FREQ=DAILY;INTERVAL=2"

    def test_roundtrip_conversion(self) -> None:
        """Test that parsing and converting back produces same rule."""
        original = "RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,FR;COUNT=10"
        rule = RecurrenceRule.from_rrule_string(original)
        result = rule.to_rrule_string()
        assert result == original
