"""Weather domain value objects.

Immutable value objects representing weather data concepts.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class TemperatureUnit(Enum):
    """Temperature measurement units."""

    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"


@dataclass(frozen=True)
class Temperature:
    """Temperature value with unit.

    Attributes:
        value: Temperature magnitude.
        unit: Measurement unit (Celsius or Fahrenheit).
    """

    value: float
    unit: TemperatureUnit

    def to_celsius(self) -> "Temperature":
        """Convert to Celsius.

        Returns:
            New Temperature instance in Celsius.
        """
        if self.unit == TemperatureUnit.CELSIUS:
            return self
        celsius_value = (self.value - 32) * 5 / 9
        return Temperature(celsius_value, TemperatureUnit.CELSIUS)

    def to_fahrenheit(self) -> "Temperature":
        """Convert to Fahrenheit.

        Returns:
            New Temperature instance in Fahrenheit.
        """
        if self.unit == TemperatureUnit.FAHRENHEIT:
            return self
        fahrenheit_value = (self.value * 9 / 5) + 32
        return Temperature(fahrenheit_value, TemperatureUnit.FAHRENHEIT)


@dataclass(frozen=True)
class WindSpeed:
    """Wind speed value with unit.

    Attributes:
        value: Speed magnitude.
        unit: Measurement unit (m/s, mph, km/h).
    """

    value: float
    unit: Literal["m/s", "mph", "km/h"] = "m/s"


class WeatherCondition(Enum):
    """Weather condition codes from OpenWeatherMap.

    All 15 distinct weather.main values with 1:1 mapping.
    """

    CLEAR = "clear"
    CLOUDS = "clouds"
    RAIN = "rain"
    DRIZZLE = "drizzle"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    MIST = "mist"
    SMOKE = "smoke"
    HAZE = "haze"
    DUST = "dust"
    FOG = "fog"
    SAND = "sand"
    ASH = "ash"
    SQUALL = "squall"
    TORNADO = "tornado"

    @classmethod
    def from_api_value(cls, value: str) -> "WeatherCondition":
        """Parse weather condition from API response.

        Args:
            value: Weather condition string from API.

        Returns:
            WeatherCondition enum value.

        Raises:
            ValueError: If value doesn't match any known condition.
        """
        normalized = value.lower()
        try:
            return cls(normalized)
        except ValueError:
            # Default to CLOUDS for unknown conditions
            return cls.CLOUDS
