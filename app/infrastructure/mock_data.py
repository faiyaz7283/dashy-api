"""Mock data generators for development and testing.

Provides realistic mock data for weather, calendar, and family members
when real API credentials are not available or in development mode.
"""

from datetime import datetime, timedelta

from app.api.models.family import FamilyMember
from app.api.models.weather import WeatherResponse


def get_mock_family_members() -> list[FamilyMember]:
    """Generate mock family member data.

    Returns:
        List of FamilyMember objects with mock data.
    """
    return [
        FamilyMember(
            name="Faiyaz",
            key="faiyaz",
            email="faiyaz7283@gmail.com",
            color="#4A90E2",
            initial="F",
            relation="father",
        ),
        FamilyMember(
            name="Trisha",
            key="trisha",
            email="humairaabbasi26@gmail.com",
            color="#E24A8D",
            initial="T",
            relation="mother",
        ),
        FamilyMember(
            name="Arya",
            key="arya",
            email="aryahaider1210@gmail.com",
            color="#4ADE80",
            initial="A",
            relation="daughter",
        ),
        FamilyMember(
            name="Raya",
            key="raya",
            email="rayahaider23@gmail.com",
            color="#FBBF24",
            initial="R",
            relation="daughter",
        ),
    ]


# Member color mapping for mock attendees
MEMBER_COLORS = {
    "faiyaz": "#4A90E2",
    "trisha": "#E24A8D",
    "arya": "#4ADE80",
    "raya": "#FBBF24",
}


