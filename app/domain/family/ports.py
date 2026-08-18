"""Family domain ports (interfaces).

Defines the contracts for family member data access.
"""

from typing import Protocol

from app.domain.family.models import FamilyMember


class FamilyRepository(Protocol):
    """Protocol for family member data access.

    Implementations provide access to family member data from various sources
    (database, configuration files, etc.).
    """

    async def get_all(self) -> list[FamilyMember]:
        """Retrieve all family members.

        Returns:
            List of all family members.
        """
        ...

    async def get_by_id(self, member_id: str) -> FamilyMember | None:
        """Retrieve a family member by ID.

        Args:
            member_id: Unique identifier for the member.

        Returns:
            FamilyMember if found, None otherwise.
        """
        ...

    async def save(self, member: FamilyMember) -> None:
        """Save a family member.

        Args:
            member: FamilyMember to save.
        """
        ...

    async def delete(self, member_id: str) -> None:
        """Delete a family member.

        Args:
            member_id: Unique identifier for the member to delete.
        """
        ...
