"""Dashy FastAPI application entry point.

Configures middleware, exception handlers, and router registration.
Kept minimal — all cross-cutting concerns live in ``app.core``.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import calendar, family, weather
from app.config import settings
from app.core.cache import close_cache, get_cache
from app.core.exceptions import DashyError
from app.core.logging import _configure_structlog, get_logger
from app.core.seed import seed_family_members_if_empty

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure logging on startup and clean up on shutdown."""
    _configure_structlog(settings.ENVIRONMENT)
    # Initialize cache connection
    cache = await get_cache()
    logger.info(
        "dashy_startup",
        environment=settings.ENVIRONMENT,
        cache_connected=cache.is_connected,
    )
    # Seed family members from environment if database is empty
    await seed_family_members_if_empty()
    yield
    # Close cache connection
    await close_cache()
    logger.info("dashy_shutdown")


app = FastAPI(
    title="Dashy API",
    description="Family Calendar Dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DashyError)
async def dashy_error_handler(request: Request, exc: DashyError) -> JSONResponse:
    """Render ``DashyError`` subclasses as RFC 9457 Problem Details responses.

    Args:
        request: The incoming HTTP request.
        exc: The caught Dashy exception.

    Returns:
        A JSON response conforming to RFC 9457.
    """
    body = {
        "type": f"https://dashy.local/errors/{exc.error_code}",
        "title": exc.error_code,
        "status": exc.status_code,
        "detail": exc.message,
    }
    if exc.detail:
        body["detail_extra"] = exc.detail
    logger.warning(
        "dashy_error",
        error_code=exc.error_code,
        status_code=exc.status_code,
        detail=exc.message,
    )
    return JSONResponse(status_code=exc.status_code, content=body)


# Include routers under /api/v1
app.include_router(weather.router, prefix="/api/v1")
app.include_router(calendar.router, prefix="/api/v1")
app.include_router(family.router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict:
    """Return service health status including cache stats."""
    cache = await get_cache()
    stats = cache.get_stats()
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "cache": {
            "connected": cache.is_connected,
            "hits": stats.hits,
            "misses": stats.misses,
            "errors": stats.errors,
        },
    }


@app.get("/")
def root() -> dict:
    """Return a simple liveness probe message."""
    return {"message": "Dashy API is running"}
