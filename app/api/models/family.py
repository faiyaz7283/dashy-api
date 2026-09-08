"""Family API models.

Pydantic models for family API requests and responses.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class FamilyMember(BaseModel):
    """A family member with display preferences and personal info.

    Attributes:
        id: Database UUID primary key (used as FK in chores/rewards).
        name: Display name.
        key: Unique identifier for the family member.
        email: Email address (also used as Google Calendar ID).
        color: Hex color code for UI color-coding.
        initial: Single character initial for display.
        date_of_birth: Optional date of birth.
        relation: Optional relationship label (e.g. "father", "daughter").
    """

    id: UUID
    name: str
    key: str
    email: str
    color: str
    initial: str
    date_of_birth: date | None = None
    relation: str | None = None
