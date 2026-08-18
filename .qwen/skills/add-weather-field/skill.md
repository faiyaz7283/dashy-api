---
name: add-weather-field
description: Add a new field to weather data (e.g., air quality, pollen count, UV index) — update domain models, adapters, API models, and tests.
---

# Add Weather Field

Add a new field to weather data throughout the Dashy backend.

## When to use

- Extending weather data with new metrics (air quality, pollen, UV index, etc.)
- Adding new information from OpenWeatherMap API
- Not for changing existing field types or names — that's a breaking change

## Prerequisites

- Understand which API provides the new field (OWM current, forecast, air pollution, etc.)
- Know the data type (number, string, enum)
- Decide if field is required or optional

## Steps

### 1. Add to domain models

Edit `app/domain/weather/models.py`:

```python
"""Weather domain models.

Value objects for weather data.
"""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class WeatherData:
    """Complete weather data value object.

    Contains current conditions and forecast data.
    """

    temperature: float
    condition: str
    humidity: int
    # ... existing fields

    # New field
    air_quality_index: int | None = None  # Optional field
    uv_index: float | None = None

    def has_air_quality(self) -> bool:
        """Check if air quality data is available.

        Returns:
            True if air quality index is not None.
        """
        return self.air_quality_index is not None
```

**Rules:**
- Add to value object (dataclass)
- Make optional if not always available (`| None = None`)
- Add helper methods if field has special logic

### 2. Update WeatherProvider Protocol (if needed)

If the new field requires a new API call, update the Protocol:

```python
# app/domain/weather/ports.py
class WeatherProvider(Protocol):
    async def get_current_weather(self, location: str) -> dict:
        """Fetch current weather conditions."""
        ...

    async def get_air_quality(self, location: str) -> dict | None:
        """Fetch air quality data.

        Args:
            location: Location identifier.

        Returns:
            Air quality data or None if not available.
        """
        ...
```

### 3. Update OWM adapter

Edit `app/infrastructure/weather/owm_adapter.py`:

```python
class OWMWeatherAdapter:
    """OpenWeatherMap implementation of WeatherProvider."""

    async def get_current_weather(self, location: str) -> dict:
        """Fetch current weather from OWM API.

        Args:
            location: Location identifier.

        Returns:
            Dictionary with weather data including new field.
        """
        client = get_http_client()

        # Fetch current weather
        response = await client.get(
            "https://api.openweathermap.org/data/4.0/onecall/current",
            params={
                "lat": self.lat,
                "lon": self.lon,
                "appid": self.api_key,
                "units": "metric"
            }
        )
        response.raise_for_status()
        data = response.json()

        # Parse existing fields
        result = self._parse_current_weather(data)

        # Fetch and add new field (if separate API call)
        if self._needs_air_quality():
            air_quality = await self.get_air_quality(location)
            result["air_quality_index"] = air_quality.get("aqi") if air_quality else None

        return result

    async def get_air_quality(self, location: str) -> dict | None:
        """Fetch air quality from OWM Air Pollution API.

        Args:
            location: Location identifier.

        Returns:
            Air quality data or None.
        """
        client = get_http_client()

        try:
            response = await client.get(
                "https://api.openweathermap.org/data/4.0/air_pollution",
                params={
                    "lat": self.lat,
                    "lon": self.lon,
                    "appid": self.api_key
                }
            )
            response.raise_for_status()
            data = response.json()

            return {
                "aqi": data["list"][0]["main"]["aqi"],
                "components": data["list"][0]["components"]
            }
        except Exception as e:
            logger.warning("air_quality_fetch_failed", error=str(e))
            return None

    def _parse_current_weather(self, data: dict) -> dict:
        """Parse OWM response to domain format.

        Args:
            data: Raw OWM API response.

        Returns:
            Parsed weather data.
        """
        return {
            "temperature": data["current"]["temp"],
            "condition": data["current"]["weather"][0]["main"],
            "humidity": data["current"]["humidity"],
            # Add new field if it's in the same API response
            "uv_index": data["current"].get("uvi"),  # Optional field
        }
```

### 4. Update mock adapter

Edit `app/infrastructure/weather/mock_adapter.py`:

```python
class MockWeatherAdapter:
    """Mock implementation of WeatherProvider."""

    async def get_current_weather(self, location: str) -> dict:
        """Return mock weather data.

        Args:
            location: Location identifier.

        Returns:
            Mock weather data with new field.
        """
        return {
            "temperature": 22.5,
            "condition": "Clear",
            "humidity": 65,
            # Add new field with mock value
            "air_quality_index": 42,
            "uv_index": 5.2,
        }

    async def get_air_quality(self, location: str) -> dict | None:
        """Return mock air quality data.

        Args:
            location: Location identifier.

        Returns:
            Mock air quality data.
        """
        return {
            "aqi": 42,
            "components": {
                "co": 200.5,
                "no2": 15.3,
                "o3": 65.2
            }
        }
```

