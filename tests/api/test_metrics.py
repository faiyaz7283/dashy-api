"""Tests for metrics API endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200():
    """Test that metrics endpoint returns 200 when enabled."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_endpoint_structure():
    """Test that metrics endpoint returns correct structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200

        data = response.json()

        # Check top-level keys
        assert "weather" in data
        assert "calendar" in data
        assert "network" in data
        assert "cache" in data

        # Check weather structure
        weather = data["weather"]
        assert "status" in weather
        assert "age_seconds" in weather
        assert "fresh_ttl" in weather
        assert "stale_ttl" in weather
        assert "last_fetch" in weather

        # Check calendar structure
        calendar = data["calendar"]
        assert "status" in calendar
        assert "age_seconds" in calendar
        assert "fresh_ttl" in calendar
        assert "stale_ttl" in calendar
        assert "last_fetch" in calendar
        assert "members" in calendar

        # Check network structure
        network = data["network"]
        assert "google_calendar" in network
        assert "openweathermap" in network

        # Check cache structure
        cache = data["cache"]
        assert "hits" in cache
        assert "misses" in cache
        assert "errors" in cache


@pytest.mark.asyncio
async def test_metrics_calendar_members():
    """Test that metrics endpoint includes per-member calendar data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200

        data = response.json()
        members = data["calendar"]["members"]

        # Should have at least one member (from seed data)
        assert isinstance(members, dict)

        # Each member should have the correct structure
        for _member_id, member_data in members.items():
            assert "status" in member_data
            assert "last_fetch" in member_data
            assert "event_count" in member_data
            assert "error" in member_data

            # Status should be one of the valid values
            assert member_data["status"] in ["fresh", "stale", "missing", "success", "failed"]


@pytest.mark.asyncio
async def test_metrics_data_status_values():
    """Test that data status values are valid."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200

        data = response.json()

        # Weather status should be valid
        assert data["weather"]["status"] in ["fresh", "stale", "missing"]

        # Calendar status should be valid
        assert data["calendar"]["status"] in ["fresh", "stale", "missing"]


@pytest.mark.asyncio
async def test_metrics_ttl_values():
    """Test that TTL values are present and reasonable."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200

        data = response.json()

        # Weather TTL values should be positive
        assert data["weather"]["fresh_ttl"] > 0
        assert data["weather"]["stale_ttl"] > 0
        assert data["weather"]["stale_ttl"] > data["weather"]["fresh_ttl"]

        # Calendar TTL values should be positive
        assert data["calendar"]["fresh_ttl"] > 0
        assert data["calendar"]["stale_ttl"] > 0
        assert data["calendar"]["stale_ttl"] > data["calendar"]["fresh_ttl"]


@pytest.mark.asyncio
async def test_metrics_network_health_structure():
    """Test that network health has correct structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200

        data = response.json()
        network = data["network"]

        # Check Google Calendar health
        assert "google_calendar" in network
        gcal = network["google_calendar"]
        assert "reachable" in gcal
        assert "last_check" in gcal

        # Check OpenWeatherMap health
        assert "openweathermap" in network
        owm = network["openweathermap"]
        assert "reachable" in owm
        assert "last_check" in owm


@pytest.mark.asyncio
async def test_metrics_cache_statistics():
    """Test that cache statistics are present."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200

        data = response.json()
        cache = data["cache"]

        # Cache stats should be non-negative integers
        assert isinstance(cache["hits"], int)
        assert cache["hits"] >= 0

        assert isinstance(cache["misses"], int)
        assert cache["misses"] >= 0

        assert isinstance(cache["errors"], int)
        assert cache["errors"] >= 0
