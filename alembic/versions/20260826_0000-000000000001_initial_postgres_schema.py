"""initial postgres schema.

Revision ID: 000000000001
Revises:
Create Date: 2026-08-26 00:00:00.000000+00:00

Single consolidated migration for PostgreSQL.
Replaces 5 SQLite migrations with clean PostgreSQL-native schema.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "000000000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables with PostgreSQL-native types."""
    # ── family_members (no FK dependencies) ───────────────────────
    op.create_table(
        "family_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=False),
        sa.Column("initial", sa.String(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("relation", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_family_members_key", "family_members", ["key"])

    # ── chore_categories (no FK dependencies) ─────────────────────
    op.create_table(
        "chore_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── chore_tags (no FK dependencies) ───────────────────────────
    op.create_table(
        "chore_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── master_chores (FK → chore_categories) ─────────────────────
    op.create_table(
        "master_chores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("difficulty", sa.Integer(), server_default="1", nullable=False),
        sa.Column("recurrence_rule", postgresql.JSONB(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("due_time", sa.String(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "expiration_behavior",
            sa.String(),
            server_default="disappear",
            nullable=False,
        ),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("max_occurrences", sa.Integer(), nullable=True),
        sa.Column("occurrence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("conditions", postgresql.JSONB(), nullable=True),
        sa.Column(
            "is_collaborative",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("created_by", sa.String(), server_default="", nullable=False),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["chore_categories.id"],
        ),
    )
    op.create_index(
        "ix_master_chores_category_id", "master_chores", ["category_id"]
    )

    # ── chore_associations (FK → master_chores) ───────────────────
    op.create_table(
        "chore_associations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("master_chore_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.String(), nullable=True),
        sa.Column(
            "is_open_pool",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("created_by", sa.String(), server_default="", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["master_chore_id"],
            ["master_chores.id"],
        ),
    )
    op.create_index(
        "ix_chore_associations_master_chore_id",
        "chore_associations",
        ["master_chore_id"],
    )

    # ── chore_instances (FK → master_chores, chore_associations) ──
    op.create_table(
        "chore_instances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("master_chore_id", sa.Uuid(), nullable=False),
        sa.Column("association_id", sa.Uuid(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("claimed_by", sa.String(), nullable=True),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.Column("assigned_by", sa.String(), nullable=True),
        sa.Column("completed_by", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["association_id"],
            ["chore_associations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["master_chore_id"],
            ["master_chores.id"],
        ),
    )
    op.create_index(
        "ix_chore_instances_master_chore_id",
        "chore_instances",
        ["master_chore_id"],
    )
    op.create_index(
        "ix_chore_instances_association_id",
        "chore_instances",
        ["association_id"],
    )

    # ── chore_tag_links (FK → master_chores, chore_tags) ──────────
    op.create_table(
        "chore_tag_links",
        sa.Column("master_chore_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("master_chore_id", "tag_id"),
        sa.ForeignKeyConstraint(
            ["master_chore_id"],
            ["master_chores.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["chore_tags.id"],
        ),
    )
    op.create_index(
        "ix_chore_tag_links_master_chore_id",
        "chore_tag_links",
        ["master_chore_id"],
    )


def downgrade() -> None:
    """Drop all tables in reverse FK dependency order."""
    op.drop_index("ix_chore_tag_links_master_chore_id", table_name="chore_tag_links")
    op.drop_table("chore_tag_links")

    op.drop_index(
        "ix_chore_instances_association_id", table_name="chore_instances"
    )
    op.drop_index(
        "ix_chore_instances_master_chore_id", table_name="chore_instances"
    )
    op.drop_table("chore_instances")

    op.drop_index(
        "ix_chore_associations_master_chore_id", table_name="chore_associations"
    )
    op.drop_table("chore_associations")

    op.drop_index("ix_master_chores_category_id", table_name="master_chores")
    op.drop_table("master_chores")

    op.drop_table("chore_tags")
    op.drop_table("chore_categories")

    op.drop_index("ix_family_members_key", table_name="family_members")
    op.drop_table("family_members")
