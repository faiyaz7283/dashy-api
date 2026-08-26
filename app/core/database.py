"""Database configuration and session management.

Reads the database URL from the application Settings (single source of truth).
Configures PostgreSQL connection pooling with health checks.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.config import settings

DATABASE_URL = settings.database_url

_async_engine = None
_async_session_factory = None


def get_async_engine():
    """Get or create the async engine.

    Returns:
        The shared async SQLAlchemy engine.
    """
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=0,
            connect_args={
                "server_settings": {"jit": "off"},
                "command_timeout": 60,
                "timeout": 30,
            },
        )
    return _async_engine


def get_async_session_factory():
    """Get or create the async session factory.

    Returns:
        Session factory bound to the async engine.
    """
    global _async_session_factory
    if _async_session_factory is None:
        async_engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession]:
    """Provide a transactional database session.

    Creates a new session, commits on success, rolls back on exception.

    Yields:
        AsyncSession: Database session for operations.
    """
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_session():
    """FastAPI dependency for async database sessions.

    Yields:
        An async SQLModel session.
    """
    factory = get_async_session_factory()
    async with factory() as session:
        yield session


async def check_connection() -> bool:
    """Check if database connection is working.

    Returns:
        True if connection is successful, False otherwise.
    """
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


async def create_db_and_tables():
    """Create all database tables.

    Warning: For development/testing only. Production should use Alembic.
    """
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def drop_all_tables():
    """Drop all database tables.

    Warning: This will delete all data. Only use for testing.
    """
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


async def dispose_engine():
    """Close all database connections.

    Should be called during application shutdown.
    """
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
