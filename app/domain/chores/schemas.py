"""Pydantic schemas for chore JSON field validation.

Single source of truth for JSON structure validation. These models
validate the recurrence_rule and conditions fields stored as JSON
in the database.
"""

from typing import Literal

from pydantic import BaseModel, model_validator


class RecurrenceRule(BaseModel):
    """Recurrence pattern configuration for chore instances.

    Validates field combinations based on frequency:
    - once: no additional fields required
    - daily: no additional fields required
    - weekly: requires day_of_week (list of days, e.g. [1,3,5] for Mon/Wed/Fri)
    - monthly: requires day_of_month OR (day_of_week + week_of_month)
    - yearly: requires month + (day_of_month OR (day_of_week + week_of_month))

    Examples:
        Daily at 8am:
            {"frequency": "daily", "frequency_interval": 1, "time": "08:00"}
        Every 3 days at 8am:
            {"frequency": "daily", "frequency_interval": 3, "time": "08:00"}
        Weekly on Monday at 9am:
            {"frequency": "weekly", "frequency_interval": 1,
             "day_of_week": [1], "time": "09:00"}
        Biweekly Mon/Wed/Fri:
            {"frequency": "weekly", "frequency_interval": 2,
             "day_of_week": [1, 3, 5], "time": "09:00"}
        Monthly on 3rd at 10am:
            {"frequency": "monthly", "frequency_interval": 1,
             "day_of_month": 3, "time": "10:00"}
        Monthly first Monday at 8am:
            {"frequency": "monthly", "frequency_interval": 1,
             "day_of_week": [1], "week_of_month": 1, "time": "08:00"}
        Yearly on Jan 15th at 9am:
            {"frequency": "yearly", "frequency_interval": 1,
             "month": 1, "day_of_month": 15, "time": "09:00"}

    Attributes:
        frequency: How often the chore recurs.
        frequency_interval: Every N days/weeks/months/years (default 1).
        time: Time of day in HH:MM 24-hour format (required for all frequencies).
        day_of_week: Days of week (0=Monday, 6=Sunday). List for multi-day patterns.
        day_of_month: Day of month (1-31). Required for monthly/yearly with fixed date.
        week_of_month: Week of month (1-5). Used with day_of_week for "first Monday" patterns.
        month: Month (1-12). Required for yearly.
    """

    frequency: Literal["once", "daily", "weekly", "monthly", "yearly"]
    frequency_interval: int = 1
    time: str

    day_of_week: list[int] | None = None
    day_of_month: int | None = None
    week_of_month: int | None = None
    month: int | None = None

    @model_validator(mode="after")
    def validate_recurrence_combinations(self) -> "RecurrenceRule":
        """Validate field combinations based on frequency.

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If required fields are missing for the frequency.
        """
        if self.frequency_interval < 1:
            raise ValueError("frequency_interval must be >= 1")

        if self.frequency in ("once", "daily"):
            pass
        elif self.frequency == "weekly":
            if not self.day_of_week:
                raise ValueError("weekly frequency requires day_of_week (non-empty list)")
        elif self.frequency == "monthly":
            if self.day_of_month is None and (
                not self.day_of_week or self.week_of_month is None
            ):
                raise ValueError(
                    "monthly frequency requires either day_of_month OR "
                    "(day_of_week + week_of_month)"
                )
        elif self.frequency == "yearly":
            if self.month is None:
                raise ValueError("yearly frequency requires month")
            if self.day_of_month is None and (
                not self.day_of_week or self.week_of_month is None
            ):
                raise ValueError(
                    "yearly frequency requires either (month + day_of_month) OR "
                    "(month + day_of_week + week_of_month)"
                )

        return self


class Condition(BaseModel):
    """Single condition for conditional chores.

    Weather conditions:
        {"type": "weather", "metric": "snowfall", "operator": "gt", "value": 0}
        {"type": "weather", "metric": "temperature", "operator": "lt", "value": 32}

    Calendar conditions:
        {"type": "calendar", "event_count": 5, "operator": "gte", "value": 5}
        {"type": "calendar", "event_type": "meeting", "operator": "eq", "value": "meeting"}

    Attributes:
        type: Data source (weather or calendar).
        operator: Comparison operator.
        value: Threshold value for comparison.
        metric: Weather metric (temperature, snowfall, rainfall, wind_speed).
        event_count: Calendar event count threshold.
        event_type: Calendar event type filter.
    """

    type: Literal["weather", "calendar"]
    operator: Literal["gt", "lt", "eq", "gte", "lte", "contains"]
    value: float | str

    metric: Literal["temperature", "snowfall", "rainfall", "wind_speed"] | None = None
    event_count: int | None = None
    event_type: str | None = None

    @model_validator(mode="after")
    def validate_condition_fields(self) -> "Condition":
        """Validate condition-specific fields.

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If required fields are missing for the condition type.
        """
        if self.type == "weather" and self.metric is None:
            raise ValueError("weather condition requires metric")
        if self.type == "calendar" and self.event_count is None and self.event_type is None:
            raise ValueError("calendar condition requires event_count or event_type")
        return self


class ConditionsConfig(BaseModel):
    """Configuration for conditional chore evaluation.

    Example:
        {
            "logic": "and",
            "conditions": [
                {"type": "weather", "metric": "snowfall", "operator": "gt", "value": 0},
                {"type": "weather", "metric": "temperature", "operator": "lt", "value": 32}
            ]
        }

    Attributes:
        logic: How to combine conditions ("and" or "or").
        conditions: List of conditions to evaluate.
    """

    logic: Literal["and", "or"] = "and"
    conditions: list[Condition]
