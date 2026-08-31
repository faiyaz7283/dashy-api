---
name: add-repository
description: Create a new repository for database persistence — implement Protocol, add SQLModel, create Alembic migration, and wire into DI container.
---

# Add Repository

Create a new repository for database persistence following Dashy's patterns.

## When to use

- Adding database persistence for a new domain
- Creating a repository for an existing domain that doesn't have one yet
- Not for adding new tables to existing repositories — use `/add-db-migration` instead

## Prerequisites

- Domain exists with `Repository` Protocol defined in `app/domain/<domain>/ports.py`
- SQLModel and Alembic configured (they are — see `app/core/database.py`)
- Understand the data you need to persist

## Steps

### 1. Review the Protocol

Read the existing Protocol:

```python
# app/domain/family/ports.py
class FamilyRepository(Protocol):
    async def get_all(self) -> list[FamilyMember]:
        """Retrieve all family members."""
        ...

    async def get_by_id(self, member_id: str) -> FamilyMember | None:
        """Retrieve a family member by ID."""
        ...

    async def save(self, member: FamilyMember) -> None:
        """Save a family member."""
        ...

    async def delete(self, member_id: str) -> None:
        """Delete a family member."""
        ...
```

### 2. Add SQLModel to persistence models

Edit `app/infrastructure/persistence/models.py`:

```python
"""Database models for persistence."""

from datetime import datetime
from sqlmodel import SQLModel, Field


class <Domain>DB(SQLModel, table=True):
    """<Domain> database model.

    Maps domain entity to database table.
    """

    __tablename__ = "<domain>s"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)
    name: str
    # ... other fields

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow}
    )
```

**Conventions:**
- Table name: `snake_case`, plural (`family_members`, `shopping_lists`)
- Primary key: `id: int | None = Field(default=None, primary_key=True)`
- Unique constraints: `Field(unique=True)`
- Indexes: `Field(index=True)` for frequently queried fields
- Timestamps: `created_at` and `updated_at` with auto-update

### 3. Generate Alembic migration

```bash
docker compose -f compose/docker-compose.dev.yml exec -T api uv run alembic revision --autogenerate -m "add_<domain>s_table"
```

Review the generated migration in `alembic/versions/<hash>_add_<domain>s_table.py`:

```python
def upgrade() -> None:
    op.create_table(
        '<domain>s',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_<domain>s_key'), '<domain>s', ['key'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_<domain>s_key'), table_name='<domain>s')
    op.drop_table('<domain>s')
```

### 4. Apply migration

```bash
docker compose -f compose/docker-compose.dev.yml exec -T api uv run alembic upgrade head
```

### 5. Create repository implementation

Create `app/infrastructure/persistence/<domain>_repository.py`:

```python
"""<Domain> repository implementation.

PostgreSQL-backed implementation of <Domain>Repository Protocol.
"""

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.<domain>.models import <Domain>Entity, <Domain>Id
from app.domain.<domain>.ports import <Domain>Repository
from app.infrastructure.persistence.models import <Domain>DB
from app.core.logging import get_logger

logger = get_logger(__name__)


class <Domain>RepositoryImpl:
    """PostgreSQL-backed implementation of <Domain>Repository.

    Provides persistent storage for <domain> entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository.

        Args:
            session: Async database session.
        """
        self.session = session

    async def get_all(self) -> list[<Domain>Entity]:
        """Retrieve all <domain> entities from database.

        Returns:
            List of <Domain>Entity instances.
        """
        result = await self.session.execute(select(<Domain>DB))
        db_models = result.scalars().all()
        return [self._to_entity(db) for db in db_models]

    async def get_by_id(self, entity_id: str) -> <Domain>Entity | None:
        """Retrieve <domain> entity by ID.

        Args:
            entity_id: Entity identifier.

        Returns:
            <Domain>Entity if found, None otherwise.
        """
        result = await self.session.execute(
            select(<Domain>DB).where(<Domain>DB.key == entity_id)
        )
        db_model = result.scalar_one_or_none()

        if db_model is None:
            return None

        return self._to_entity(db_model)

    async def save(self, entity: <Domain>Entity) -> None:
        """Save <domain> entity to database.

        Creates new record or updates existing one.

        Args:
            entity: <Domain>Entity to save.
        """
        # Check if exists
        existing = await self.get_by_id(entity.id.value)

        if existing:
            # Update
            db_model = await self._get_db_model(entity.id.value)
            db_model.name = entity.name
            # ... update other fields
        else:
            # Create
            db_model = self._to_db_model(entity)
            self.session.add(db_model)

        await self.session.commit()
        logger.info("<domain>_saved", entity_id=entity.id.value)

    async def delete(self, entity_id: str) -> None:
        """Delete <domain> entity from database.

        Args:
            entity_id: Entity identifier.
        """
        db_model = await self._get_db_model(entity_id)

        if db_model:
            await self.session.delete(db_model)
            await self.session.commit()
            logger.info("<domain>_deleted", entity_id=entity_id)

    async def _get_db_model(self, entity_id: str) -> <Domain>DB | None:
        """Get database model by ID.

        Args:
            entity_id: Entity identifier.

        Returns:
            <Domain>DB if found, None otherwise.
        """
        result = await self.session.execute(
            select(<Domain>DB).where(<Domain>DB.key == entity_id)
        )
        return result.scalar_one_or_none()

    def _to_entity(self, db_model: <Domain>DB) -> <Domain>Entity:
        """Convert database model to domain entity.

        Args:
            db_model: Database model instance.

        Returns:
            Domain entity instance.
        """
        return <Domain>Entity(
            id=<Domain>Id(value=db_model.key),
            name=db_model.name,
            # ... map other fields
        )

    def _to_db_model(self, entity: <Domain>Entity) -> <Domain>DB:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity instance.

        Returns:
            Database model instance.
        """
        return <Domain>DB(
            key=entity.id.value,
            name=entity.name,
            # ... map other fields
        )
```

