"""Mock weather adapter implementing WeatherProvider protocol.

Returns mock weather data for development and testing.
"""

from app.api.models.weather import WeatherResponse
from app.infrastructure.mock_data import get_mock_weather


class MockWeatherAdapter:
    """Mock weather adapter.

    Implements WeatherProvider protocol for returning mock weather data.
    Used in development and testing environments.
    """

    async def get_weather(self, units: str = "imperial") -> WeatherResponse:
        """Fetch mock weather data.

        Args:
            units: Temperature units - "metric" for Celsius, "imperial" for Fahrenheit (default).

        Returns:
            WeatherResponse with mock current conditions and 19-day forecast.
        """
        return get_mock_weather(units)
