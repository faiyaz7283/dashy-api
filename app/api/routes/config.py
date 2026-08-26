"""Configuration API routes.

Read-only endpoint exposing application configuration to the frontend.
"""

from fastapi import APIRouter

from app.api.models.config import AppConfig
from app.config import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=AppConfig)
async def get_config() -> AppConfig:
    """Return application configuration.

    Returns:
        AppConfig with timezone and other display settings.
    """
    return AppConfig(timezone=settings.TIMEZONE)
