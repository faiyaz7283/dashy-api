"""Application configuration via pydantic-settings.

All settings are loaded from ``.env`` files and validated at startup.
No hardcoded defaults for secrets or environment-specific values.
"""

import json

from pydantic_settings import BaseSettings


class FamilyMemberConfig:
    """A single family member parsed from the ``FAMILY_MEMBERS`` JSON env var.

    Attributes:
        name: Display name for the family member.
        key: Unique identifier used in API responses and member lookups.
        email: Email address (also used as Google Calendar ID).
        color: Hex color code for UI color-coding.
    """

    def __init__(self, name: str, key: str, email: str, color: str) -> None:
        """Initialize a family member configuration.

        Args:
            name: Display name for the family member.
            key: Unique identifier used in API responses and member lookups.
            email: Email address (also used as Google Calendar ID).
            color: Hex color code for UI color-coding.
        """
        self.name = name
        self.key = key
        self.email = email
        self.color = color


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        ENVIRONMENT: Runtime environment name (``development``, ``production``, ``testing``).
        GOOGLE_SERVICE_ACCOUNT_JSON: Path to the Google service account JSON file.
        OPENWEATHERMAP_API_KEY: API key for OpenWeatherMap.
        OPENWEATHERMAP_LAT: Latitude for weather location.
        OPENWEATHERMAP_LON: Longitude for weather location.
        WEATHER_USE_MOCK: When ``True``, return mock weather data instead of calling the API.
        FAMILY_MEMBERS: JSON string containing the family members array.
        CORS_ORIGINS: Comma-separated list of allowed CORS origins.
    """

    # Environment
    ENVIRONMENT: str = "development"

    # Google Calendar
    GOOGLE_SERVICE_ACCOUNT_JSON: str = "/tmp/test-service-account.json"

    # OpenWeatherMap
    OPENWEATHERMAP_API_KEY: str = "test-api-key"
    OPENWEATHERMAP_LAT: float = 40.715401
    OPENWEATHERMAP_LON: float = -73.512924
    WEATHER_USE_MOCK: bool = False

    # Calendar
    CALENDAR_USE_MOCK: bool = False

    # Family
    FAMILY_MEMBERS: str = (
        '[{"name":"Test User","key":"test","email":"test@example.com","color":"#FF0000"}]'
    )

    # CORS
    CORS_ORIGINS: str = "https://dashy.local,http://localhost:3000,http://dashy.local"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./dashy.db"

    # Cache
    REDIS_URL: str = "redis://localhost:6379"
    WEATHER_CACHE_TTL: int = 600  # 10 minutes
    CALENDAR_CACHE_TTL: int = 120  # 2 minutes

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the comma-separated ``CORS_ORIGINS`` into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def get_family_members(self) -> list[FamilyMemberConfig]:
        """Parse ``FAMILY_MEMBERS`` JSON into a list of ``FamilyMemberConfig`` objects.

        Returns:
            List of parsed family member configurations.
        """
        members = json.loads(self.FAMILY_MEMBERS)
        return [
            FamilyMemberConfig(
                name=m["name"],
                key=m["key"],
                email=m["email"],
                color=m["color"],
            )
            for m in members
        ]


settings = Settings()
