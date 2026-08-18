"""Tests for weather adapter and parsing functions."""

from datetime import UTC, datetime, timedelta
from datetime import timezone as dt_timezone

import pytest

from app.infrastructure.weather.owm_adapter import (
    _build_response,
    _get_today_midnight_timestamp,
    _map_condition,
    _map_icon,
    _parse_hourly_from_data,
    _ts_to_date,
    _ts_to_datetime,
    _ts_to_iso,
)

# ── _map_condition ────────────────────────────────────────


class TestMapCondition:
    """All 15 OWM weather.main values map 1:1, with safe fallback."""

    @pytest.mark.parametrize(
        "main,expected",
        [
            ("Clear", "clear"),
            ("Clouds", "clouds"),
            ("Rain", "rain"),
            ("Drizzle", "drizzle"),
            ("Thunderstorm", "thunderstorm"),
            ("Snow", "snow"),
            ("Mist", "mist"),
            ("Smoke", "smoke"),
            ("Haze", "haze"),
            ("Dust", "dust"),
            ("Fog", "fog"),
            ("Sand", "sand"),
            ("Ash", "ash"),
            ("Squall", "squall"),
            ("Tornado", "tornado"),
            ("clear", "clear"),  # already lowercase
            ("CLOUDS", "clouds"),  # uppercase
        ],
    )
    def test_valid_conditions(self, main: str, expected: str):
        assert _map_condition(main) == expected

    def test_unknown_condition_fallback(self):
        assert _map_condition("Unknown") == "clouds"


# ── _map_icon ──────────────────────────────────────────


class TestMapIcon:
    def test_day_suffix(self):
        assert _map_icon("01d") == "d"
        assert _map_icon("10d") == "d"

    def test_night_suffix(self):
        assert _map_icon("01n") == "n"
        assert _map_icon("10n") == "n"

    def test_short_code_defaults_to_day(self):
        assert _map_icon("01") == "d"


# ── Timestamp helpers ─────────────────────────────────────────


class TestTimestampHelpers:
    def test_ts_to_iso(self):
        # 2026-08-11 06:12:00 UTC → EDT (-4h) = 02:12
        ts = 1754892720  # some fixed timestamp
        result = _ts_to_iso(ts, tz_offset=-14400)
        assert result == "02:12"

    def test_ts_to_datetime(self):
        ts = 1754892720
        result = _ts_to_datetime(ts, tz_offset=-14400)
        assert result.startswith("2025-08-11T02:12:00")

    def test_ts_to_date(self):
        ts = 1754892720
        result = _ts_to_date(ts, tz_offset=-14400)
        assert result == "2025-08-11"


# ── _get_today_midnight_timestamp ─────────────────────


class TestTodayMidnightTimestamp:
    def test_returns_midnight_in_local_tz(self):
        tz_offset = -14400  # EDT
        ts = _get_today_midnight_timestamp(tz_offset)
        local_tz = dt_timezone(timedelta(seconds=tz_offset))
        dt = datetime.fromtimestamp(ts, tz=local_tz)
        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.second == 0

    def test_different_tz_offsets(self):
        # UTC
        ts_utc = _get_today_midnight_timestamp(0)
        utc_tz = UTC
        dt_utc = datetime.fromtimestamp(ts_utc, tz=utc_tz)
        assert dt_utc.hour == 0

        # JST (+9h)
        ts_jst = _get_today_midnight_timestamp(32400)
        jst_tz = dt_timezone(timedelta(seconds=32400))
        dt_jst = datetime.fromtimestamp(ts_jst, tz=jst_tz)
        assert dt_jst.hour == 0


# ── _parse_hourly_from_data ───────────────────────────


