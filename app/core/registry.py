"""Provider registry for Dashy.

Single source of truth for which providers are registered and available.
Helps with testing and ensures consistency across the application.
"""

from app.core.container import (
    get_calendar_provider,
    get_family_repository,
    get_weather_provider,
)


class ProviderRegistry:
    """Registry for all providers in the application.

    Provides a centralized way to access all providers and verify
    that they are properly configured.
    """

    @staticmethod
    def get_weather_provider():
        """Get the registered weather provider."""
        return get_weather_provider()

    @staticmethod
    def get_calendar_provider():
        """Get the registered calendar provider."""
        return get_calendar_provider()

    @staticmethod
    async def get_family_repository():
        """Get the registered family repository.

        Yields:
            FamilyRepository: The family repository instance.
        """
        async for repo in get_family_repository():
            yield repo

    @staticmethod
    def verify_providers() -> dict[str, bool]:
        """Verify that all providers are properly configured.

        Returns:
            Dictionary mapping provider names to their availability status.
        """
        status = {}

        try:
            weather = get_weather_provider()
            status["weather"] = weather is not None
        except Exception:
            status["weather"] = False

        try:
            calendar = get_calendar_provider()
            status["calendar"] = calendar is not None
        except Exception:
            status["calendar"] = False

        return status


# Singleton instance
registry = ProviderRegistry()
