"""SQLModel database models."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Uuid
from sqlalchemy.dialects.postgresql import JSONB
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

    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    name: str
    category_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("chore_categories.id"), nullable=False),
    )
    difficulty: int = Field(default=1)
    recurrence_rule: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: date | None = None
    expiration_behavior: str = Field(default="disappear")
    end_date: date | None = None
    max_occurrences: int | None = None
    occurrence_count: int = Field(default=0)
    conditions: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    is_collaborative: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default="false", nullable=False),
    )
    created_by: str = Field(default="")
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

    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    master_chore_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("master_chores.id"), nullable=False),
    )
    association_id: UUID | None = Field(
        default=None,
        sa_column=Column(Uuid, ForeignKey("chore_associations.id"), nullable=True),
    )
    period_start: date | None = None
    period_end: date | None = None
    status: str = Field(default="active")
    claimed_by: str | None = None
    assigned_to: str | None = None
    assigned_by: str | None = None
    completed_by: str | None = None
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
    """Association between a master chore and a member or open pool."""

    __tablename__ = "chore_associations"

    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    master_chore_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("master_chores.id"), nullable=False),
    )
    member_id: str | None = None
    is_open_pool: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default="false", nullable=False),
    )
    created_by: str = Field(default="")
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