def get_mock_calendar_events(
    start_date: str | None = None, end_date: str | None = None
) -> list[dict]:
    """Generate mock calendar events in Google Calendar API format.

    Returns events as raw dicts matching Google Calendar API structure,
    so they can be parsed by the same parse_event() function used for real data.

    Args:
        start_date: Start date in ISO format (e.g. "2026-08-08"). Defaults to current week Monday.
        end_date: End date in ISO format (e.g. "2026-08-08"). Defaults to current week Sunday.

    Returns:
        List of event dicts in Google Calendar API format.
    """
    if start_date and end_date:
        # Parse the requested range
        if "T" in start_date:
            range_start = datetime.fromisoformat(start_date.replace("Z", ""))
        else:
            range_start = datetime.strptime(start_date, "%Y-%m-%d").replace(
                hour=0, minute=0, second=0
            )
        if "T" in end_date:
            range_end = datetime.fromisoformat(end_date.replace("Z", ""))
        else:
            range_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
    else:
        # Default to current week
        today = datetime.now()
        range_start = today - timedelta(days=today.weekday())
        range_start = range_start.replace(hour=0, minute=0, second=0)
        range_end = range_start + timedelta(days=6, hours=23, minutes=59)

    total_days = (range_end - range_start).days + 1

    # Event templates: (day_offset, start_h, start_m, end_h, end_m, title,
    #                   members, all_day, organizer, description, location, recurrence)
    event_templates = [
        (
            0,
            9,
            0,
            9,
            30,
            "Team Standup",
            ["faiyaz"],
            False,
            "faiyaz",
            "Daily sync with the team",
            None,
            "RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR",
        ),
        (
            0,
            10,
            0,
            11,
            0,
            "Morning Yoga",
            ["trisha"],
            False,
            "trisha",
            "Vinyasa flow class",
            "Local Studio",
            None,
        ),
        (
            0,
            16,
            0,
            17,
            30,
            "Soccer Practice",
            ["arya"],
            False,
            "faiyaz",
            "Weekly soccer practice",
            "Community Field",
            "RRULE:FREQ=WEEKLY;BYDAY=MO",
        ),
        (
            1,
            8,
            0,
            9,
            0,
            "Dentist Appt",
            ["faiyaz", "arya"],
            False,
            "faiyaz",
            "Regular checkup for Arya",
            "Dr. Smith's Office",
            None,
        ),
        (
            1,
            9,
            0,
            12,
            0,
            "Preschool",
            ["raya"],
            False,
            "trisha",
            "Morning preschool session",
            "Little Learners Academy",
            "RRULE:FREQ=WEEKLY;BYDAY=TU,TH",
        ),
        (
            1,
            11,
            0,
            12,
            0,
            "Grocery Shopping",
            ["trisha"],
            False,
            "trisha",
            "Weekly grocery run",
            "Whole Foods",
            None,
        ),
        (
            1,
            18,
            0,
            19,
            0,
            "Gym",
            ["faiyaz"],
            False,
            "faiyaz",
            "Workout session",
            "LA Fitness",
            "RRULE:FREQ=WEEKLY;BYDAY=TU",
        ),
        (
            2,
            15,
            0,
            16,
            0,
            "Reading Club",
            ["arya"],
            False,
            "trisha",
            "Book discussion group",
            "Library",
            None,
        ),
        (
            2,
            16,
            0,
            17,
            0,
            "Piano Lesson",
            ["trisha", "arya"],
            False,
            "trisha",
            "Arya's piano lesson",
            "Music School",
            "RRULE:FREQ=WEEKLY;BYDAY=WE",
        ),
        (
            2,
            19,
            0,
            22,
            0,
            "Date Night",
            ["faiyaz", "trisha"],
            False,
            "faiyaz",
            "Weekly date night",
            "Italian Restaurant",
            None,
        ),
        (
            3,
            10,
            0,
            12,
            0,
            "Playdate w/ Lily",
            ["raya"],
            False,
            "trisha",
            "Playdate with Lily from preschool",
            "Lily's House",
            None,
        ),
        (
            3,
            17,
            0,
            18,
            30,
            "Cook Dinner",
            ["trisha"],
            False,
            "trisha",
            "Prepare meals for the week",
            "Home",
            None,
        ),
        (
            4,
            0,
            0,
            23,
            59,
            "Science Fair Project",
            ["arya", "faiyaz"],
            True,
            "faiyaz",
            "Work on Arya's science fair project",
            "Home",
            None,
        ),
        (
            4,
            13,
            0,
            17,
            0,
            "Team Offsite",
            ["faiyaz"],
            False,
            "faiyaz",
            "Quarterly team offsite meeting",
            "Conference Center",
            None,
        ),
        (
            4,
            19,
            0,
            21,
            0,
            "Family Movie Night",
            ["faiyaz", "trisha", "arya", "raya"],
            False,
            "faiyaz",
            "Watch a family movie together",
            "Home",
            "RRULE:FREQ=WEEKLY;BYDAY=FR",
        ),
        (
            5,
            10,
            0,
            12,
            0,
            "Park Visit",
            ["raya", "arya"],
            False,
            "trisha",
            "Visit the playground",
            "Central Park",
            None,
        ),
        (
            5,
            11,
            0,
            13,
            0,
            "Brunch w/ Friends",
            ["trisha", "faiyaz"],
            False,
            "trisha",
            "Brunch with Sarah and Mike",
            "Cafe Downtown",
            None,
        ),
        (
            6,
            11,
            0,
            13,
            0,
            "Meal Prep",
            ["faiyaz", "trisha"],
            False,
            "trisha",
            "Prepare meals for the upcoming week",
            "Home",
            "RRULE:FREQ=WEEKLY;BYDAY=SU",
        ),
        (
            6,
            15,
            0,
            17,
            0,
            "Homework Catch-up",
            ["arya"],
            False,
            "arya",
            "Finish homework assignments",
            "Home",
            None,
        ),
    ]

    events = []
    event_id = 0
    # Repeat the weekly template pattern across the requested range, so long
    # ranges (month/year views) are populated throughout, not just week one.
    for week in range((total_days + 6) // 7):
        for tpl in event_templates:
            (
                day_offset,
                sh,
                sm,
                eh,
                em,
                title,
                members,
                all_day,
                organizer,
                description,
                location,
                recurrence,
            ) = tpl
            actual_day = week * 7 + day_offset
            if actual_day >= total_days:
                continue
            event_id += 1

            event_start = range_start + timedelta(days=actual_day)
            event_start = event_start.replace(hour=sh, minute=sm)
            event_end = range_start + timedelta(days=actual_day)
            event_end = event_end.replace(hour=eh, minute=em)

            if all_day:
                event_start = event_start.replace(hour=0, minute=0)
                event_end = event_end.replace(hour=23, minute=59)

            # Create mock attendees in Google Calendar API format
            attendees = []
            for member_key in members:
                attendees.append({
                    "email": f"{member_key}@gmail.com",
                    "displayName": member_key.capitalize(),
                    "responseStatus": "accepted",
                    "self": member_key == organizer,
                })

            # Build event in Google Calendar API format
            event = {
                "id": str(event_id),
                "summary": title,
                "status": "confirmed",
                "description": description,
                "location": location,
                "creator": {
                    "email": f"{organizer}@gmail.com",
                    "displayName": organizer.capitalize(),
                },
                "organizer": {
                    "email": f"{organizer}@gmail.com",
                    "displayName": organizer.capitalize(),
                },
                "attendees": attendees,
            }

            # Add start/end times in Google Calendar API format
            if all_day:
                event["start"] = {"date": event_start.strftime("%Y-%m-%d")}
                event["end"] = {"date": event_end.strftime("%Y-%m-%d")}
            else:
                event["start"] = {"dateTime": event_start.strftime("%Y-%m-%dT%H:%M:%S")}
                event["end"] = {"dateTime": event_end.strftime("%Y-%m-%dT%H:%M:%S")}

            # Add recurrence rule if present
            if recurrence:
                event["recurrence"] = [recurrence]

            events.append(event)

    return events


def _get_mock_api_responses() -> tuple[dict, list[dict], list[dict]]:
    """Generate mock API response dicts that match One Call API 4.0 structure exactly.

    Returns:
        Tuple of (current_data, hourly_data, daily_data) - raw dicts matching 4.0 API responses.
    """
    from datetime import timezone as tz

    # Eastern Time offset (EDT = UTC-4, EST = UTC-5)
    # For simplicity, use EDT (-4 hours = -14400 seconds)
    tz_offset = -14400
    eastern_tz = tz(timedelta(seconds=tz_offset))
    now = datetime.now(eastern_tz)
    today = now.date()

    # Mock sunrise/sunset times (Eastern)
    sunrise_time = now.replace(hour=6, minute=12, second=0, microsecond=0)
    sunset_time = now.replace(hour=19, minute=48, second=0, microsecond=0)
    sunrise_ts = int(sunrise_time.timestamp())
    sunset_ts = int(sunset_time.timestamp())

    # Current conditions (in Celsius, as OWM returns metric by default)
    current_temp_c = 25.5  # ~78°F
    current_data = {
        "lat": 40.715401,
        "lon": -73.512924,
        "timezone": "America/New_York",
        "timezone_offset": tz_offset,
        "data": [
            {
                "dt": int(now.timestamp()),
                "sunrise": sunrise_ts,
                "sunset": sunset_ts,
                "temp": current_temp_c,
                "feels_like": 26.7,  # ~80°F
                "pressure": 1015.0,
                "humidity": 55,
                "dew_point": 16.7,  # ~62°F
                "uvi": 6.5,
                "clouds": 10,
                "visibility": 10000,
                "wind_speed": 3.8,  # ~8.5 mph
                "wind_deg": 225,
                "wind_gust": 5.4,  # ~12 mph
                "weather": [
                    {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d",
                    }
                ],
                "alerts": [],
            }
        ],
    }

    # Hourly data (48 hours starting from today's midnight)
    hourly_data_list = []
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(48):
        hour_time = today_midnight + timedelta(hours=i)
        hour_ts = int(hour_time.timestamp())
        # Simulate temperature curve: cooler at night, warmer during day
        hour_of_day = hour_time.hour
        if 0 <= hour_of_day < 6:
            temp_c = 18.3  # ~65°F
        elif 6 <= hour_of_day < 12:
            temp_c = 18.3 + (hour_of_day - 6) * 1.5  # warming up
        elif 12 <= hour_of_day < 18:
            temp_c = 25.5  # ~78°F peak
        else:
            temp_c = 25.5 - (hour_of_day - 18) * 1.2  # cooling down

        hourly_data_list.append(
            {
                "dt": hour_ts,
                "temp": temp_c,
                "feels_like": temp_c + 1.1,
                "pressure": 1015.0,
                "humidity": 55 + (hour_of_day % 10),
                "dew_point": 16.7,
                "uvi": max(0, 6.5 - abs(hour_of_day - 12) * 0.5),
                "clouds": 10,
                "visibility": 10000,
                "wind_speed": 3.8 + (hour_of_day % 5) * 0.2,
                "wind_deg": 225,
                "wind_gust": 5.4,
                "weather": [
                    {
                        "id": 800,
                        "main": "Clear",
                        "description": "clear sky",
                        "icon": "01d" if 6 <= hour_of_day < 20 else "01n",
                    }
                ],
                "pop": 0.05,
                "alerts": [],
            }
        )

    # Daily data (19 days starting from today)
    daily_data_list = []
    conditions = ["Clear", "Clouds", "Drizzle", "Rain", "Thunderstorm", "Clouds", "Clear"]
    for i in range(19):
        day_date = today + timedelta(days=i)
        # Use Eastern-aware datetimes so timestamps align with hourly data
        day_midnight = datetime.combine(day_date, datetime.min.time(), tzinfo=eastern_tz)
        day_ts = int(day_midnight.timestamp())

        day_sunrise = datetime.combine(
            day_date, datetime.min.time().replace(hour=6, minute=12), tzinfo=eastern_tz
        )
        day_sunset = datetime.combine(
            day_date, datetime.min.time().replace(hour=19, minute=48), tzinfo=eastern_tz
        )
        day_sunrise_ts = int(day_sunrise.timestamp())
        day_sunset_ts = int(day_sunset.timestamp())

        # Simulate temperature variation
        base_temp = 25.5 - (i % 3) * 1.5
        day_condition = conditions[i % len(conditions)]
        icon_code = "01d" if day_condition == "Clear" else "02d"

        daily_data_list.append(
            {
                "dt": day_ts,
                "sunrise": day_sunrise_ts,
                "sunset": day_sunset_ts,
                "moonrise": day_sunrise_ts + 3600,
                "moonset": day_sunset_ts - 3600,
                "moon_phase": 0.75,
                "temp": {
                    "day": base_temp,
                    "min": base_temp - 5.6,  # ~10°F lower
                    "max": base_temp + 2.8,  # ~5°F higher
                    "night": base_temp - 4.4,
                    "eve": base_temp - 1.1,
                    "morn": base_temp - 3.3,
                },
                "feels_like": {
                    "day": base_temp + 1.1,
                    "night": base_temp - 5.0,
                    "eve": base_temp - 0.6,
                    "morn": base_temp - 2.8,
                },
                "pressure": 1015.0,
                "humidity": 55 + (i % 10),
                "dew_point": 16.7,
                "wind_speed": 3.8 + (i % 5) * 0.3,
                "wind_deg": 225,
                "wind_gust": 5.4,
                "weather": [
                    {
                        "id": 800 if day_condition == "Clear" else 802,
                        "main": day_condition,
                        "description": day_condition.lower(),
                        "icon": icon_code,
                    }
                ],
                "clouds": 10 + (i % 20),
                "pop": 0.05 + (i % 10) * 0.02,
                "uvi": 6.5 - (i % 3) * 0.5,
                "alerts": [],
            }
        )

    return current_data, hourly_data_list, daily_data_list


def get_mock_weather(units: str = "imperial") -> WeatherResponse:
    """Generate mock weather data by creating 4.0-shaped API response dicts.

    Parses them through the same _build_response() function as real data
    to ensure code parity between mock and real responses.

    Args:
        units: Temperature units - "metric" for Celsius, "imperial" for Fahrenheit (default).

    Returns:
        WeatherResponse with mock current conditions and 19-day forecast.
    """
    from app.infrastructure.weather.owm_adapter import _build_response

    current_data, hourly_data, daily_data = _get_mock_api_responses()

    # Extract timezone_offset from mock current data
    tz_offset = current_data.get("timezone_offset", 0)

    # Parse through the same function as real API data
    return _build_response(current_data, hourly_data, daily_data, tz_offset, units)