### 5. Update API response models

Edit `app/api/models/weather.py`:

```python
"""Weather API models.

Request and response models for weather endpoints.
"""

from pydantic import BaseModel, Field


class CurrentWeatherResponse(BaseModel):
    """Current weather response model."""

    temperature: float = Field(description="Current temperature")
    condition: str = Field(description="Weather condition")
    humidity: int = Field(description="Humidity percentage")
    # ... existing fields

    # New field
    air_quality_index: int | None = Field(
        default=None,
        description="Air Quality Index (1-5 scale)"
    )
    uv_index: float | None = Field(
        default=None,
        description="UV index (0-11+ scale)"
    )

    @classmethod
    def from_domain(cls, data: dict) -> "CurrentWeatherResponse":
        """Create response from domain data.

        Args:
            data: Domain weather data dictionary.

        Returns:
            CurrentWeatherResponse instance.
        """
        return cls(
            temperature=data["temperature"],
            condition=data["condition"],
            humidity=data["humidity"],
            air_quality_index=data.get("air_quality_index"),
            uv_index=data.get("uv_index"),
        )
```

### 6. Update tests

#### Unit tests

```python
# tests/unit/domain/test_weather_models.py
from app.domain.weather.models import WeatherData


def test_weather_data_with_air_quality():
    """Test weather data includes air quality."""
    weather = WeatherData(
        temperature=22.5,
        condition="Clear",
        humidity=65,
        air_quality_index=42
    )

    assert weather.air_quality_index == 42
    assert weather.has_air_quality() is True


def test_weather_data_without_air_quality():
    """Test weather data without air quality."""
    weather = WeatherData(
        temperature=22.5,
        condition="Clear",
        humidity=65
    )

    assert weather.air_quality_index is None
    assert weather.has_air_quality() is False
```

#### Integration tests

```python
# tests/integration/test_owm_adapter.py
import pytest


@pytest.mark.asyncio
async def test_owm_adapter_parses_air_quality(httpx_mock):
    """Test adapter parses air quality from API response."""
    # Mock air quality API
    httpx_mock.add_response(
        url="https://api.openweathermap.org/data/4.0/air_pollution?lat=40.7&lon=-73.5&appid=test",
        json={
            "list": [{
                "main": {"aqi": 3},
                "components": {"co": 200.5}
            }]
        }
    )

    adapter = OWMWeatherAdapter(api_key="test", lat=40.7, lon=-73.5)
    result = await adapter.get_air_quality("NewYork")

    assert result is not None
    assert result["aqi"] == 3
```

#### API tests

```python
# tests/api/test_weather_api.py
import pytest


@pytest.mark.asyncio
async def test_weather_response_includes_air_quality():
    """Test weather endpoint returns air quality data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/weather?units=imperial")

        assert response.status_code == 200
        data = response.json()

        # Check new field is present
        assert "air_quality_index" in data["current"]
        assert "uv_index" in data["current"]
```

### 7. Run quality gate

```bash
uv run ruff check app/ tests/ && uv run python -m compileall app/ && uv run pytest tests/ -v
```

## Checklist

- [ ] Field added to domain models (`app/domain/weather/models.py`)
- [ ] Protocol updated if new API call needed
- [ ] OWM adapter updated to fetch/parse new field
- [ ] Mock adapter updated with mock data
- [ ] API response model updated (`app/api/models/weather.py`)
- [ ] Unit tests added for domain models
- [ ] Integration tests added for adapter
- [ ] API tests added for endpoint
- [ ] Quality gate passes
- [ ] Documentation updated

## Example: Adding UV index

1. Add `uv_index: float | None` to `WeatherData` dataclass
2. Parse from OWM current weather response (it's in the same API call)
3. Add to `CurrentWeatherResponse` model
4. Add mock value to `MockWeatherAdapter`
5. Update tests
6. Quality gate passes

## Example: Adding air quality (separate API)

1. Add `air_quality_index: int | None` to `WeatherData`
2. Add `get_air_quality()` method to `WeatherProvider` Protocol
3. Implement in `OWMWeatherAdapter` (calls separate air pollution API)
4. Implement in `MockWeatherAdapter`
5. Fetch air quality in `get_current_weather()` and add to result
6. Add to API response model
7. Update tests
8. Quality gate passes

## Notes

- Make fields optional if not always available
- Handle API failures gracefully (log warning, return None)
- Use `| None` for optional fields (Pydantic v2 syntax)
- Field descriptions appear in OpenAPI docs
- Test both with and without the new field
- Consider caching if field requires separate API call
