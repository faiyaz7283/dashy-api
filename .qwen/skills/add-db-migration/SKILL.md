---
name: add-db-migration
description: Workflow for creating and applying Alembic database migrations for Dashy's SQLite database.
---

# Add Database Migration

Workflow for creating and applying Alembic database migrations.

## Prerequisites

- SQLModel ORM models exist in `app/infrastructure/persistence/models.py`
- Alembic is configured (`alembic.ini` + `alembic/` directory exist)
- Database URL is set in environment (`DATABASE_URL` env var or default `sqlite+aiosqlite:///./dashy.db`)

## Steps

### 1. Add or modify SQLModel

Edit `app/infrastructure/persistence/models.py`:

```python
from sqlmodel import SQLModel, Field
from datetime import datetime

class NewTable(SQLModel, table=True):
    """New table docstring."""
    __tablename__ = "new_table"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**Conventions:**
- Table name: `snake_case`, plural (`family_members`, `shopping_lists`)
- Primary key: `id: int | None = Field(default=None, primary_key=True)`
- Indexes: Add `index=True` to frequently queried fields
- Timestamps: `created_at` and `updated_at` with `default_factory=datetime.utcnow`

### 2. Generate migration

```bash
uv run alembic revision --autogenerate -m "add_new_table"
```

This creates a new file in `alembic/versions/<hash>_add_new_table.py`.

### 3. Review generated migration

Open the generated migration file and verify:

```python
def upgrade() -> None:
    op.create_table(
        'new_table',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_new_table_name'), 'new_table', ['name'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_new_table_name'), table_name='new_table')
    op.drop_table('new_table')
```

**Check:**
- ✅ All columns are present with correct types
- ✅ Indexes are created for indexed fields
- ✅ `downgrade()` properly reverses `upgrade()`
- ✅ No data loss in downgrade (or document if intentional)

### 4. Apply migration

```bash
uv run alembic upgrade head
```

Verify tables were created:

```bash
uv run python -c "from app.core.database import sync_engine; from sqlmodel import SQLModel; print(SQLModel.metadata.tables.keys())"
```

### 5. Test rollback

```bash
# Rollback one step
uv run alembic downgrade -1

# Verify table is gone
# Then re-apply
uv run alembic upgrade head
```

**Why test rollback?** Ensures migrations are reversible for deployment rollbacks.

### 6. Update repository (if needed)

If this migration adds a new table, create or update the repository:

```python
# app/infrastructure/persistence/new_table_repository.py
from sqlmodel import select
from app.core.database import get_async_session

class NewTableRepository:
    """Repository for NewTable persistence."""

    async def get_all(self) -> list[NewTable]:
        async for session in get_async_session():
            result = await session.execute(select(NewTable))
            return list(result.scalars().all())
```

### 7. Add tests

Create integration test in `tests/integration/test_<domain>_repository.py`:

```python
import pytest
from app.infrastructure.persistence.new_table_repository import NewTableRepository

@pytest.mark.asyncio
async def test_new_table_crud():
    repo = NewTableRepository()

    # Create
    item = NewTable(name="test")
    await repo.save(item)

    # Read
    items = await repo.get_all()
    assert len(items) == 1
    assert items[0].name == "test"

    # Delete
    await repo.delete(item.id)
    items = await repo.get_all()
    assert len(items) == 0
```

### 8. Run quality gate

```bash
uv run ruff check app/ tests/ && uv run python -m compileall app/ && uv run pytest tests/ -v
```

## Common patterns

### Adding a column to existing table

```python
# In models.py, add field to existing SQLModel
class ExistingTable(SQLModel, table=True):
    # ... existing fields
    new_field: str = Field(default="default_value")
```

Generate migration — Alembic will detect the new column and add `op.add_column()`.

### Renaming a table or column

```bash
# Generate empty migration
uv run alembic revision -m "rename_old_to_new"
```

Manually edit the migration:

```python
def upgrade() -> None:
    op.rename_table('old_name', 'new_name')
    # or for columns:
    op.alter_column('table_name', 'old_column', new_column_name='new_column')

def downgrade() -> None:
    op.rename_table('new_name', 'old_name')
```

### Adding a foreign key

```python
class ChildTable(SQLModel, table=True):
    parent_id: int = Field(foreign_key="parent_table.id")
```

Alembic will generate `op.create_foreign_key()`.

## Troubleshooting

**"No changes detected"**
- Ensure model has `table=True`
- Check `__tablename__` is set
- Verify model is imported in `alembic/env.py`

**"Table already exists"**
- Migration was applied but not recorded in `alembic_version` table
- Manually insert: `INSERT INTO alembic_version VALUES '<revision_id>'`

**Migration fails on apply**
- Check SQL syntax in generated migration
- Verify column types are SQLite-compatible
- Test migration on a fresh database

## Database persistence

**Important:** SQLite database file should be volume-mounted when running in Docker to persist across container restarts. Configure `DATABASE_URL` in `.env` accordingly.
