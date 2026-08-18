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
