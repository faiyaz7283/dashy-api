"""SQLModel database models."""

from datetime import UTC, date, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, SQLModel
from uuid6 import uuid7


class FamilyMemberDB(SQLModel, table=True):
    """Family member database model.

    The canonical family registry table. Stores personal info used
    across all features (calendar, rewards, permissions, etc.).
    """

    __tablename__ = "family_members"

    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    key: str = Field(unique=True, index=True)
    name: str
    email: str
    color: str
    initial: str
    date_of_birth: date | None = Field(default=None)
    relation: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            onupdate=lambda: datetime.now(UTC),
        ),
    )


class ChoreCategoryDB(SQLModel, table=True):
    """Chore category database model."""

    __tablename__ = "chore_categories"

    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    name: str = Field(unique=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ChoreTagDB(SQLModel, table=True):
    """Chore tag database model."""

    __tablename__ = "chore_tags"

    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    name: str = Field(unique=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class MasterChoreDB(SQLModel, table=True):
    """Master chore template database model."""

    __tablename__ = "master_chores"
    __table_args__ = (
        CheckConstraint("difficulty >= 1 AND difficulty <= 5", name="ck_difficulty_range"),
        CheckConstraint(
            "frequency IN ('once','daily','weekly','monthly','yearly')",
            name="ck_frequency_valid",
        ),
        CheckConstraint("frequency_interval >= 1", name="ck_frequency_interval_min"),
        CheckConstraint(
            "day_of_month IS NULL OR (day_of_month >= 1 AND day_of_month <= 31)",
            name="ck_day_of_month_range",
        ),
        CheckConstraint(
            "week_of_month IS NULL OR (week_of_month >= 1 AND week_of_month <= 5)",
            name="ck_week_of_month_range",
        ),
        CheckConstraint(
            "month IS NULL OR (month >= 1 AND month <= 12)",
            name="ck_month_range",
        ),
        CheckConstraint(
            "max_occurrences IS NULL OR max_occurrences > 0",
            name="ck_max_occurrences_positive",
        ),
        CheckConstraint(
            "status IN ('active','inactive','archived')",
            name="ck_master_status_valid",
        ),
    )

    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    name: str
    category_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("chore_categories.id"), nullable=False),
    )
    difficulty: int = Field(default=1)

    # Recurrence (flattened from JSONB)
    frequency: str = Field(default="once")
    frequency_interval: int = Field(default=1)
    day_of_week: list[int] | None = Field(
        default=None,
        sa_column=Column(ARRAY(Integer), nullable=True),
    )
    day_of_month: int | None = None
    week_of_month: int | None = None
    month: int | None = None

    # Timing
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: date | None = None

    # Termination
    end_date: date | None = None
    max_occurrences: int | None = None
    occurrence_count: int = Field(default=0)

    # Metadata
    conditions: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    is_collaborative: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default="false", nullable=False),
    )
    created_by: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("family_members.id"), nullable=False),
    )
    status: str = Field(default="active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            onupdate=lambda: datetime.now(UTC),
        ),
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


class ChoreInstanceDB(SQLModel, table=True):
    """Chore instance database model."""

    __tablename__ = "chore_instances"
    __table_args__ = (
        UniqueConstraint(
            "master_chore_id", "association_id", "period_start",
            name="uq_instance_period",
        ),
        CheckConstraint(
            "assigned_by IS NULL OR member_id != assigned_by",
            name="ck_no_self_assign",
        ),
        CheckConstraint(
            "status IN ('active','in_progress','completed','overdue','missed','archived')",
            name="ck_instance_status_valid",
        ),
    )

    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    master_chore_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("master_chores.id"), nullable=False),
    )
    association_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("chore_associations.id"), nullable=False),
    )
    period_start: date = Field(
        sa_column=Column(sa.Date, nullable=False),
    )
    period_end: date | None = None
    member_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("family_members.id"), nullable=False),
    )
    assigned_by: UUID | None = Field(
        default=None,
        sa_column=Column(Uuid, ForeignKey("family_members.id"), nullable=True),
    )
    status: str = Field(default="active")
    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            onupdate=lambda: datetime.now(UTC),
        ),
    )


class ChoreAssociationDB(SQLModel, table=True):
    """Association between a master chore and a member or open pool.

    member_id NULL = open pool (anyone can claim).
    UNIQUE(master_chore_id, member_id) prevents duplicate associations.
    """

    __tablename__ = "chore_associations"
    __table_args__ = (
        UniqueConstraint(
            "master_chore_id", "member_id",
            name="uq_association_member",
        ),
    )

    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    master_chore_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("master_chores.id"), nullable=False),
    )
    member_id: UUID | None = Field(
        default=None,
        sa_column=Column(Uuid, ForeignKey("family_members.id"), nullable=True),
    )
    created_by: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("family_members.id"), nullable=False),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            onupdate=lambda: datetime.now(UTC),
        ),
    )
    removed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


class ChoreTagLinkDB(SQLModel, table=True):
    """Many-to-many link between master chores and tags."""

    __tablename__ = "chore_tag_links"

    master_chore_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("master_chores.id"), primary_key=True),
    )
    tag_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("chore_tags.id"), primary_key=True),
    )


class ChoreAuditLogDB(SQLModel, table=True):
    """Append-only audit log for all chore entity changes."""

    __tablename__ = "chore_audit_log"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('master_chore','association','instance')",
            name="ck_audit_entity_type",
        ),
        CheckConstraint(
            "action IN ('created','updated','deleted','status_changed')",
            name="ck_audit_action",
        ),
    )

    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    entity_type: str = Field(
        sa_column=Column(sa.String, nullable=False),
    )
    entity_id: UUID = Field(
        sa_column=Column(Uuid, nullable=False),
    )
    action: str = Field(
        sa_column=Column(sa.String, nullable=False),
    )
    actor_id: UUID | None = Field(
        default=None,
        sa_column=Column(Uuid, ForeignKey("family_members.id"), nullable=True),
    )
    old_values: dict | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    new_values: dict | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
