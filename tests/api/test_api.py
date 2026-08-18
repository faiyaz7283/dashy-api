"""Tests for the Dashy API endpoints.

This module contains integration tests for all API endpoints to verify
they return the expected response structure and status codes.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "environment" in data


@pytest.mark.asyncio
async def test_root():
    """Test the root endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


@pytest.mark.asyncio
async def test_get_calendar():
    """Test the calendar endpoint returns events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/calendar")
        assert response.status_code == 200
        data = response.json()
        assert "week_start" in data
        assert "week_end" in data
        assert "events" in data
        assert isinstance(data["events"], list)


@pytest.mark.asyncio
async def test_get_weather():
    """Test the weather endpoint returns current and forecast."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/weather")
        assert response.status_code == 200
        data = response.json()
        assert "current" in data
        assert "forecast" in data
        assert "temperature" in data["current"]
        assert isinstance(data["forecast"], list)


@pytest.mark.asyncio
async def test_get_family_members():
    """Test the family members endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/family")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Database may be empty in test environment, just verify structure
        if len(data) > 0:
            # Each member should have required fields
            for member in data:
                assert "name" in member
                assert "key" in member
                assert "email" in member
                assert "color" in member
                assert "initial" in member
