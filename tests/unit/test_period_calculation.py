"""Unit tests for period calculation utilities.

Tests the pure functions in app.domain.chores.utils.periods
for all recurrence frequencies and edge cases.
"""

from datetime import date

from app.domain.chores.schemas import RecurrenceRule
from app.domain.chores.utils.periods import (
    _advance_one_month,
    _get_nth_weekday,
    calculate_period,
    get_next_occurrence,
)


class TestCalculatePeriodDaily:
    """Tests for daily frequency period calculation."""

    def test_daily_returns_same_date(self) -> None:
        """Test that daily frequency returns the reference date as both start and end."""
        rule = RecurrenceRule(frequency="daily", time="18:00")
        ref = date(2026, 8, 26)

        start, end = calculate_period(rule, ref)

        assert start == ref
        assert end == ref


class TestCalculatePeriodWeekly:
    """Tests for weekly frequency period calculation."""

    def test_weekly_target_in_future(self) -> None:
        """Test weekly when target day is later this week."""
        # Wednesday Aug 26, target Monday (0) → next Monday Aug 31
        rule = RecurrenceRule(frequency="weekly", day_of_week=[0], time="10:00")
        ref = date(2026, 8, 26)  # Wednesday

        start, end = calculate_period(rule, ref)

        assert start == date(2026, 8, 31)
        assert end == date(2026, 8, 31)

    def test_weekly_target_is_today(self) -> None:
        """Test weekly when reference date is the target day."""
        # Monday Aug 31, target Monday (0) → same day
        rule = RecurrenceRule(frequency="weekly", day_of_week=[0], time="10:00")
        ref = date(2026, 8, 31)  # Monday

        start, end = calculate_period(rule, ref)

        assert start == date(2026, 8, 31)
        assert end == date(2026, 8, 31)

    def test_weekly_target_in_past_wraps_to_next_week(self) -> None:
        """Test weekly when target day already passed this week."""
        # Tuesday Sep 1, target Monday (0) → next Monday Sep 7
        rule = RecurrenceRule(frequency="weekly", day_of_week=[0], time="10:00")
        ref = date(2026, 9, 1)  # Tuesday

        start, end = calculate_period(rule, ref)

        assert start == date(2026, 9, 7)
        assert end == date(2026, 9, 7)

    def test_weekly_friday(self) -> None:
        """Test weekly with Friday as target."""
        # Wednesday Aug 26, target Friday (4) → Friday Aug 28
        rule = RecurrenceRule(frequency="weekly", day_of_week=[4], time="15:00")
        ref = date(2026, 8, 26)  # Wednesday

        start, end = calculate_period(rule, ref)

        assert start == date(2026, 8, 28)
        assert end == date(2026, 8, 28)


class TestCalculatePeriodMonthly:
    """Tests for monthly frequency period calculation."""

    def test_monthly_fixed_day(self) -> None:
        """Test monthly with fixed day of month."""
        rule = RecurrenceRule(frequency="monthly", day_of_month=15, time="11:00")
        ref = date(2026, 8, 20)

        start, end = calculate_period(rule, ref)

        assert start == date(2026, 8, 15)
        assert end == date(2026, 8, 15)

    def test_monthly_fixed_day_clamped_for_short_month(self) -> None:
        """Test monthly day 31 clamped to February's last day."""
        rule = RecurrenceRule(frequency="monthly", day_of_month=31, time="10:00")
        ref = date(2026, 2, 10)  # Feb 2026 has 28 days

        start, end = calculate_period(rule, ref)

        assert start == date(2026, 2, 28)
        assert end == date(2026, 2, 28)

    def test_monthly_nth_weekday(self) -> None:
        """Test monthly with Nth weekday pattern (first Monday)."""
        # August 2026: first Monday is Aug 3
        rule = RecurrenceRule(
            frequency="monthly", day_of_week=[0], week_of_month=1, time="09:00"
        )
        ref = date(2026, 8, 20)

        start, end = calculate_period(rule, ref)

        assert start == date(2026, 8, 3)
        assert end == date(2026, 8, 3)


class TestCalculatePeriodYearly:
    """Tests for yearly frequency period calculation."""

    def test_yearly_fixed_date(self) -> None:
        """Test yearly with fixed month and day."""
        rule = RecurrenceRule(frequency="yearly", month=1, day_of_month=15, time="09:00")
        ref = date(2026, 8, 20)

        start, end = calculate_period(rule, ref)

        assert start == date(2026, 1, 15)
        assert end == date(2026, 1, 15)

    def test_yearly_nth_weekday(self) -> None:
        """Test yearly with Nth weekday pattern (4th Thursday of November)."""
        # November 2026: 4th Thursday is Nov 26
        rule = RecurrenceRule(
            frequency="yearly", month=11, day_of_week=[3], week_of_month=4, time="12:00"
        )
        ref = date(2026, 8, 20)

        start, end = calculate_period(rule, ref)

        assert start == date(2026, 11, 26)
        assert end == date(2026, 11, 26)


