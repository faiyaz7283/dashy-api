"""Database configuration and session management.

Reads the database URL from the application Settings (single source of truth).
Enables WAL mode for SQLite to support concurrent reads/writes on the Pi.
"""

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# Database URL from Settings (single source of truth)
DATABASE_URL = settings.DATABASE_URL

# Convert async URL to sync URL for migrations
SYNC_DATABASE_URL = DATABASE_URL.replace("+aiosqlite", "")


def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode and foreign keys on SQLite connections.

    WAL mode allows concurrent readers and a single writer, which is
    important for the Pi deployment where the kiosk may poll while
    background tasks write.
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Synchronous engine for migrations
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)
event.listen(sync_engine, "connect", _set_sqlite_pragma)

# Async engine for application (lazily initialized)
_async_engine = None


def get_async_engine():
    """Get or create the async engine.

    Returns:
        The shared async SQLAlchemy engine.
    """
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(DATABASE_URL, echo=False)
        event.listen(_async_engine.sync_engine, "connect", _set_sqlite_pragma)
    return _async_engine


# Async session factory (lazily initialized)
_async_session_local = None


def get_async_session_factory():
    """Get or create the async session factory.

    Returns:
        Session factory bound to the async engine.
    """
    global _async_session_local
    if _async_session_local is None:
        async_engine = get_async_engine()
        _async_session_local = sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_local


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(sync_engine)


def get_session():
    """Get synchronous database session.

    Yields:
        A synchronous SQLModel session.
    """
    with Session(sync_engine) as session:
        yield session


async def get_async_session():
    """Get asynchronous database session.

    Yields:
        An async SQLModel session.
    """
    async_session_local = get_async_session_factory()
    async with async_session_local() as session:
        yield session
