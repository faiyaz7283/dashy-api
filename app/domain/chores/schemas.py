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
    - weekly: requires day_of_week
    - monthly: requires day_of_month OR (day_of_week + week_of_month)
    - yearly: requires month + (day_of_month OR (day_of_week + week_of_month))

    Examples:
        Daily at 8am:
            {"frequency": "daily", "time": "08:00"}
        Weekly on Monday at 9am:
            {"frequency": "weekly", "day_of_week": 1, "time": "09:00"}
        Monthly on 3rd at 10am:
            {"frequency": "monthly", "day_of_month": 3, "time": "10:00"}
        Monthly first Monday at 8am:
            {"frequency": "monthly", "day_of_week": 1, "week_of_month": 1, "time": "08:00"}
        Yearly on Jan 15th at 9am:
            {"frequency": "yearly", "month": 1, "day_of_month": 15, "time": "09:00"}
        Yearly 4th Thursday Nov at 12pm:
            {
                "frequency": "yearly",
                "month": 11,
                "day_of_week": 3,
                "week_of_month": 4,
                "time": "12:00"
            }

    Attributes:
        frequency: How often the chore recurs.
        time: Time of day in HH:MM 24-hour format (required for all frequencies).
        day_of_week: Day of week (0=Monday, 6=Sunday). Required for weekly.
        day_of_month: Day of month (1-31). Required for monthly/yearly with fixed date.
        week_of_month: Week of month (1-5). Used with day_of_week for "first Monday" patterns.
        month: Month (1-12). Required for yearly.
    """

    frequency: Literal["once", "daily", "weekly", "monthly", "yearly"]
    time: str

    day_of_week: int | None = None
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
        if self.frequency in ("once", "daily"):
            pass
        elif self.frequency == "weekly":
            if self.day_of_week is None:
                raise ValueError("weekly frequency requires day_of_week")
        elif self.frequency == "monthly":
            if self.day_of_month is None and (
                self.day_of_week is None or self.week_of_month is None
            ):
                raise ValueError(
                    "monthly frequency requires either day_of_month OR "
                    "(day_of_week + week_of_month)"
                )
        elif self.frequency == "yearly":
            if self.month is None:
                raise ValueError("yearly frequency requires month")
            if self.day_of_month is None and (
                self.day_of_week is None or self.week_of_month is None
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
