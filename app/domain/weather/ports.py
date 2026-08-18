"""Weather domain ports (interfaces).

Defines the contracts for weather data providers and repositories.
"""

from typing import Protocol


class WeatherProvider(Protocol):
    """Protocol for weather data providers.

    Implementations fetch weather data from external APIs or mock sources.
    """

    async def get_current_weather(self, location: str) -> dict:
        """Fetch current weather conditions.

        Args:
            location: Location identifier (e.g., "New York,NY" or coordinates).

        Returns:
            Dictionary containing current weather data.
        """
        ...

    async def get_forecast(self, location: str, days: int = 7) -> list[dict]:
        """Fetch weather forecast.

        Args:
            location: Location identifier.
            days: Number of days to forecast (1-16).

        Returns:
            List of dictionaries containing daily forecast data.
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
