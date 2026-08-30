"""Dashy FastAPI application entry point.

Configures middleware, exception handlers, and router registration.
Kept minimal — all cross-cutting concerns live in ``app.core``.
"""

from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import calendar, chores, config, family, metrics, weather
from app.config import settings
from app.core.cache import close_cache, get_cache
from app.core.database import check_connection
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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Render ``HTTPException`` as RFC 9457 Problem Details responses.

    Ensures all HTTP errors use the same format as DashyError responses.

    Args:
        request: The incoming HTTP request.
        exc: The caught HTTPException.

    Returns:
        A JSON response conforming to RFC 9457.
    """
    # Map common status codes to error codes
    error_code_map = {
        400: "bad-request",
        401: "unauthorized",
        403: "forbidden",
        404: "not-found",
        409: "conflict",
        422: "unprocessable-entity",
        500: "internal-error",
        503: "service-unavailable",
    }

    error_code = error_code_map.get(exc.status_code, "http-error")
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    body = {
        "type": f"https://dashy.local/errors/{error_code}",
        "title": error_code,
        "status": exc.status_code,
        "detail": detail,
    }

    logger.warning(
        "http_error",
        status_code=exc.status_code,
        detail=detail,
    )
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Render ``RequestValidationError`` as RFC 9457 Problem Details responses.

    Args:
        request: The incoming HTTP request.
        exc: The caught RequestValidationError.

    Returns:
        A JSON response conforming to RFC 9457.
    """
    # Convert errors to JSON-serializable format
    errors = []
    for error in exc.errors():
        error_dict = {
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        # Only include ctx if it's JSON-serializable
        if "ctx" in error:
            try:
                import json
                json.dumps(error["ctx"])
                error_dict["ctx"] = error["ctx"]
            except (TypeError, ValueError):
                error_dict["ctx"] = str(error["ctx"])
        errors.append(error_dict)

    logger.warning(
        "validation_error",
        status_code=422,
        detail=str(errors),
    )
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://dashy.local/errors/validation-error",
            "title": "validation-error",
            "status": 422,
            "detail": "Request validation failed",
            "errors": errors,
        },
    )


# Include routers under /api/v1
app.include_router(weather.router, prefix="/api/v1")
app.include_router(calendar.router, prefix="/api/v1")
app.include_router(family.router, prefix="/api/v1")
app.include_router(chores.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")


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


@app.get("/health/db")
async def database_health_check() -> dict:
    """Return database connection health status.

    Returns:
        Dict with status and latency if healthy, 503 if unhealthy.
    """
    start = perf_counter()
    is_healthy = await check_connection()
    latency_ms = round((perf_counter() - start) * 1000, 2)

    if is_healthy:
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
        }
    else:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "latency_ms": latency_ms,
            },
        )


@app.get("/")
def root() -> dict:
    """Return a simple liveness probe message."""
    return {"message": "Dashy API is running"}
