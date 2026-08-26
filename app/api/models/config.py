"""API models for application configuration."""

from pydantic import BaseModel


class AppConfig(BaseModel):
    """Application configuration exposed to the frontend.

    Attributes:
        timezone: IANA timezone identifier for display conversions.
    """

    timezone: str
