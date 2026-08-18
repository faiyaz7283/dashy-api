"""Tests for weather unit conversion functionality."""


from app.infrastructure.weather.owm_adapter import celsius_to_fahrenheit, convert_temperature


def test_celsius_to_fahrenheit_conversion():
    """Test Celsius to Fahrenheit conversion function."""
    # Freezing point
    assert celsius_to_fahrenheit(0) == 32.0

    # Boiling point
    assert celsius_to_fahrenheit(100) == 212.0

    # Room temperature
    assert abs(celsius_to_fahrenheit(25.6) - 78.08) < 0.1


def test_convert_temperature_metric():
    """Test convert_temperature with metric units returns Celsius as-is."""
    assert convert_temperature(25.6, "metric") == 25.6
    assert convert_temperature(None, "metric") is None


def test_convert_temperature_imperial():
    """Test convert_temperature with imperial units converts to Fahrenheit."""
    result = convert_temperature(25.6, "imperial")
    assert abs(result - 78.08) < 0.1

    assert convert_temperature(None, "imperial") is None