class TestCalculatePeriodOnce:
    """Tests for once frequency period calculation."""

    def test_once_returns_none(self) -> None:
        """Test that once frequency returns None for both start and end."""
        rule = RecurrenceRule(frequency="once", time="10:00")
        ref = date(2026, 8, 26)

        start, end = calculate_period(rule, ref)

        assert start is None
        assert end is None


class TestGetNthWeekday:
    """Tests for the _get_nth_weekday helper."""

    def test_first_monday_august_2026(self) -> None:
        """Test first Monday of August 2026."""
        result = _get_nth_weekday(2026, 8, 0, 1)  # Monday=0, 1st
        assert result == date(2026, 8, 3)

    def test_fourth_thursday_november_2026(self) -> None:
        """Test 4th Thursday of November 2026 (Thanksgiving)."""
        result = _get_nth_weekday(2026, 11, 3, 4)  # Thursday=3, 4th
        assert result == date(2026, 11, 26)

    def test_fifth_occurrence_clamps_to_fourth(self) -> None:
        """Test that 5th occurrence returns 4th when month only has 4."""
        # August 2026 has only 4 Fridays (7, 14, 21, 28)
        result = _get_nth_weekday(2026, 8, 4, 5)  # Friday=4, 5th
        assert result == date(2026, 8, 28)  # Falls back to 4th


class TestAdvanceOneMonth:
    """Tests for the _advance_one_month helper."""

    def test_normal_month_advance(self) -> None:
        """Test advancing from mid-month to next month."""
        result = _advance_one_month(date(2026, 8, 15))
        assert result == date(2026, 9, 15)

    def test_december_wraps_to_january(self) -> None:
        """Test advancing from December wraps to January next year."""
        result = _advance_one_month(date(2026, 12, 10))
        assert result == date(2027, 1, 10)

    def test_day_31_clamped_to_short_month(self) -> None:
        """Test that day 31 is clamped when next month is shorter."""
        result = _advance_one_month(date(2026, 1, 31))
        assert result == date(2026, 2, 28)


class TestGetNextOccurrence:
    """Tests for get_next_occurrence — the trigger for first/next instance."""

    def test_daily_before_configured_time_returns_today(self) -> None:
        """Test daily before configured time returns today."""
        rule = RecurrenceRule(frequency="daily", time="18:00")
        ref = date(2026, 8, 26)

        result = get_next_occurrence(rule, ref, "10:00")

        assert result == date(2026, 8, 26)

    def test_daily_after_configured_time_returns_tomorrow(self) -> None:
        """Test daily after configured time returns tomorrow."""
        rule = RecurrenceRule(frequency="daily", time="18:00")
        ref = date(2026, 8, 26)

        result = get_next_occurrence(rule, ref, "19:00")

        assert result == date(2026, 8, 27)

    def test_weekly_on_target_day_before_time_returns_today(self) -> None:
        """Test weekly on target day before configured time returns today."""
        rule = RecurrenceRule(frequency="weekly", day_of_week=[0], time="10:00")
        ref = date(2026, 8, 31)  # Monday

        result = get_next_occurrence(rule, ref, "08:00")

        assert result == date(2026, 8, 31)

    def test_weekly_on_target_day_after_time_returns_next_week(self) -> None:
        """Test weekly on target day after configured time returns next week."""
        rule = RecurrenceRule(frequency="weekly", day_of_week=[0], time="10:00")
        ref = date(2026, 8, 31)  # Monday

        result = get_next_occurrence(rule, ref, "11:00")

        assert result == date(2026, 9, 7)

    def test_weekly_not_on_target_day_returns_next_target(self) -> None:
        """Test weekly when not on target day returns next occurrence."""
        rule = RecurrenceRule(frequency="weekly", day_of_week=[0], time="10:00")
        ref = date(2026, 8, 26)  # Wednesday

        result = get_next_occurrence(rule, ref, "15:00")

        assert result == date(2026, 8, 31)  # Next Monday

    def test_once_returns_same_date(self) -> None:
        """Test once frequency returns the reference date."""
        rule = RecurrenceRule(frequency="once", time="10:00")
        ref = date(2026, 8, 26)

        result = get_next_occurrence(rule, ref, "10:00")

        assert result == date(2026, 8, 26)

    def test_monthly_advances_to_next_month(self) -> None:
        """Test monthly after target date advances to next month."""
        rule = RecurrenceRule(frequency="monthly", day_of_month=15, time="11:00")
        ref = date(2026, 8, 20)  # Past the 15th

        result = get_next_occurrence(rule, ref, "12:00")

        assert result == date(2026, 9, 15)
