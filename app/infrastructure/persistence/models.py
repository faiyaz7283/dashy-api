"""SQLModel database models."""

from datetime import date, datetime

from sqlmodel import Field, SQLModel


class FamilyMemberDB(SQLModel, table=True):
    """Family member database model.

    The canonical family registry table. Stores personal info used
    across all features (calendar, rewards, permissions, etc.).
    """

    __tablename__ = "family_members"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)
    name: str
    email: str
    color: str
    initial: str
    date_of_birth: date | None = Field(default=None)
    relation: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow}
    )


class ChoreCategoryDB(SQLModel, table=True):
    """Chore category database model."""

    __tablename__ = "chore_categories"

    id: str = Field(primary_key=True)
    name: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChoreTagDB(SQLModel, table=True):
    """Chore tag database model."""

    __tablename__ = "chore_tags"

    id: str = Field(primary_key=True)
    name: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MasterChoreDB(SQLModel, table=True):
    """Master chore template database model."""

    __tablename__ = "master_chores"

    id: str = Field(primary_key=True)
    name: str
    category_id: str = Field(foreign_key="chore_categories.id")
    difficulty: int = Field(default=1)
    frequency: str = Field(default="once")
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: str | None = None
    expiration_behavior: str = Field(default="disappear")
    created_by: str = Field(default="")
    approved_by: str | None = None
    status: str = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None


class ChoreInstanceDB(SQLModel, table=True):
    """Chore instance database model."""

    __tablename__ = "chore_instances"

    id: str = Field(primary_key=True)
    master_chore_id: str = Field(foreign_key="master_chores.id")
    period_start: str | None = None
    period_end: str | None = None
    status: str = Field(default="active")
    claimed_by: str | None = None
    assigned_to: str | None = None
    assigned_by: str | None = None
    completed_by: str | None = None
    signoff_by: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    signed_off_at: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChoreTagLinkDB(SQLModel, table=True):
    """Many-to-many link between master chores and tags."""

    __tablename__ = "chore_tag_links"

    master_chore_id: str = Field(foreign_key="master_chores.id", primary_key=True)
    tag_id: str = Field(foreign_key="chore_tags.id", primary_key=True)
