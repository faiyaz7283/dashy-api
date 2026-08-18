"""OpenWeatherMap adapter implementing WeatherProvider protocol.

Fetches weather data from OpenWeatherMap One Call API 4.0.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from app.api.models.weather import (
    DailyForecast,
    HourlyForecast,
    WeatherCondition,
    WeatherCurrent,
    WeatherResponse,
)
from app.config import settings
from app.core.logging import get_logger
from app.infrastructure.weather.http_client import get_http_client

logger = get_logger(__name__)

# Valid OWM weather.main values — 1:1 mapping, no grouping.
_VALID_CONDITIONS: set[str] = {
    "clear",
    "clouds",
    "rain",
    "drizzle",
    "thunderstorm",
    "snow",
    "mist",
    "smoke",
    "haze",
    "dust",
    "fog",
    "sand",
    "ash",
    "squall",
    "tornado",
}

# How many records to fetch from each timeline endpoint.
_MAX_DAILY_RECORDS = 20  # Fetch 20 to ensure 19 remain after filtering past entries
_MAX_HOURLY_RECORDS = 48  # 2 full days


def _map_condition(weather_main: str) -> WeatherCondition:
    """Map OpenWeatherMap weather.main to our condition type (1:1, no grouping)."""
    normalized = weather_main.lower()
    if normalized in _VALID_CONDITIONS:
        return normalized  # type: ignore[return-value]
    return "clouds"  # safe fallback


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9 / 5) + 32


def convert_temperature(value: float | None, units: str) -> float | None:
    """Convert temperature from Celsius to requested units."""
    if value is None:
        return None
    if units == "imperial":
        return celsius_to_fahrenheit(value)
    return value  # metric, return as-is


def _map_icon(icon_code: str) -> str:
    """Extract day/night suffix from OWM icon code (e.g., '01d' -> 'd', '01n' -> 'n')."""
    if len(icon_code) >= 3:
        return icon_code[2]  # 'd' or 'n'
    return "d"  # default to day


def _ts_to_iso(ts: int, tz_offset: int = 0) -> str:
    """Convert Unix timestamp to ISO time string (HH:MM) in local timezone."""
    local_tz = timezone(timedelta(seconds=tz_offset))
    return datetime.fromtimestamp(ts, tz=local_tz).strftime("%H:%M")


def _ts_to_datetime(ts: int, tz_offset: int = 0) -> str:
    """Convert Unix timestamp to ISO datetime string in local timezone."""
    local_tz = timezone(timedelta(seconds=tz_offset))
    return datetime.fromtimestamp(ts, tz=local_tz).strftime("%Y-%m-%dT%H:%M:%S")


def _ts_to_date(ts: int, tz_offset: int = 0) -> str:
    """Convert Unix timestamp to ISO date string (YYYY-MM-DD) in local timezone."""
    local_tz = timezone(timedelta(seconds=tz_offset))
    return datetime.fromtimestamp(ts, tz=local_tz).strftime("%Y-%m-%d")


def _get_today_midnight_timestamp(tz_offset: int) -> int:
    """Get Unix timestamp for today's midnight in the given timezone.

    This ensures "today" is calculated in the local timezone (Eastern Time),
    not UTC. The tz_offset comes from the OWM API response and accounts for DST.

    Args:
        tz_offset: Timezone offset in seconds from UTC.

    Returns:
        Unix timestamp for today's midnight in the specified timezone.
    """
    local_tz = timezone(timedelta(seconds=tz_offset))
    now = datetime.now(local_tz)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(today_midnight.timestamp())


def _parse_hourly_from_data(
    hourly_data: list[dict], day_date: str, tz_offset: int = 0, units: str = "imperial"
) -> list[HourlyForecast]:
    """Parse hourly data for a specific day from One Call API 4.0 response."""
    result = []
    for h in hourly_data:
        h_date = _ts_to_date(h["dt"], tz_offset)
        if h_date != day_date:
            continue
        condition = _map_condition(h["weather"][0]["main"])
        result.append(
            HourlyForecast(
                time=_ts_to_datetime(h["dt"], tz_offset),
                temperature=convert_temperature(h["temp"], units),
                feels_like=convert_temperature(h["feels_like"], units),
                condition=condition,
                icon=condition,  # Use condition name, not day/night suffix
                humidity=h.get("humidity", 0),
                wind_speed=h.get("wind_speed", 0),
                pop=h.get("pop", 0),
                pressure=h.get("pressure"),
                dew_point=h.get("dew_point"),
                uvi=h.get("uvi"),
            )
        )
    return result


def _build_response(
    current_data: dict,
    hourly_data: list[dict] | None,
    daily_data: list[dict] | None,
    tz_offset: int,
    units: str = "imperial",
) -> WeatherResponse:
    """Build WeatherResponse from One Call API 4.0 data.

    Args:
        current_data: Current weather data dict from OWM API.
        hourly_data: Hourly forecast data list, or None.
        daily_data: Daily forecast data list, or None.
        tz_offset: Timezone offset in seconds from UTC.
        units: Temperature units ("metric" or "imperial").

    Returns:
        WeatherResponse with parsed current and forecast data.
    """
    # Build current weather
    if "data" in current_data and len(current_data["data"]) > 0:
        current_record = current_data["data"][0]
        current_condition = _map_condition(current_record["weather"][0]["main"])

        # Calculate is_night based on sunrise/sunset times
        is_night = False
        if "sunrise" in current_record and "sunset" in current_record:
            local_tz = timezone(timedelta(seconds=tz_offset))
            now = datetime.now(local_tz)
            sunrise_ts = current_record["sunrise"]
            sunset_ts = current_record["sunset"]
            now_ts = now.timestamp()
            is_night = now_ts < sunrise_ts or now_ts > sunset_ts

        current = WeatherCurrent(
            temperature=convert_temperature(current_record.get("temp"), units),
            feels_like=convert_temperature(current_record.get("feels_like"), units),
            condition=current_condition,
            icon=current_condition,  # Use condition name, not day/night suffix
            is_night=is_night,
            humidity=current_record.get("humidity", 0),
            wind_speed=current_record.get("wind_speed", 0),
            wind_gust=current_record.get("wind_gust"),
            wind_deg=current_record.get("wind_deg"),
            pressure=current_record.get("pressure"),
            dew_point=convert_temperature(current_record.get("dew_point"), units),
            uvi=current_record.get("uvi"),
            sunrise=_ts_to_iso(current_record["sunrise"], tz_offset)
            if "sunrise" in current_record
            else None,
            sunset=_ts_to_iso(current_record["sunset"], tz_offset)
            if "sunset" in current_record
            else None,
        )
    else:
        # Should not reach here since we already checked current_data, but fallback
        from app.infrastructure.mock_data import get_mock_weather
        return get_mock_weather(units)

    # Build daily forecast
    forecast: list[DailyForecast] = []
    seen_dates: set[str] = set()

    # Get today's date in local timezone to filter out past days
    local_tz = timezone(timedelta(seconds=tz_offset))
    now_ts = int(datetime.now(local_tz).timestamp())
    today_date = _ts_to_date(now_ts, tz_offset)

    if daily_data:
        for day in daily_data:
            date = _ts_to_date(day["dt"], tz_offset)
            # Skip past dates and duplicates
            if date < today_date or date in seen_dates:
                continue
            seen_dates.add(date)

            temp = day.get("temp", {})
            feels = day.get("feels_like", {})
            weather = day["weather"][0] if day.get("weather") else {}
            day_condition = _map_condition(weather.get("main", "clouds"))

            # Get hourly data for this day
            day_hourly = []
            if hourly_data:
                day_hourly = _parse_hourly_from_data(hourly_data, date, tz_offset, units)

            forecast.append(
                DailyForecast(
                    date=date,
                    high=convert_temperature(temp.get("max", 0), units),
                    low=convert_temperature(temp.get("min", 0), units),
                    condition=day_condition,
                    icon=day_condition,  # Use condition name, not day/night suffix
                    feels_like_day=convert_temperature(feels.get("day"), units),
                    feels_like_night=convert_temperature(feels.get("night"), units),
                    temp_morn=convert_temperature(temp.get("morn"), units),
                    temp_day=convert_temperature(temp.get("day"), units),
                    temp_eve=convert_temperature(temp.get("eve"), units),
                    temp_night=convert_temperature(temp.get("night"), units),
                    humidity=day.get("humidity"),
                    pressure=day.get("pressure"),
                    dew_point=convert_temperature(day.get("dew_point"), units),
                    wind_speed=day.get("wind_speed"),
                    wind_gust=day.get("wind_gust"),
                    wind_deg=day.get("wind_deg"),
                    uvi=day.get("uvi"),
                    pop=day.get("pop"),
                    rain=day.get("rain"),
                    snow=day.get("snow"),
                    clouds=day.get("clouds"),
                    sunrise=(
                        _ts_to_iso(day["sunrise"], tz_offset) if "sunrise" in day else None
                    ),
                    sunset=(_ts_to_iso(day["sunset"], tz_offset) if "sunset" in day else None),
                    moonrise=(
                        _ts_to_iso(day["moonrise"], tz_offset) if "moonrise" in day else None
                    ),
                    moonset=(
                        _ts_to_iso(day["moonset"], tz_offset) if "moonset" in day else None
                    ),
                    moon_phase=day.get("moon_phase"),
                    summary=None,  # daily.summary removed in 4.0
                    hourly=day_hourly,
                )
            )

    # Ensure exactly 19 days (today + 18 future days)
    forecast = forecast[:19]

    return WeatherResponse(current=current, forecast=forecast)


class OWMWeatherAdapter:
    """OpenWeatherMap API adapter.

    Implements WeatherProvider protocol for fetching weather data
    from OpenWeatherMap One Call API 4.0.
    """

    def __init__(
        self,
        api_key: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
    ) -> None:
        """Initialize OWM adapter.

        Args:
            api_key: OpenWeatherMap API key. Defaults to settings.OPENWEATHERMAP_API_KEY.
            lat: Latitude. Defaults to settings.OPENWEATHERMAP_LAT.
            lon: Longitude. Defaults to settings.OPENWEATHERMAP_LON.
        """
        self.api_key = api_key or settings.OPENWEATHERMAP_API_KEY
        self.lat = lat if lat is not None else settings.OPENWEATHERMAP_LAT
        self.lon = lon if lon is not None else settings.OPENWEATHERMAP_LON

    async def get_weather(self, units: str = "imperial") -> WeatherResponse:
        """Fetch current weather and 19-day forecast from OpenWeatherMap API 4.0.

        Args:
            units: Temperature units - "metric" for Celsius, "imperial" for Fahrenheit (default).

        Returns:
            WeatherResponse with current conditions and 19-day forecast.
        """
        client = get_http_client()

        # Step 1: Fetch current weather to get timezone_offset
        current_data = await self._fetch_current(client)
        if current_data is None:
            logger.warning("current_weather_failed", msg="falling back to mock data")
            from app.infrastructure.mock_data import get_mock_weather
            return get_mock_weather(units)

        # Step 2: Calculate start timestamp (today's midnight in local timezone)
        # The timezone_offset from OWM accounts for DST automatically.
        tz_offset = current_data.get("timezone_offset", 0)
        start_ts = _get_today_midnight_timestamp(tz_offset)

        # Step 3: Fetch daily and hourly concurrently with start parameter
        daily_task = self._fetch_daily(client, start=start_ts)
        hourly_task = self._fetch_hourly(client, start=start_ts)

        daily_data, hourly_data = await asyncio.gather(daily_task, hourly_task)

        # If both failed, fall back to mock
        if daily_data is None and hourly_data is None:
            logger.warning("daily_hourly_failed", msg="falling back to mock data")
            from app.infrastructure.mock_data import get_mock_weather
            return get_mock_weather(units)

        return _build_response(current_data, hourly_data, daily_data, tz_offset, units)

    async def _fetch_current(self, client: httpx.AsyncClient) -> dict | None:
        """Fetch current weather from One Call API 4.0."""
        try:
            response = await client.get(
                "https://api.openweathermap.org/data/4.0/onecall/current",
                params={
                    "lat": self.lat,
                    "lon": self.lon,
                    "appid": self.api_key,
                    "units": "metric",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error("current_weather_api_error", error=str(e))
            return None

    async def _fetch_hourly(
        self,
        client: httpx.AsyncClient,
        start: int | None = None,
        max_records: int = _MAX_HOURLY_RECORDS,
    ) -> list[dict] | None:
        """Fetch hourly forecast from One Call API 4.0 with pagination.

        Anchored at 'start' timestamp (today's midnight in local timezone).
        Limited to max_records to avoid fetching historical data.

        Args:
            client: HTTP client for making requests.
            start: Start timestamp for pagination (today's midnight).
            max_records: Maximum number of records to fetch.

        Returns:
            List of hourly forecast data dicts, or None on error.
        """
        try:
            all_hourly: list[dict] = []
            url = "https://api.openweathermap.org/data/4.0/onecall/timeline/1h"
            params: dict = {
                "lat": self.lat,
                "lon": self.lon,
                "appid": self.api_key,
                "units": "metric",
            }
            if start is not None:
                params["start"] = start

            # Fetch first page
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            all_hourly.extend(data.get("data", []))

            # Follow pagination until we have enough records or no more pages
            while "next" in data and len(all_hourly) < max_records:
                next_url = data["next"]
                response = await client.get(next_url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                all_hourly.extend(data.get("data", []))

            # Trim to max_records
            return all_hourly[:max_records]
        except httpx.HTTPError as e:
            logger.error("hourly_forecast_api_error", error=str(e))
            return None

    async def _fetch_daily(
        self,
        client: httpx.AsyncClient,
        start: int | None = None,
        max_records: int = _MAX_DAILY_RECORDS,
    ) -> list[dict] | None:
        """Fetch daily forecast from One Call API 4.0 with pagination.

        Anchored at 'start' timestamp (today's midnight in local timezone).
        Limited to max_records (20 days) to ensure 19 remain after filtering past entries.

        Args:
            client: HTTP client for making requests.
            start: Start timestamp for pagination (today's midnight).
            max_records: Maximum number of records to fetch.

        Returns:
            List of daily forecast data dicts, or None on error.
        """
        try:
            all_daily: list[dict] = []
            url = "https://api.openweathermap.org/data/4.0/onecall/timeline/1day"
            params: dict = {
                "lat": self.lat,
                "lon": self.lon,
                "appid": self.api_key,
                "units": "metric",
            }
            if start is not None:
                params["start"] = start

            # Fetch first page
            response = await client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            all_daily.extend(data.get("data", []))

            # Follow pagination until we have enough records or no more pages
            while "next" in data and len(all_daily) < max_records:
                next_url = data["next"]
                response = await client.get(next_url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                all_daily.extend(data.get("data", []))

            # Trim to max_records
            return all_daily[:max_records]
        except httpx.HTTPError as e:
            logger.error("daily_forecast_api_error", error=str(e))
            return None
