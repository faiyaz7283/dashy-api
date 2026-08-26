"""Unit tests for condition evaluator."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.api.models.weather import DailyForecast, WeatherCurrent, WeatherResponse
from app.domain.chores.condition_evaluator import ConditionEvaluator
from app.domain.chores.schemas import Condition, ConditionsConfig


@pytest.fixture
def mock_weather_provider() -> AsyncMock:
    """Create a mock weather provider.

    Returns:
        AsyncMock configured as WeatherProvider.
    """
    return AsyncMock()


@pytest.fixture
def mock_calendar_provider() -> AsyncMock:
    """Create a mock calendar provider.

    Returns:
        AsyncMock configured as CalendarProvider.
    """
    return AsyncMock()


@pytest.fixture
def evaluator(
    mock_weather_provider: AsyncMock, mock_calendar_provider: AsyncMock
) -> ConditionEvaluator:
    """Create a condition evaluator with mock providers.

    Args:
        mock_weather_provider: Mock weather provider.
        mock_calendar_provider: Mock calendar provider.

    Returns:
        ConditionEvaluator instance.
    """
    return ConditionEvaluator(
        weather_provider=mock_weather_provider,
        calendar_provider=mock_calendar_provider,
        calendar_id="test@example.com",
    )


@pytest.fixture
def weather_with_snow() -> WeatherResponse:
    """Create weather response with snowfall.

    Returns:
        WeatherResponse with snow > 0.
    """
    today = datetime.now(UTC).date().isoformat()
    return WeatherResponse(
        current=WeatherCurrent(
            temperature=28.0,
            feels_like=25.0,
            condition="snow",
            icon="13d",
            humidity=80,
            wind_speed=10.0,
        ),
        forecast=[
            DailyForecast(
                date=today,
                high=32.0,
                low=25.0,
                condition="snow",
                icon="13d",
                snow=5.0,
            )
        ],
    )


@pytest.fixture
def weather_no_snow() -> WeatherResponse:
    """Create weather response without snowfall.

    Returns:
        WeatherResponse with snow = 0.
    """
    today = datetime.now(UTC).date().isoformat()
    return WeatherResponse(
        current=WeatherCurrent(
            temperature=45.0,
            feels_like=42.0,
            condition="clear",
            icon="01d",
            humidity=60,
            wind_speed=5.0,
        ),
        forecast=[
            DailyForecast(
                date=today,
                high=50.0,
                low=40.0,
                condition="clear",
                icon="01d",
                snow=0.0,
            )
        ],
    )


class TestConditionEvaluatorWeather:
    """Tests for weather condition evaluation."""

    @pytest.mark.asyncio
    async def test_snowfall_gt_zero_when_snowing(
        self, evaluator: ConditionEvaluator, weather_with_snow: WeatherResponse
    ) -> None:
        """Test snowfall > 0 condition when it's snowing."""
        evaluator.weather_provider.get_weather.return_value = weather_with_snow

        condition = Condition(
            type="weather", metric="snowfall", operator="gt", value=0
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        result = await evaluator.evaluate(config)
        assert result is True

    @pytest.mark.asyncio
    async def test_snowfall_gt_zero_when_clear(
        self, evaluator: ConditionEvaluator, weather_no_snow: WeatherResponse
    ) -> None:
        """Test snowfall > 0 condition when it's clear."""
        evaluator.weather_provider.get_weather.return_value = weather_no_snow

        condition = Condition(
            type="weather", metric="snowfall", operator="gt", value=0
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        result = await evaluator.evaluate(config)
        assert result is False

    @pytest.mark.asyncio
    async def test_temperature_lt_threshold(
        self, evaluator: ConditionEvaluator, weather_with_snow: WeatherResponse
    ) -> None:
        """Test temperature < threshold condition."""
        evaluator.weather_provider.get_weather.return_value = weather_with_snow

        condition = Condition(
            type="weather", metric="temperature", operator="lt", value=32
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        result = await evaluator.evaluate(config)
        assert result is True

    @pytest.mark.asyncio
    async def test_temperature_gte_threshold(
        self, evaluator: ConditionEvaluator, weather_with_snow: WeatherResponse
    ) -> None:
        """Test temperature >= threshold condition (false when below)."""
        evaluator.weather_provider.get_weather.return_value = weather_with_snow

        condition = Condition(
            type="weather", metric="temperature", operator="gte", value=32
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        result = await evaluator.evaluate(config)
        assert result is False

    @pytest.mark.asyncio
    async def test_wind_speed_gt_threshold(
        self, evaluator: ConditionEvaluator, weather_with_snow: WeatherResponse
    ) -> None:
        """Test wind_speed > threshold condition."""
        evaluator.weather_provider.get_weather.return_value = weather_with_snow

        condition = Condition(
            type="weather", metric="wind_speed", operator="gt", value=5
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        result = await evaluator.evaluate(config)
        assert result is True


class TestConditionEvaluatorCalendar:
    """Tests for calendar condition evaluation."""

    @pytest.mark.asyncio
    async def test_event_count_gte_threshold(self, evaluator: ConditionEvaluator) -> None:
        """Test event_count >= threshold condition."""
        evaluator.calendar_provider.fetch_events.return_value = [
            {"summary": "Event 1"},
            {"summary": "Event 2"},
            {"summary": "Event 3"},
        ]

        condition = Condition(
            type="calendar", event_count=3, operator="gte", value=3
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        result = await evaluator.evaluate(config)
        assert result is True

    @pytest.mark.asyncio
    async def test_event_count_lt_threshold(self, evaluator: ConditionEvaluator) -> None:
        """Test event_count < threshold condition (true when less)."""
        evaluator.calendar_provider.fetch_events.return_value = [
            {"summary": "Event 1"},
            {"summary": "Event 2"},
        ]

        condition = Condition(
            type="calendar", event_count=3, operator="lt", value=3
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        result = await evaluator.evaluate(config)
        assert result is True

    @pytest.mark.asyncio
    async def test_event_type_contains(self, evaluator: ConditionEvaluator) -> None:
        """Test event_type contains condition."""
        evaluator.calendar_provider.fetch_events.return_value = [
            {"summary": "Team Meeting"},
            {"summary": "Lunch"},
        ]

        condition = Condition(
            type="calendar", event_type="Meeting", operator="contains", value="Meeting"
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        result = await evaluator.evaluate(config)
        assert result is True


class TestConditionEvaluatorLogic:
    """Tests for AND/OR logic in condition evaluation."""

    @pytest.mark.asyncio
    async def test_and_logic_all_true(
        self, evaluator: ConditionEvaluator, weather_with_snow: WeatherResponse
    ) -> None:
        """Test AND logic when all conditions are true."""
        evaluator.weather_provider.get_weather.return_value = weather_with_snow

        conditions = [
            Condition(type="weather", metric="snowfall", operator="gt", value=0),
            Condition(type="weather", metric="temperature", operator="lt", value=32),
        ]
        config = ConditionsConfig(logic="and", conditions=conditions)

        result = await evaluator.evaluate(config)
        assert result is True

    @pytest.mark.asyncio
    async def test_and_logic_one_false(
        self, evaluator: ConditionEvaluator, weather_with_snow: WeatherResponse
    ) -> None:
        """Test AND logic when one condition is false."""
        evaluator.weather_provider.get_weather.return_value = weather_with_snow

        conditions = [
            Condition(type="weather", metric="snowfall", operator="gt", value=0),
            Condition(type="weather", metric="temperature", operator="gt", value=32),
        ]
        config = ConditionsConfig(logic="and", conditions=conditions)

        result = await evaluator.evaluate(config)
        assert result is False

    @pytest.mark.asyncio
    async def test_or_logic_one_true(
        self, evaluator: ConditionEvaluator, weather_with_snow: WeatherResponse
    ) -> None:
        """Test OR logic when one condition is true."""
        evaluator.weather_provider.get_weather.return_value = weather_with_snow

        conditions = [
            Condition(type="weather", metric="snowfall", operator="gt", value=0),
            Condition(type="weather", metric="temperature", operator="gt", value=32),
        ]
        config = ConditionsConfig(logic="or", conditions=conditions)

        result = await evaluator.evaluate(config)
        assert result is True

    @pytest.mark.asyncio
    async def test_or_logic_all_false(
        self, evaluator: ConditionEvaluator, weather_no_snow: WeatherResponse
    ) -> None:
        """Test OR logic when all conditions are false."""
        evaluator.weather_provider.get_weather.return_value = weather_no_snow

        conditions = [
            Condition(type="weather", metric="snowfall", operator="gt", value=0),
            Condition(type="weather", metric="temperature", operator="lt", value=32),
        ]
        config = ConditionsConfig(logic="or", conditions=conditions)

        result = await evaluator.evaluate(config)
        assert result is False


class TestConditionEvaluatorErrorHandling:
    """Tests for error handling in condition evaluation."""

    @pytest.mark.asyncio
    async def test_weather_fetch_failure(self, evaluator: ConditionEvaluator) -> None:
        """Test graceful handling when weather fetch fails."""
        evaluator.weather_provider.get_weather.side_effect = Exception("API error")

        condition = Condition(
            type="weather", metric="temperature", operator="gt", value=32
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        result = await evaluator.evaluate(config)
        assert result is False

    @pytest.mark.asyncio
    async def test_calendar_fetch_failure(self, evaluator: ConditionEvaluator) -> None:
        """Test graceful handling when calendar fetch fails."""
        evaluator.calendar_provider.fetch_events.side_effect = Exception("API error")

        condition = Condition(
            type="calendar", event_count=1, operator="gte", value=1
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        result = await evaluator.evaluate(config)
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_conditions(self, evaluator: ConditionEvaluator) -> None:
        """Test that empty conditions list returns True."""
        config = ConditionsConfig(logic="and", conditions=[])

        result = await evaluator.evaluate(config)
        assert result is True

    @pytest.mark.asyncio
    async def test_unavailable_metric_returns_false(self, evaluator: ConditionEvaluator) -> None:
        """Test that unavailable metric (e.g., snowfall with no forecast) returns False."""
        condition = Condition(
            type="weather", metric="snowfall", operator="gt", value=0
        )
        config = ConditionsConfig(logic="and", conditions=[condition])

        # Weather response with no forecast data — snowfall metric unavailable
        evaluator.weather_provider.get_weather.return_value = WeatherResponse(
            current=WeatherCurrent(
                temperature=50.0,
                feels_like=48.0,
                condition="clear",
                icon="01d",
                humidity=60,
                wind_speed=5.0,
            ),
            forecast=[],
        )

        result = await evaluator.evaluate(config)
        assert result is False
