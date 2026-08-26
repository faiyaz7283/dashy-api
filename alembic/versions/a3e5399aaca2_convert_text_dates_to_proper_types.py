"""Convert text dates to proper types.

Revision ID: a3e5399aaca2
Revises: f39bfa5aac9f
Create Date: 2026-08-26 19:40:44.419268

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'a3e5399aaca2'
down_revision: str | Sequence[str] | None = 'f39bfa5aac9f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema.

    Convert TEXT date/datetime columns to proper Date/DateTime types.

    Note: SQLite uses dynamic typing and stores all dates as TEXT internally.
    This migration documents the type change for clarity and future PostgreSQL
    migration. The Python/SQLModel layer now enforces proper date/datetime types.

    Changed columns:
    - master_chores.due_date: str -> date
    - master_chores.end_date: str -> date
    - chore_instances.period_start: str -> date
    - chore_instances.period_end: str -> date
    - chore_instances.started_at: str -> datetime
    - chore_instances.completed_at: str -> datetime
    """
    # SQLite doesn't require schema changes for type conversion
    # The type enforcement happens at the Python/SQLModel layer


def downgrade() -> None:
    """Downgrade schema.

    Revert Date/DateTime columns back to TEXT (str) types.
    """
    # SQLite doesn't require schema changes for type conversion