**Key patterns:**
- Inject `AsyncSession` via constructor
- Use `select()` for queries
- Convert between DB model and domain entity
- Log important operations
- Handle both create and update in `save()`

### 6. Add repository factory to DI container

Edit `app/core/container.py`:

```python
from app.core.database import get_async_session_factory
from app.domain.<domain>.ports import <Domain>Repository
from app.infrastructure.persistence.<domain>_repository import <Domain>RepositoryImpl


async def get_<domain>_repository() -> <Domain>Repository:
    """Get <domain> repository with async database session.

    Returns:
        <Domain>Repository instance.
    """
    async_session_factory = get_async_session_factory()
    async with async_session_factory() as session:
        return <Domain>RepositoryImpl(session)
```

### 7. Add dependency to API deps

Edit `app/api/deps.py`:

```python
from typing import Annotated
from fastapi import Depends
from app.core.container import get_<domain>_repository
from app.domain.<domain>.ports import <Domain>Repository

<Domain>RepositoryDep = Annotated[<Domain>Repository, Depends(get_<domain>_repository)]
```

### 8. Use in API routes

```python
# app/api/routes/<domain>.py
from fastapi import APIRouter
from app.api.deps import <Domain>RepositoryDep
from app.api.models.<domain> import <Domain>Response

router = APIRouter(prefix="/<domain>", tags=["<domain>"])


@router.get("", response_model=list[<Domain>Response])
async def get_<domain>s(
    repository: <Domain>RepositoryDep,
) -> list[<Domain>Response]:
    """Get all <domain> entities.

    Args:
        repository: Injected <domain> repository.

    Returns:
        List of <Domain>Response instances.
    """
    entities = await repository.get_all()
    return [<Domain>Response.from_entity(e) for e in entities]
```

### 9. Add integration tests

Create `tests/integration/test_<domain>_repository.py`:

```python
import pytest
from app.core.database import get_async_session_factory
from app.domain.<domain>.models import <Domain>Entity, <Domain>Id
from app.infrastructure.persistence.<domain>_repository import <Domain>RepositoryImpl


@pytest.mark.asyncio
async def test_<domain>_repository_crud():
    """Test repository CRUD operations with real PostgreSQL."""
    # Arrange
    async_session_factory = get_async_session_factory()
    async with async_session_factory() as session:
        repo = <Domain>RepositoryImpl(session)

        entity = <Domain>Entity(
            id=<Domain>Id(value="test-1"),
            name="Test Entity"
        )

        # Act - Create
        await repo.save(entity)

        # Assert - Read
        result = await repo.get_by_id("test-1")
        assert result is not None
        assert result.name == "Test Entity"

        # Act - Update
        entity.name = "Updated Name"
        await repo.save(entity)

        # Assert
        result = await repo.get_by_id("test-1")
        assert result.name == "Updated Name"

        # Act - Delete
        await repo.delete("test-1")

        # Assert
        result = await repo.get_by_id("test-1")
        assert result is None


@pytest.mark.asyncio
async def test_<domain>_repository_get_all():
    """Test retrieving all entities."""
    async_session_factory = get_async_session_factory()
    async with async_session_factory() as session:
        repo = <Domain>RepositoryImpl(session)

        # Arrange
        entity1 = <Domain>Entity(id=<Domain>Id(value="1"), name="First")
        entity2 = <Domain>Entity(id=<Domain>Id(value="2"), name="Second")

        await repo.save(entity1)
        await repo.save(entity2)

        # Act
        results = await repo.get_all()

        # Assert
        assert len(results) >= 2

        # Cleanup
        await repo.delete("1")
        await repo.delete("2")
```

### 10. Run quality gate

```bash
make lint-api && make build-api && make test-api
```

## Checklist

- [ ] SQLModel added to `app/infrastructure/persistence/models.py`
- [ ] Alembic migration generated and reviewed
- [ ] Migration applied successfully
- [ ] Repository implementation created
- [ ] All Protocol methods implemented
- [ ] Conversion methods (`_to_entity`, `_to_db_model`) implemented
- [ ] Repository factory added to DI container
- [ ] Dependency added to `app/api/deps.py`
- [ ] Repository used in API routes
- [ ] Integration tests added
- [ ] Quality gate passes

## Example: Adding "shopping list" repository

1. Add `ShoppingListDB` SQLModel to `persistence/models.py`
2. Generate migration: `docker compose -f compose/docker-compose.dev.yml exec -T api uv run alembic revision --autogenerate -m "add_shopping_lists"`
3. Create `app/infrastructure/persistence/shopping_list_repository.py`
4. Implement `ListRepository` Protocol
5. Add `get_shopping_list_repository()` to container
6. Add `ListRepositoryDep` to deps
7. Use in routes
8. Integration tests

## Notes

- Repository should only depend on Protocol, not concrete implementations
- Use async SQLAlchemy sessions (`AsyncSession`)
- Convert between DB model and domain entity at repository boundary
- Log important operations (save, delete)
- Test with real PostgreSQL database (integration tests)
- Follow Google-style docstrings
