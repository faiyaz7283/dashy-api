"""Weather API models.

Pydantic models for weather API requests and responses.
"""

from typing import Literal

from pydantic import BaseModel

# Weather condition enum matching OpenWeatherMap API
WeatherCondition = Literal[
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
]


class WeatherCurrent(BaseModel):
    """Current weather conditions.

    Attributes:
        temperature: Current temperature.
        feels_like: Feels-like temperature.
        condition: Weather condition code.
        icon: Weather icon code.
        is_night: Whether it's currently nighttime.
        humidity: Humidity percentage.
        wind_speed: Wind speed.
        wind_gust: Wind gust speed, if any.
        wind_deg: Wind direction in degrees, if any.
        pressure: Atmospheric pressure, if any.
        dew_point: Dew point temperature, if any.
        uvi: UV index, if any.
        sunrise: Sunrise time (ISO time), if any.
        sunset: Sunset time (ISO time), if any.
    """

    temperature: float
    feels_like: float
    condition: WeatherCondition
    icon: str
    is_night: bool = False
    humidity: int
    wind_speed: float
    wind_gust: float | None = None
    wind_deg: int | None = None
    pressure: float | None = None
    dew_point: float | None = None
    uvi: float | None = None
    sunrise: str | None = None
    sunset: str | None = None


class HourlyForecast(BaseModel):
    """Hourly weather forecast data.

    Attributes:
        time: Forecast time (ISO datetime).
        temperature: Temperature at this hour.
        feels_like: Feels-like temperature.
        condition: Weather condition code.
        icon: Weather icon code.
        humidity: Humidity percentage.
        wind_speed: Wind speed.
        pop: Probability of precipitation (0-1).
        pressure: Atmospheric pressure, if any.
        dew_point: Dew point temperature, if any.
        uvi: UV index, if any.
    """

    time: str
    temperature: float
    feels_like: float
    condition: WeatherCondition
    icon: str
    humidity: int
    wind_speed: float
    pop: float
    pressure: float | None = None
    dew_point: float | None = None
    uvi: float | None = None


class DailyForecast(BaseModel):
    """Daily weather forecast with optional hourly breakdown.

    Rich fields are populated for days 1-7 from One Call API.
    Basic fields are populated for days 8-19.

    Attributes:
        date: Forecast date (ISO date).
        high: High temperature for the day.
        low: Low temperature for the day.
        condition: Weather condition code.
        icon: Weather icon code.
        feels_like_day: Daytime feels-like temperature, if any.
        feels_like_night: Nighttime feels-like temperature, if any.
        temp_morn: Morning temperature, if any.
        temp_day: Daytime temperature, if any.
        temp_eve: Evening temperature, if any.
        temp_night: Nighttime temperature, if any.
        humidity: Humidity percentage, if any.
        pressure: Atmospheric pressure, if any.
        dew_point: Dew point temperature, if any.
        wind_speed: Wind speed, if any.
        wind_gust: Wind gust speed, if any.
        wind_deg: Wind direction in degrees, if any.
        uvi: UV index, if any.
        pop: Probability of precipitation (0-1), if any.
        rain: Rainfall in mm, if any.
        snow: Snowfall in mm, if any.
        clouds: Cloud cover percentage, if any.
        sunrise: Sunrise time (ISO time), if any.
        sunset: Sunset time (ISO time), if any.
        moonrise: Moonrise time (ISO time), if any.
        moonset: Moonset time (ISO time), if any.
        moon_phase: Moon phase (0-1), if any.
        summary: Weather summary text, if any.
        hourly: List of hourly forecasts for this day.
    """

    date: str
    high: float
    low: float
    condition: WeatherCondition
    icon: str

    # Rich fields (days 1-7 from One Call API)
    feels_like_day: float | None = None
    feels_like_night: float | None = None
    temp_morn: float | None = None
    temp_day: float | None = None
    temp_eve: float | None = None
    temp_night: float | None = None
    humidity: int | None = None
    pressure: float | None = None
    dew_point: float | None = None
    wind_speed: float | None = None
    wind_gust: float | None = None
    wind_deg: int | None = None
    uvi: float | None = None
    pop: float | None = None
    rain: float | None = None
    snow: float | None = None
    clouds: int | None = None
    sunrise: str | None = None
    sunset: str | None = None
    moonrise: str | None = None
    moonset: str | None = None
    moon_phase: float | None = None
    summary: str | None = None

    # Hourly breakdown (days 1-7 only)
    hourly: list[HourlyForecast] = []


class WeatherResponse(BaseModel):
    """Complete weather response with current conditions and forecast.

    Attributes:
        current: Current weather conditions.
        forecast: List of daily forecasts (up to 19 days).
    """

    current: WeatherCurrent
    forecast: list[DailyForecast]
