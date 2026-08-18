"""Legacy models module - re-exports from new locations for backward compatibility."""

from app.api.models import (
    Attendee,
    CalendarEvent,
    DailyForecast,
    FamilyMember,
    HourlyForecast,
    WeatherCondition,
    WeatherCurrent,
    WeatherResponse,
    WeekCalendar,
)

__all__ = [
    "Attendee",
    "CalendarEvent",
    "DailyForecast",
    "FamilyMember",
    "HourlyForecast",
    "WeatherCondition",
    "WeatherCurrent",
    "WeatherResponse",
    "WeekCalendar",
]
