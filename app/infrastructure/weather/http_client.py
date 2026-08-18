"""Shared HTTP client for weather API calls.

Provides a singleton httpx.AsyncClient with connection pooling
to reduce latency and resource usage.
"""

from functools import lru_cache

import httpx


@lru_cache
def get_http_client() -> httpx.AsyncClient:
    """Get a shared HTTP client with connection pooling.

    Returns:
        Configured httpx.AsyncClient instance.
    """
    return httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    )
