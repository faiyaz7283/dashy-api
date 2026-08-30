"""Metrics API routes.

Provides endpoints for monitoring data freshness and system health.
"""

from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, HTTPException, status

from app.api.deps import CacheDep, FamilyServiceDep
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


async def check_upstream_health() -> dict[str, dict]:
    """Check reachability of upstream services (Google Calendar, OpenWeatherMap).

    Results are cached for NETWORK_HEALTH_CHECK_TTL seconds to avoid hammering APIs.

    Returns:
        Dict with health status for each upstream service.
    """
    from app.core.cache import get_cache

    cache = await get_cache()
    cache_key = "metrics:network_health"

    # Check if we have cached health data
    cached_health = await cache.get(cache_key)
    if cached_health:
        return cached_health

    # Perform health checks
    health_data = {}
    check_timestamp = datetime.now(UTC).isoformat()

    # Check Google Calendar API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://www.googleapis.com/calendar/v3/users/me/calendarList")
            # We expect 401 (unauthorized) but that means the service is reachable
            health_data["google_calendar"] = {
                "reachable": response.status_code in [200, 401, 403],
                "status_code": response.status_code,
                "last_check": check_timestamp,
            }
    except Exception as e:
        logger.warning("google_calendar_health_check_failed", error=str(e))
        health_data["google_calendar"] = {
            "reachable": False,
            "error": str(e),
            "last_check": check_timestamp,
        }

    # Check OpenWeatherMap API
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Use a minimal request that doesn't consume API quota
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": 0, "lon": 0, "appid": "test"},
            )
            # We expect 401 (invalid API key) but that means the service is reachable
            health_data["openweathermap"] = {
                "reachable": response.status_code in [200, 401, 403],
                "status_code": response.status_code,
                "last_check": check_timestamp,
            }
    except Exception as e:
        logger.warning("openweathermap_health_check_failed", error=str(e))
        health_data["openweathermap"] = {
            "reachable": False,
            "error": str(e),
            "last_check": check_timestamp,
        }

    # Cache the health data
    await cache.set(cache_key, health_data, ttl=settings.NETWORK_HEALTH_CHECK_TTL)

    return health_data


def calculate_data_status(fresh_ttl: int, stale_ttl: int, ttl_remaining: int | None) -> dict:
    """Calculate data status based on TTL remaining.

    Args:
        fresh_ttl: Fresh cache TTL in seconds.
        stale_ttl: Stale cache TTL in seconds.
        ttl_remaining: TTL remaining for the cache entry, or None if not cached.

    Returns:
        Dict with status, age_seconds, fresh_ttl, and stale_ttl.
    """
    if ttl_remaining is None:
        return {
            "status": "missing",
            "age_seconds": None,
            "fresh_ttl": fresh_ttl,
            "stale_ttl": stale_ttl,
        }

    # Calculate age based on which TTL tier we're in
    if ttl_remaining > fresh_ttl:
        # This shouldn't happen, but handle it gracefully
        age_seconds = 0
        status_str = "fresh"
    elif ttl_remaining > 0:
        # We're in the fresh tier
        age_seconds = fresh_ttl - ttl_remaining
        status_str = "fresh"
    else:
        # We're in the stale tier (ttl_remaining is negative or zero)
        # Age is fresh_ttl + abs(ttl_remaining)
        age_seconds = fresh_ttl + abs(ttl_remaining)
        status_str = "stale"

    return {
        "status": status_str,
        "age_seconds": age_seconds,
        "fresh_ttl": fresh_ttl,
        "stale_ttl": stale_ttl,
    }


