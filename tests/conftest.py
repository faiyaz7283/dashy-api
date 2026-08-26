"""Shared pytest fixtures for Dashy tests.

Provides test configuration, mock providers, and container overrides
for unit, integration, and API tests.

Test isolation uses PostgreSQL — tables are created once per session,
and individual tests clean their own data as needed.
"""

import os
from unittest.mock import AsyncMock

import pytest

# Configure test environment BEFORE any app imports.
# This ensures Settings reads POSTGRES_* from .env.test, not defaults.
os.environ.setdefault("ENVIRONMENT", "testing")

from dotenv import load_dotenv

load_dotenv(".env.test", override=True)

from app.config import Settings  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
async def setup_test_database():
    """Create database tables before any tests run.

    This fixture runs once per test session and ensures all SQLModel
    tables exist in the test PostgreSQL database with the current schema.
    Seeds the database with test family members for tests that need them.
    """
    from app.core.database import create_db_and_tables, dispose_engine, get_async_session_factory
    from app.domain.family.models import FamilyMember
    from app.infrastructure.persistence.family_repository import FamilyRepositoryImpl

    await create_db_and_tables()

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        repo = FamilyRepositoryImpl(session)
        existing = await repo.get_all()
        if not existing:
            test_members = [
                FamilyMember(
                    id="faiyaz",
                    name="Faiyaz",
                    email="faiyaz@test.com",
                    color="#4A90E2",
                    initial="F",
                ),
                FamilyMember(
                    id="trisha",
                    name="Trisha",
                    email="trisha@test.com",
                    color="#E24A8D",
                    initial="T",
                ),
            ]
            for member in test_members:
                await repo.save(member)

    yield

    await dispose_engine()


@pytest.fixture
def test_settings() -> Settings:
    """Load test configuration from .env.test.

    Returns:
        Settings instance configured for testing.
    """
    return Settings(_env_file=".env.test")


@pytest.fixture
def mock_weather_provider() -> AsyncMock:
    """Mock weather provider for unit tests.

    Returns:
        AsyncMock configured with weather provider methods.
    """
    provider = AsyncMock()
    provider.get_current.return_value = None
    provider.get_hourly.return_value = []
    provider.get_daily.return_value = []
    return provider


@pytest.fixture
def mock_calendar_provider() -> AsyncMock:
    """Mock calendar provider for unit tests.

    Returns:
        AsyncMock configured with calendar provider methods.
    """
    provider = AsyncMock()
    provider.fetch_events.return_value = []
    return provider
