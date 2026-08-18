"""Unit tests for weather domain services."""

from app.domain.weather.models import TemperatureUnit, WeatherCondition
from app.domain.weather.services import convert_temperature, map_weather_condition


class TestConvertTemperature:
    """Tests for temperature conversion service."""

    def test_celsius_to_fahrenheit(self) -> None:
        """Test converting Celsius to Fahrenheit."""
        result = convert_temperature(0, TemperatureUnit.CELSIUS, TemperatureUnit.FAHRENHEIT)
        assert result == 32.0

    def test_fahrenheit_to_celsius(self) -> None:
        """Test converting Fahrenheit to Celsius."""
        result = convert_temperature(32, TemperatureUnit.FAHRENHEIT, TemperatureUnit.CELSIUS)
        assert result == 0.0

    def test_same_unit_returns_same_value(self) -> None:
        """Test that converting to same unit returns same value."""
        result = convert_temperature(20, TemperatureUnit.CELSIUS, TemperatureUnit.CELSIUS)
        assert result == 20.0

    def test_boiling_point(self) -> None:
        """Test boiling point conversion."""
        result = convert_temperature(100, TemperatureUnit.CELSIUS, TemperatureUnit.FAHRENHEIT)
        assert result == 212.0

    def test_negative_temperature(self) -> None:
        """Test negative temperature conversion."""
        result = convert_temperature(-40, TemperatureUnit.CELSIUS, TemperatureUnit.FAHRENHEIT)
        assert result == -40.0  # -40°C = -40°F


class TestMapWeatherCondition:
    """Tests for weather condition mapping service."""

    def test_map_clear(self) -> None:
        """Test mapping clear condition."""
        result = map_weather_condition("clear")
        assert result == WeatherCondition.CLEAR

    def test_map_clouds(self) -> None:
        """Test mapping clouds condition."""
        result = map_weather_condition("clouds")
        assert result == WeatherCondition.CLOUDS

    def test_map_rain(self) -> None:
        """Test mapping rain condition."""
        result = map_weather_condition("rain")
        assert result == WeatherCondition.RAIN

    def test_map_case_insensitive(self) -> None:
        """Test that mapping is case insensitive."""
        assert map_weather_condition("CLEAR") == WeatherCondition.CLEAR
        assert map_weather_condition("Clear") == WeatherCondition.CLEAR
        assert map_weather_condition("cLeAr") == WeatherCondition.CLEAR

    def test_map_unknown_defaults_to_clouds(self) -> None:
        """Test that unknown condition defaults to CLOUDS."""
        result = map_weather_condition("unknown")
        assert result == WeatherCondition.CLOUDS
