"""Family domain entities.

Domain entities representing family members.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class FamilyMember:
    """Family member entity.

    Represents a person in the family registry. This is the canonical
    source of member identity used across all features (calendar, rewards,
    permissions, etc.).

    Attributes:
        id: Unique business identifier (member key, e.g. "faiyaz").
        name: Display name.
        email: Email address (also used as Google Calendar ID).
        color: Hex color code for UI color-coding.
        initial: Single character initial for display.
        date_of_birth: Optional date of birth.
        relation: Optional relationship label (e.g. "father", "daughter").
    """

    id: str
    name: str
    email: str
    color: str
    initial: str
    date_of_birth: date | None = field(default=None)
    relation: str | None = field(default=None)

    def __eq__(self, other: object) -> bool:
        """Check equality based on identity (id).

        Args:
            other: Another object to compare.

        Returns:
            True if same id, False otherwise.
        """
        if not isinstance(other, FamilyMember):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity (id).

        Returns:
            Hash value based on id.
        """
        return hash(self.id)
