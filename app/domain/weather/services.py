"""Weather domain services.

Pure business logic for weather data processing.
"""

from app.domain.weather.models import Temperature, TemperatureUnit, WeatherCondition


def convert_temperature(
    value: float,
    from_unit: TemperatureUnit,
    to_unit: TemperatureUnit,
) -> float:
    """Convert temperature between units.

    Args:
        value: Temperature value to convert.
        from_unit: Source temperature unit.
        to_unit: Target temperature unit.

    Returns:
        Converted temperature value.
    """
    temp = Temperature(value, from_unit)
    if to_unit == TemperatureUnit.CELSIUS:
        return temp.to_celsius().value
    return temp.to_fahrenheit().value


def map_weather_condition(api_value: str) -> WeatherCondition:
    """Map API weather condition string to domain enum.

    Args:
        api_value: Weather condition string from API.

    Returns:
        WeatherCondition enum value.
    """
    return WeatherCondition.from_api_value(api_value)
