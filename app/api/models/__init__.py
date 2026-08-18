"""API models package.

Re-exports all API models for backward compatibility.
"""

from app.api.models.calendar import Attendee, CalendarEvent, WeekCalendar
from app.api.models.family import FamilyMember
from app.api.models.requests import CalendarQuery, WeatherQuery
from app.api.models.weather import (
    DailyForecast,
    HourlyForecast,
    WeatherCondition,
    WeatherCurrent,
    WeatherResponse,
)

__all__ = [
    # Weather
    "WeatherCondition",
    "WeatherCurrent",
    "HourlyForecast",
    "DailyForecast",
    "WeatherResponse",
    # Calendar
    "Attendee",
    "CalendarEvent",
    "WeekCalendar",
    # Family
    "FamilyMember",
    # Requests
    "WeatherQuery",
    "CalendarQuery",
]