@router.get("")
async def get_metrics(cache: CacheDep, family_service: FamilyServiceDep):
    """Get system metrics including data freshness and network health.

    Returns comprehensive metrics about:
    - Weather data freshness (status, age, TTL)
    - Calendar data freshness (status, age, TTL)
    - Per-member calendar fetch status
    - Network health (upstream API reachability)
    - Cache statistics (hits, misses, errors)

    All timestamps are in UTC.

    Returns:
        Dict with metrics data.

    Raises:
        HTTPException: If metrics are disabled (404).
    """
    if not settings.METRICS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics endpoint is disabled",
        )

    # Get weather cache metadata (default units is imperial)
    weather_fresh_meta = await cache.get_with_metadata("weather:imperial:fresh")
    weather_stale_meta = await cache.get_with_metadata("weather:imperial:stale")

    # Determine weather status
    if weather_fresh_meta:
        weather_status = calculate_data_status(
            fresh_ttl=settings.WEATHER_CACHE_TTL,
            stale_ttl=settings.WEATHER_STALE_TTL,
            ttl_remaining=weather_fresh_meta["ttl_remaining"],
        )
        weather_value = weather_fresh_meta["value"]
        weather_last_fetch = weather_value.get("timestamp") if weather_value else None
    elif weather_stale_meta:
        weather_status = {
            "status": "stale",
            "age_seconds": settings.WEATHER_CACHE_TTL + abs(weather_stale_meta["ttl_remaining"]),
            "fresh_ttl": settings.WEATHER_CACHE_TTL,
            "stale_ttl": settings.WEATHER_STALE_TTL,
        }
        weather_value = weather_stale_meta["value"]
        weather_last_fetch = weather_value.get("timestamp") if weather_value else None
    else:
        weather_status = {
            "status": "missing",
            "age_seconds": None,
            "fresh_ttl": settings.WEATHER_CACHE_TTL,
            "stale_ttl": settings.WEATHER_STALE_TTL,
        }
        weather_last_fetch = None

    # Get calendar cache metadata (default date range key is "default:default")
    calendar_fresh_meta = await cache.get_with_metadata("calendar:default:default:fresh")
    calendar_stale_meta = await cache.get_with_metadata("calendar:default:default:stale")

    # Determine calendar status
    if calendar_fresh_meta:
        calendar_status = calculate_data_status(
            fresh_ttl=settings.CALENDAR_CACHE_TTL,
            stale_ttl=settings.CALENDAR_STALE_TTL,
            ttl_remaining=calendar_fresh_meta["ttl_remaining"],
        )
        calendar_value = calendar_fresh_meta["value"]
        calendar_last_fetch = calendar_value.get("timestamp") if calendar_value else None
    elif calendar_stale_meta:
        calendar_status = {
            "status": "stale",
            "age_seconds": settings.CALENDAR_CACHE_TTL + abs(calendar_stale_meta["ttl_remaining"]),
            "fresh_ttl": settings.CALENDAR_CACHE_TTL,
            "stale_ttl": settings.CALENDAR_STALE_TTL,
        }
        calendar_value = calendar_stale_meta["value"]
        calendar_last_fetch = calendar_value.get("timestamp") if calendar_value else None
    else:
        calendar_status = {
            "status": "missing",
            "age_seconds": None,
            "fresh_ttl": settings.CALENDAR_CACHE_TTL,
            "stale_ttl": settings.CALENDAR_STALE_TTL,
        }
        calendar_last_fetch = None

    # Get per-member calendar metadata
    family_members = await family_service.get_all_members()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    member_metrics = {}

    for member in family_members:
        member_meta_key = f"calendar:member_meta:{member.id}:{today}"
        member_meta = await cache.get(member_meta_key)

        if member_meta:
            member_metrics[member.id] = {
                "status": member_meta.get("status", "unknown"),
                "last_fetch": member_meta.get("last_fetch"),
                "event_count": member_meta.get("event_count", 0),
                "error": member_meta.get("error"),
            }
        else:
            member_metrics[member.id] = {
                "status": "missing",
                "last_fetch": None,
                "event_count": 0,
                "error": None,
            }

    # Get network health (cached)
    network_health = await check_upstream_health()

    # Get cache statistics
    cache_stats = cache.get_stats()

    return {
        "weather": {
            **weather_status,
            "last_fetch": weather_last_fetch,
        },
        "calendar": {
            **calendar_status,
            "last_fetch": calendar_last_fetch,
            "members": member_metrics,
        },
        "network": network_health,
        "cache": {
            "hits": cache_stats.hits,
            "misses": cache_stats.misses,
            "errors": cache_stats.errors,
        },
    }
