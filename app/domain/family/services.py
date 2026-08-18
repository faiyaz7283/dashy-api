"""Family domain services.

Pure business logic for family member management.
"""

from app.domain.family.models import FamilyMember
from app.domain.family.ports import FamilyRepository


class FamilyService:
    """Service for family member operations.

    Encapsulates business logic for managing family members.
    """

    def __init__(self, repository: FamilyRepository) -> None:
        """Initialize family service.

        Args:
            repository: Family member data repository.
        """
        self.repository = repository

    async def get_all_members(self) -> list[FamilyMember]:
        """Retrieve all family members.

        Returns:
            List of all family members.
        """
        return await self.repository.get_all()

    async def get_member(self, member_id: str) -> FamilyMember | None:
        """Retrieve a family member by ID.

        Args:
            member_id: Unique identifier for the member.

        Returns:
            FamilyMember if found, None otherwise.
        """
        return await self.repository.get_by_id(member_id)

    async def add_member(self, member: FamilyMember) -> None:
        """Add a new family member.

        Args:
            member: FamilyMember to add.
        """
        await self.repository.save(member)

    async def update_member(self, member: FamilyMember) -> None:
        """Update an existing family member.

        Args:
            member: FamilyMember with updated data.
        """
        await self.repository.save(member)

    async def delete_member(self, member_id: str) -> None:
        """Delete a family member.

        Args:
            member_id: Unique identifier for the member to delete.
        """
        await self.repository.delete(member_id)
