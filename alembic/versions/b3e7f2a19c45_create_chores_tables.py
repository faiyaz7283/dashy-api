"""Create chores tables.

Revision ID: b3e7f2a19c45
Revises: a973d5cbbdd8
Create Date: 2026-08-18 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e7f2a19c45"
down_revision: str | Sequence[str] | None = "a973d5cbbdd8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create chores tables and seed preset categories."""
    # chore_categories
    op.create_table(
        "chore_categories",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chore_categories_name"), "chore_categories", ["name"], unique=True
    )

    # chore_tags
    op.create_table(
        "chore_tags",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chore_tags_name"), "chore_tags", ["name"], unique=True
    )

    # master_chores
    op.create_table(
        "master_chores",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "category_id",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "frequency",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="once",
        ),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("due_time", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("due_date", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "expiration_behavior",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="disappear",
        ),
        sa.Column(
            "created_by",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column(
            "approved_by",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["category_id"], ["chore_categories.id"]),
    )

    # chore_tag_links (join table)
    op.create_table(
        "chore_tag_links",
        sa.Column(
            "master_chore_id",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column("tag_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("master_chore_id", "tag_id"),
        sa.ForeignKeyConstraint(["master_chore_id"], ["master_chores.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["chore_tags.id"]),
    )

    # chore_instances
    op.create_table(
        "chore_instances",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "master_chore_id",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column("period_start", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("period_end", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="active",
        ),
        sa.Column("claimed_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("assigned_to", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("assigned_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("completed_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("signoff_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("started_at", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("completed_at", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("signed_off_at", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["master_chore_id"], ["master_chores.id"]),
    )

    # Seed preset categories
    from datetime import datetime

    now = datetime.utcnow().isoformat()
    preset_categories = [
        ("cat-kitchen", "Kitchen"),
        ("cat-bathroom", "Bathroom"),
        ("cat-outdoor", "Outdoor"),
        ("cat-laundry", "Laundry"),
        ("cat-general", "General"),
    ]
    for cat_id, cat_name in preset_categories:
        op.execute(
            f"INSERT INTO chore_categories (id, name, created_at) "
            f"VALUES ('{cat_id}', '{cat_name}', '{now}')"
        )


def downgrade() -> None:
    """Drop chores tables."""
    op.drop_table("chore_instances")
    op.drop_table("chore_tag_links")
    op.drop_table("master_chores")
    op.drop_index(op.f("ix_chore_tags_name"), table_name="chore_tags")
    op.drop_table("chore_tags")
    op.drop_index(op.f("ix_chore_categories_name"), table_name="chore_categories")
    op.drop_table("chore_categories")
