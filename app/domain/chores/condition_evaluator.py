"""Condition evaluator for conditional chores.

Evaluates JSON-based conditions against live weather and calendar data
to determine whether conditional chore instances should be generated.
"""

from datetime import datetime, timedelta

from app.config import settings
from app.core.logging import get_logger
from app.domain.calendar.models import DateRange
from app.domain.calendar.ports import CalendarProvider
from app.domain.chores.schemas import Condition, ConditionsConfig
from app.domain.weather.ports import WeatherProvider

logger = get_logger(__name__)

OPERATOR_MAP = {
    "gt": lambda actual, threshold: actual > threshold,
    "gte": lambda actual, threshold: actual >= threshold,
    "lt": lambda actual, threshold: actual < threshold,
    "lte": lambda actual, threshold: actual <= threshold,
    "eq": lambda actual, threshold: actual == threshold,
    "contains": lambda actual, threshold: threshold in actual,
}


class ConditionEvaluator:
    """Evaluates conditional chore conditions against live data.

    Fetches weather and calendar data via injected providers and
    evaluates condition trees with AND/OR logic.

    Attributes:
        weather_provider: Provider for current weather data.
        calendar_provider: Provider for calendar events.
        calendar_id: Calendar ID to query for calendar conditions.
    """

    def __init__(
        self,
        weather_provider: WeatherProvider,
        calendar_provider: CalendarProvider,
        calendar_id: str = "",
    ) -> None:
        """Initialize the condition evaluator.

        Args:
            weather_provider: Weather data provider.
            calendar_provider: Calendar data provider.
            calendar_id: Default calendar ID for calendar conditions.
        """
        self.weather_provider = weather_provider
        self.calendar_provider = calendar_provider
        self.calendar_id = calendar_id

    async def evaluate(self, conditions_config: ConditionsConfig) -> bool:
        """Evaluate a full conditions configuration.

        Args:
            conditions_config: Validated conditions with logic and condition list.

        Returns:
            True if conditions are met, False otherwise.
        """
        if not conditions_config.conditions:
            return True

        results = [await self._evaluate_single(c) for c in conditions_config.conditions]

        met = all(results) if conditions_config.logic == "and" else any(results)

        logger.info(
            "evaluate_conditions",
            logic=conditions_config.logic,
            results=results,
            met=met,
        )
        return met

    async def _evaluate_single(self, condition: Condition) -> bool:
        """Evaluate a single condition against live data.

        Args:
            condition: Individual condition to evaluate.

        Returns:
            True if the condition is met, False otherwise.
        """
        if condition.type == "weather":
            return await self._evaluate_weather(condition)
        if condition.type == "calendar":
            return await self._evaluate_calendar(condition)

        logger.warning("evaluate_unknown_type", condition_type=condition.type)
        return False

    async def _evaluate_weather(self, condition: Condition) -> bool:
        """Evaluate a weather condition against current conditions.

        Fetches current weather and extracts the metric value. For
        snowfall/rainfall, checks today's daily forecast since those
        are not in current conditions.

        Args:
            condition: Weather condition with metric, operator, and value.

        Returns:
            True if the weather metric satisfies the condition.
        """
        try:
            weather = await self.weather_provider.get_weather()
        except Exception:
            logger.warning("weather_fetch_failed", exc_info=True)
            return False

        metric = condition.metric
        if metric is None:
            return False

        actual = self._extract_weather_metric(weather, metric)
        if actual is None:
            logger.info("weather_metric_unavailable", metric=metric)
            return False

        threshold = float(condition.value) if isinstance(condition.value, str) else condition.value
        compare_fn = OPERATOR_MAP.get(condition.operator)
        if compare_fn is None:
            return False

        return compare_fn(actual, threshold)

    @staticmethod
    def _extract_weather_metric(weather: object, metric: str) -> float | None:
        """Extract a numeric metric from weather response.

        Args:
            weather: WeatherResponse from the weather provider.
            metric: Metric name (temperature, wind_speed, snowfall, rainfall).

        Returns:
            Numeric value for the metric, or None if unavailable.
        """
        current = getattr(weather, "current", None)
        forecast = getattr(weather, "forecast", None)

        if metric == "temperature" and current is not None:
            return getattr(current, "temperature", None)

        if metric == "wind_speed" and current is not None:
            return getattr(current, "wind_speed", None)

        if metric in ("snowfall", "rainfall") and forecast:
            today_str = datetime.now(settings.tz).date().isoformat()
            for day in forecast:
                if getattr(day, "date", None) == today_str:
                    field = "snow" if metric == "snowfall" else "rain"
                    value = getattr(day, field, None)
                    return value if value is not None else 0.0

        return None

    async def _evaluate_calendar(self, condition: Condition) -> bool:
        """Evaluate a calendar condition against today's events.

        Fetches events for today and checks event count or event type.

        Args:
            condition: Calendar condition with event_count/event_type, operator, value.

        Returns:
            True if the calendar data satisfies the condition.
        """
        try:
            now = datetime.now(settings.tz)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(hours=23, minutes=59, seconds=59)
            date_range = DateRange(start=today_start, end=today_end)

            events = await self.calendar_provider.fetch_events(
                self.calendar_id, date_range
            )
        except Exception:
            logger.warning("calendar_fetch_failed", exc_info=True)
            return False

        if condition.event_count is not None:
            actual_count = len(events)
            threshold = float(condition.value)
            compare_fn = OPERATOR_MAP.get(condition.operator)
            if compare_fn is None:
                return False
            return compare_fn(float(actual_count), threshold)

        if condition.event_type is not None:
            event_titles = [
                event.get("summary", "") for event in events
            ]
            threshold_str = str(condition.value)

            if condition.operator == "contains":
                return any(threshold_str in title for title in event_titles)

            compare_fn = OPERATOR_MAP.get(condition.operator)
            if compare_fn is None:
                return False
            return compare_fn(event_titles, threshold_str)

        return False
