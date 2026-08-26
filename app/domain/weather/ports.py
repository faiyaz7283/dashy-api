"""Weather domain ports (interfaces).

Defines the contracts for weather data providers and repositories.
"""

from typing import Protocol

from app.api.models.weather import WeatherResponse


class WeatherProvider(Protocol):
    """Protocol for weather data providers.

    Implementations fetch weather data from external APIs or mock sources.
    """

    async def get_weather(self, units: str = "imperial") -> WeatherResponse:
        """Fetch current weather conditions and forecast.

        Args:
            units: Temperature units — "metric" for Celsius,
                "imperial" for Fahrenheit (default).

        Returns:
            WeatherResponse with current conditions and forecast.
        """
        ...


class WeatherRepository(Protocol):
    """Protocol for weather data persistence.

    Implementations store and retrieve cached weather data.
    """

    async def save_current(self, location: str, data: dict) -> None:
        """Save current weather data to cache.

        Args:
            location: Location identifier.
            data: Current weather data to cache.
        """
        ...

    async def get_current(self, location: str) -> dict | None:
        """Retrieve cached current weather data.

        Args:
            location: Location identifier.

        Returns:
            Cached weather data or None if not found/expired.
        """
        ...

    async def save_forecast(self, location: str, data: list[dict]) -> None:
        """Save forecast data to cache.

        Args:
            location: Location identifier.
            data: Forecast data to cache.
        """
        ...

    async def get_forecast(self, location: str) -> list[dict] | None:
        """Retrieve cached forecast data.

        Args:
            location: Location identifier.

        Returns:
            Cached forecast data or None if not found/expired.
        """
        ...
