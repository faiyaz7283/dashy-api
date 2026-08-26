"""Period calculation utilities for chore instance generation.

Single source of truth for period boundary logic. Given a recurrence
rule and a reference date, calculates the period_start and period_end
for chore instances.
"""

from calendar import monthrange
from datetime import date, timedelta

from app.domain.chores.schemas import RecurrenceRule


def calculate_period(
    rule: RecurrenceRule, reference_date: date
) -> tuple[date | None, date | None]:
    """Calculate period boundaries based on recurrence rule.

    Determines the start and end dates of the period that contains
    or follows the reference date, based on the recurrence pattern.

    Args:
        rule: Validated RecurrenceRule with frequency and configuration.
        reference_date: Date to calculate period for (usually today).

    Returns:
        (period_start, period_end) tuple. None for frequency=once.

    Examples:
        Daily: reference_date=Aug 26 → (Aug 26, Aug 26)
        Weekly Mon: reference_date=Wed Aug 26 → (Mon Aug 31, Mon Aug 31)
        Monthly 15th: reference_date=Aug 20 → (Aug 15, Aug 15)
        Yearly Jan 15: reference_date=Aug 20 2026 → (Jan 15 2027, Jan 15 2027)
    """
    if rule.frequency == "once":
        return (None, None)

    if rule.frequency == "daily":
        return (reference_date, reference_date)

    if rule.frequency == "weekly":
        target_weekday = rule.day_of_week
        current_weekday = reference_date.weekday()
        days_diff = target_weekday - current_weekday

        if days_diff < 0:
            days_diff += 7

        target_date = reference_date + timedelta(days=days_diff)
        return (target_date, target_date)

    if rule.frequency == "monthly":
        year = reference_date.year
        month = reference_date.month

        if rule.day_of_month is not None:
            max_day = monthrange(year, month)[1]
            day = min(rule.day_of_month, max_day)
            target_date = date(year, month, day)
            return (target_date, target_date)

        if rule.day_of_week is not None and rule.week_of_month is not None:
            target_date = _get_nth_weekday(
                year, month, rule.day_of_week, rule.week_of_month
            )
            return (target_date, target_date)

    if rule.frequency == "yearly":
        month = rule.month
        year = reference_date.year

        if rule.day_of_month is not None:
            max_day = monthrange(year, month)[1]
            day = min(rule.day_of_month, max_day)
            return (date(year, month, day), date(year, month, day))

        if rule.day_of_week is not None and rule.week_of_month is not None:
            target_date = _get_nth_weekday(
                year, month, rule.day_of_week, rule.week_of_month
            )
            return (target_date, target_date)

    return (None, None)


def _get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Get the Nth occurrence of a weekday in a month.

    Args:
        year: Year.
        month: Month (1-12).
        weekday: Day of week (0=Monday, 6=Sunday).
        n: Occurrence number (1=first, 2=second, etc.).

    Returns:
        Date of the Nth weekday. If the Nth occurrence doesn't exist
        in the month, returns the last occurrence instead.

    Example:
        _get_nth_weekday(2026, 11, 3, 4) → 4th Thursday of November 2026.
    """
    first_day = date(year, month, 1)
    first_weekday = first_day.weekday()

    days_to_target = (weekday - first_weekday) % 7
    first_occurrence = first_day + timedelta(days=days_to_target)

    target_date = first_occurrence + timedelta(weeks=n - 1)

    if target_date.month != month:
        target_date = first_occurrence + timedelta(weeks=n - 2)

    return target_date


def get_next_occurrence(
    rule: RecurrenceRule, from_date: date, from_time: str
) -> date:
    """Calculate the next occurrence date from a given date and time.

    Used for first instance generation (association trigger) and
    next instance after completion.

    Args:
        rule: Validated RecurrenceRule.
        from_date: Starting date to calculate from.
        from_time: Current time in HH:MM format.

    Returns:
        Next occurrence date.

    Logic:
        - If the target day is today and current time < configured time → today.
        - If the target day is today and current time >= configured time → next period.
        - If the target day is not today → next target day (could still be this week).
    """
    if rule.frequency == "once":
        return from_date

    period_start, _ = calculate_period(rule, from_date)

    if period_start is None:
        return from_date

    # If the calculated period is in the past, advance to the next one
    if period_start < from_date:
        if rule.frequency == "daily":
            return from_date + timedelta(days=1)
        if rule.frequency == "weekly":
            return period_start + timedelta(weeks=1)
        if rule.frequency == "monthly":
            next_month_date = _advance_one_month(from_date)
            result, _ = calculate_period(rule, next_month_date)
            return result or from_date
        if rule.frequency == "yearly":
            next_year_date = date(from_date.year + 1, 1, 1)
            result, _ = calculate_period(rule, next_year_date)
            return result or from_date
        return from_date

    # If the calculated period is in the future, return it
    if period_start > from_date:
        return period_start

    # period_start == from_date: check if we're before or after the configured time
    if from_time < rule.time:
        return period_start

    # We're on the target day but after the configured time, advance to next period
    if rule.frequency == "daily":
        return from_date + timedelta(days=1)

    if rule.frequency == "weekly":
        return period_start + timedelta(weeks=1)

    if rule.frequency == "monthly":
        next_month_date = _advance_one_month(from_date)
        result, _ = calculate_period(rule, next_month_date)
        return result or from_date

    if rule.frequency == "yearly":
        next_year_date = date(from_date.year + 1, 1, 1)
        result, _ = calculate_period(rule, next_year_date)
        return result or from_date

    return from_date


def _advance_one_month(from_date: date) -> date:
    """Advance a date by one month, clamping to month boundaries.

    Args:
        from_date: Starting date.

    Returns:
        Date one month later, with day clamped to the new month's max.
    """
    next_month = from_date.month + 1 if from_date.month < 12 else 1
    next_year = from_date.year if from_date.month < 12 else from_date.year + 1
    max_day = monthrange(next_year, next_month)[1]
    day = min(from_date.day, max_day)
    return date(next_year, next_month, day)
