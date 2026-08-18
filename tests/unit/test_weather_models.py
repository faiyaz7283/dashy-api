"""Unit tests for weather domain models."""

import pytest

from app.domain.weather.models import Temperature, TemperatureUnit, WeatherCondition


class TestTemperature:
    """Tests for Temperature value object."""

    def test_celsius_to_fahrenheit(self) -> None:
        """Test converting Celsius to Fahrenheit."""
        temp = Temperature(0, TemperatureUnit.CELSIUS)
        fahrenheit = temp.to_fahrenheit()
        assert fahrenheit.value == 32.0
        assert fahrenheit.unit == TemperatureUnit.FAHRENHEIT

    def test_fahrenheit_to_celsius(self) -> None:
        """Test converting Fahrenheit to Celsius."""
        temp = Temperature(32, TemperatureUnit.FAHRENHEIT)
        celsius = temp.to_celsius()
        assert celsius.value == 0.0
        assert celsius.unit == TemperatureUnit.CELSIUS

    def test_celsius_to_celsius_returns_same(self) -> None:
        """Test that converting Celsius to Celsius returns same instance."""
        temp = Temperature(20, TemperatureUnit.CELSIUS)
        result = temp.to_celsius()
        assert result is temp

    def test_fahrenheit_to_fahrenheit_returns_same(self) -> None:
        """Test that converting Fahrenheit to Fahrenheit returns same instance."""
        temp = Temperature(68, TemperatureUnit.FAHRENHEIT)
        result = temp.to_fahrenheit()
        assert result is temp

    def test_boiling_point_conversion(self) -> None:
        """Test boiling point conversion (100°C = 212°F)."""
        temp = Temperature(100, TemperatureUnit.CELSIUS)
        fahrenheit = temp.to_fahrenheit()
        assert fahrenheit.value == 212.0

    def test_freezing_point_conversion(self) -> None:
        """Test freezing point conversion (32°F = 0°C)."""
        temp = Temperature(32, TemperatureUnit.FAHRENHEIT)
        celsius = temp.to_celsius()
        assert celsius.value == 0.0

    def test_temperature_is_immutable(self) -> None:
        """Test that Temperature is immutable (frozen dataclass)."""
        temp = Temperature(20, TemperatureUnit.CELSIUS)
        with pytest.raises(AttributeError):
            temp.value = 25  # type: ignore


class TestWeatherCondition:
    """Tests for WeatherCondition enum."""

    def test_from_api_value_lowercase(self) -> None:
        """Test parsing lowercase API value."""
        condition = WeatherCondition.from_api_value("clear")
        assert condition == WeatherCondition.CLEAR

    def test_from_api_value_uppercase(self) -> None:
        """Test parsing uppercase API value."""
        condition = WeatherCondition.from_api_value("CLOUDS")
        assert condition == WeatherCondition.CLOUDS

    def test_from_api_value_mixed_case(self) -> None:
        """Test parsing mixed case API value."""
        condition = WeatherCondition.from_api_value("Rain")
        assert condition == WeatherCondition.RAIN

    def test_from_api_value_unknown_defaults_to_clouds(self) -> None:
        """Test that unknown API value defaults to CLOUDS."""
        condition = WeatherCondition.from_api_value("unknown")
        assert condition == WeatherCondition.CLOUDS

    def test_all_conditions_are_valid(self) -> None:
        """Test that all 15 OWM conditions are defined."""
        expected_conditions = {
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
        actual_conditions = {c.value for c in WeatherCondition}
        assert actual_conditions == expected_conditions