class TestParseHourlyFromData:
    def test_filters_by_date(self):
        """Only returns hourly records matching the target date."""
        hourly_data = [
            {
                "dt": 1000,
                "temp": 20,
                "feels_like": 21,
                "humidity": 50,
                "wind_speed": 3,
                "weather": [{"main": "Clear", "icon": "01d"}],
                "pop": 0.1,
                "pressure": 1013.0,
            },
            {
                "dt": 2000,
                "temp": 22,
                "feels_like": 23,
                "humidity": 55,
                "wind_speed": 4,
                "weather": [{"main": "Clouds", "icon": "02d"}],
                "pop": 0.2,
                "pressure": 1014.0,
            },
        ]
        # Mock _ts_to_date to control date matching
        from unittest.mock import patch

        with patch("app.infrastructure.weather.owm_adapter._ts_to_date") as mock_date:
            mock_date.side_effect = ["2026-08-11", "2026-08-12"]
            result = _parse_hourly_from_data(hourly_data, "2026-08-11", tz_offset=-14400)
            assert len(result) == 1
            assert result[0].temperature == pytest.approx(68.0, abs=0.1)  # 20°C → 68°F

    def test_converts_celsius_to_fahrenheit(self):
        hourly_data = [
            {
                "dt": 1000,
                "temp": 25.0,
                "feels_like": 26.0,
                "humidity": 50,
                "wind_speed": 3,
                "weather": [{"main": "Clear", "icon": "01d"}],
                "pop": 0.1,
                "pressure": 1013.0,
            },
        ]
        from unittest.mock import patch

        with patch("app.infrastructure.weather.owm_adapter._ts_to_date", return_value="2026-08-11"):
            result = _parse_hourly_from_data(
                hourly_data, "2026-08-11", tz_offset=-14400, units="imperial"
            )
            assert result[0].temperature == pytest.approx(77.0, abs=0.1)

    def test_returns_empty_for_no_match(self):
        hourly_data = [
            {
                "dt": 1000,
                "temp": 20,
                "feels_like": 21,
                "humidity": 50,
                "wind_speed": 3,
                "weather": [{"main": "Clear", "icon": "01d"}],
                "pop": 0.1,
                "pressure": 1013.0,
            },
        ]
        from unittest.mock import patch

        with patch("app.infrastructure.weather.owm_adapter._ts_to_date", return_value="2026-08-12"):
            result = _parse_hourly_from_data(hourly_data, "2026-08-11", tz_offset=-14400)
            assert len(result) == 0


# ── _build_response ───────────────────────────────────


class TestBuildResponse:
    """Test parsing 4.0 API response structure into WeatherResponse."""

    @pytest.fixture
    def sample_4_0_data(self):
        """Minimal 4.0-shaped API response dicts."""
        tz_offset = -14400
        now = datetime.now(dt_timezone(timedelta(seconds=tz_offset)))
        today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        current = {
            "lat": 40.71,
            "lon": -73.51,
            "timezone": "America/New_York",
            "timezone_offset": tz_offset,
            "data": [
                {
                    "dt": int(now.timestamp()),
                    "sunrise": int(now.replace(hour=6, minute=12).timestamp()),
                    "sunset": int(now.replace(hour=19, minute=48).timestamp()),
                    "temp": 25.5,
                    "feels_like": 26.7,
                    "pressure": 1015.0,
                    "humidity": 55,
                    "dew_point": 16.7,
                    "uvi": 6.5,
                    "clouds": 10,
                    "visibility": 10000,
                    "wind_speed": 3.8,
                    "wind_deg": 225,
                    "wind_gust": 5.4,
                    "weather": [
                        {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
                    ],
                    "alerts": [],
                }
            ],
        }

        # 19 days of daily data
        daily = []
        for i in range(19):
            day = today_midnight + timedelta(days=i)
            daily.append(
                {
                    "dt": int(day.timestamp()),
                    "sunrise": int(day.replace(hour=6, minute=12).timestamp()),
                    "sunset": int(day.replace(hour=19, minute=48).timestamp()),
                    "moonrise": int(day.replace(hour=7, minute=0).timestamp()),
                    "moonset": int(day.replace(hour=20, minute=0).timestamp()),
                    "moon_phase": 0.75,
                    "temp": {
                        "day": 25.0,
                        "min": 18.0,
                        "max": 28.0,
                        "night": 19.0,
                        "eve": 23.0,
                        "morn": 20.0,
                    },
                    "feels_like": {"day": 26.0, "night": 18.0, "eve": 22.0, "morn": 19.0},
                    "pressure": 1015.0,
                    "humidity": 55,
                    "dew_point": 16.7,
                    "wind_speed": 3.8,
                    "wind_deg": 225,
                    "wind_gust": 5.4,
                    "weather": [
                        {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
                    ],
                    "clouds": 10,
                    "pop": 0.05,
                    "uvi": 6.5,
                    "alerts": [],
                }
            )

        # 48 hours of hourly data
        hourly = []
        for i in range(48):
            hour = today_midnight + timedelta(hours=i)
            hourly.append(
                {
                    "dt": int(hour.timestamp()),
                    "temp": 22.0,
                    "feels_like": 23.0,
                    "pressure": 1015.0,
                    "humidity": 55,
                    "dew_point": 16.7,
                    "uvi": 5.0,
                    "clouds": 10,
                    "visibility": 10000,
                    "wind_speed": 3.8,
                    "wind_deg": 225,
                    "wind_gust": 5.4,
                    "weather": [
                        {"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}
                    ],
                    "pop": 0.05,
                    "alerts": [],
                }
            )

        return current, hourly, daily, tz_offset

    def test_returns_19_days_forecast(self, sample_4_0_data):
        current, hourly, daily, tz_offset = sample_4_0_data
        response = _build_response(current, hourly, daily, tz_offset)
        assert len(response.forecast) == 19

    def test_all_days_have_rich_fields(self, sample_4_0_data):
        """Every day in the 19-day forecast has rich 4.0 fields."""
        current, hourly, daily, tz_offset = sample_4_0_data
        response = _build_response(current, hourly, daily, tz_offset)
        for day in response.forecast:
            assert day.feels_like_day is not None
            assert day.feels_like_night is not None
            assert day.temp_morn is not None
            assert day.temp_day is not None
            assert day.temp_eve is not None
            assert day.temp_night is not None
            assert day.humidity is not None
            assert day.pressure is not None
            assert day.moonrise is not None
            assert day.moonset is not None
            assert day.moon_phase is not None

    def test_hourly_data_only_for_first_two_days(self, sample_4_0_data):
        """Hourly breakdown only populated for days 1-2 (48 hours)."""
        current, hourly, daily, tz_offset = sample_4_0_data
        response = _build_response(current, hourly, daily, tz_offset)
        # First 2 days should have hourly data
        assert len(response.forecast[0].hourly) == 24
        assert len(response.forecast[1].hourly) == 24
        # Days 3-14 should have empty hourly
        for day in response.forecast[2:]:
            assert day.hourly == []

    def test_current_weather_fields(self, sample_4_0_data):
        current, hourly, daily, tz_offset = sample_4_0_data
        response = _build_response(current, hourly, daily, tz_offset)
        assert response.current.temperature == pytest.approx(77.9, abs=0.1)  # 25.5°C → °F
        assert response.current.condition == "clear"
        assert response.current.humidity == 55
        assert response.current.pressure == 1015.0

    def test_pressure_is_float(self, sample_4_0_data):
        """API returns pressure as float, model accepts it."""
        current, hourly, daily, tz_offset = sample_4_0_data
        response = _build_response(current, hourly, daily, tz_offset)
        assert isinstance(response.current.pressure, float)

    def test_summary_is_none(self, sample_4_0_data):
        """daily.summary removed in 4.0, should be None."""
        current, hourly, daily, tz_offset = sample_4_0_data
        response = _build_response(current, hourly, daily, tz_offset)
        for day in response.forecast:
            assert day.summary is None

    def test_empty_daily_returns_empty_forecast(self):
        current = {
            "data": [
                {
                    "temp": 25,
                    "feels_like": 26,
                    "humidity": 50,
                    "wind_speed": 3,
                    "weather": [{"main": "Clear", "icon": "01d"}],
                    "sunrise": 0,
                    "sunset": 0,
                }
            ]
        }
        response = _build_response(current, None, None, 0)
        assert response.forecast == []

    def test_empty_hourly_returns_empty_hourly_lists(self, sample_4_0_data):
        current, _, daily, tz_offset = sample_4_0_data
        response = _build_response(current, None, daily, tz_offset)
        for day in response.forecast:
            assert day.hourly == []


# ── MockWeatherAdapter tests ───────────────────────────


class TestMockWeatherAdapter:
    """Test that MockWeatherAdapter returns mock data."""

    @pytest.mark.asyncio
    async def test_returns_mock_data(self):
        """MockWeatherAdapter returns mock data."""
        from app.infrastructure.weather.mock_adapter import MockWeatherAdapter
        adapter = MockWeatherAdapter()
        response = await adapter.get_weather()
        assert response.current is not None
        assert len(response.forecast) == 19

    @pytest.mark.asyncio
    async def test_mock_data_has_rich_fields(self):
        """Mock data matches 4.0 structure — all 19 days have rich fields."""
        from app.infrastructure.weather.mock_adapter import MockWeatherAdapter
        adapter = MockWeatherAdapter()
        response = await adapter.get_weather()
        for day in response.forecast:
            assert day.feels_like_day is not None
            assert day.temp_morn is not None
            assert day.temp_day is not None
            assert day.humidity is not None
            assert day.pressure is not None

    @pytest.mark.asyncio
    async def test_mock_data_has_hourly_for_first_two_days(self):
        """Mock data has 48 hourly records split across first 2 days."""
        from app.infrastructure.weather.mock_adapter import MockWeatherAdapter
        adapter = MockWeatherAdapter()
        response = await adapter.get_weather()
        assert len(response.forecast[0].hourly) == 24
        assert len(response.forecast[1].hourly) == 24
        for day in response.forecast[2:]:
            assert day.hourly == []

    @pytest.mark.asyncio
    async def test_mock_data_units_imperial(self):
        """Mock data returns Fahrenheit by default."""
        from app.infrastructure.weather.mock_adapter import MockWeatherAdapter
        adapter = MockWeatherAdapter()
        response = await adapter.get_weather(units="imperial")
        assert response.current.temperature > 50  # Fahrenheit

    @pytest.mark.asyncio
    async def test_mock_data_units_metric(self):
        """Mock data returns Celsius when requested."""
        from app.infrastructure.weather.mock_adapter import MockWeatherAdapter
        adapter = MockWeatherAdapter()
        response = await adapter.get_weather(units="metric")
        assert 15 < response.current.temperature < 35  # Celsius
