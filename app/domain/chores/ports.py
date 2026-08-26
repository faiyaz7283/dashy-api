"""Chores domain ports (interfaces).

Defines the contracts for chores data access.
"""

from datetime import date
from typing import Protocol

from app.domain.chores.models import (
    ChoreAssociation,
    ChoreCategory,
    ChoreInstance,
    ChoreTag,
    MasterChore,
    MasterChoreStatus,
)


class ChoresRepository(Protocol):
    """Protocol for chores data access.

    Implementations provide access to chore data from various sources
    (database, mock data, etc.).
    """

    async def get_categories(self) -> list[ChoreCategory]:
        """Retrieve all chore categories.

        Returns:
            List of all chore categories.
        """
        ...

    async def create_category(self, name: str) -> ChoreCategory:
        """Create a new chore category.

        Args:
            name: Category display name.

        Returns:
            The newly created category.
        """
        ...

    async def get_tags(self) -> list[ChoreTag]:
        """Retrieve all chore tags.

        Returns:
            List of all chore tags.
        """
        ...

    async def create_tag(self, name: str) -> ChoreTag:
        """Create a new chore tag.

        Args:
            name: Tag display name.

        Returns:
            The newly created tag.
        """
        ...

    async def get_master_chores(self, include_archived: bool = False) -> list[MasterChore]:
        """Retrieve master chore templates.

        Args:
            include_archived: Whether to include soft-deleted masters.

        Returns:
            List of master chores.
        """
        ...

    async def get_master_chore_by_id(self, chore_id: str) -> MasterChore | None:
        """Retrieve a single master chore by ID.

        Args:
            chore_id: Unique identifier for the master chore.

        Returns:
            MasterChore if found, None otherwise.
        """
        ...

    async def create_master_chore(self, chore: MasterChore, tag_ids: list[str]) -> MasterChore:
        """Create a new master chore with tag associations.

        Args:
            chore: MasterChore entity to persist.
            tag_ids: List of tag IDs to associate.

        Returns:
            The newly created master chore.
        """
        ...

    async def update_master_chore(self, chore_id: str, updates: dict) -> MasterChore:
        """Update a master chore with the given fields.

        Args:
            chore_id: Unique identifier for the master chore.
            updates: Dictionary of field names to new values.

        Returns:
            The updated master chore.
        """
        ...

    async def delete_master_chore(self, chore_id: str) -> None:
        """Soft-delete a master chore by setting deleted_at.

        Args:
            chore_id: Unique identifier for the master chore.
        """
        ...

    async def get_instances(self, master_chore_id: str | None = None) -> list[ChoreInstance]:
        """Retrieve chore instances, optionally filtered by master chore.

        Args:
            master_chore_id: If provided, only return instances for this master.

        Returns:
            List of chore instances.
        """
        ...

    async def get_instance_by_id(self, instance_id: str) -> ChoreInstance | None:
        """Retrieve a single chore instance by ID.

        Args:
            instance_id: Unique identifier for the instance.

        Returns:
            ChoreInstance if found, None otherwise.
        """
        ...

    async def create_instance(self, instance: ChoreInstance) -> ChoreInstance:
        """Create a new chore instance.

        Args:
            instance: ChoreInstance entity to persist.

        Returns:
            The newly created instance.
        """
        ...

    async def update_instance(self, instance_id: str, updates: dict) -> ChoreInstance:
        """Update a chore instance with the given fields.

        Args:
            instance_id: Unique identifier for the instance.
            updates: Dictionary of field names to new values.

        Returns:
            The updated instance.
        """
        ...

    async def delete_instance(self, instance_id: str) -> None:
        """Delete a chore instance permanently.

        Args:
            instance_id: Unique identifier for the instance.
        """
        ...

    async def get_association(self, association_id: str) -> ChoreAssociation | None:
        """Retrieve a single chore association by ID.

        Args:
            association_id: Unique identifier for the association.

        Returns:
            ChoreAssociation if found, None otherwise.
        """
        ...

    async def create_association(self, association: ChoreAssociation) -> ChoreAssociation:
        """Create a new chore association.

        Args:
            association: ChoreAssociation entity to persist.

        Returns:
            The newly created association.
        """
        ...

    async def delete_association(self, association_id: str) -> None:
        """Soft-delete a chore association by setting removed_at.

        Args:
            association_id: Unique identifier for the association.
        """
        ...

    async def list_associations(
        self,
        master_chore_id: str | None = None,
        member_id: str | None = None,
        include_removed: bool = False,
    ) -> list[ChoreAssociation]:
        """Retrieve chore associations with optional filters.

        Args:
            master_chore_id: Filter by master chore ID.
            member_id: Filter by member ID.
            include_removed: Whether to include soft-deleted associations.

        Returns:
            List of chore associations.
        """
        ...

    async def get_associations_by_master(self, master_chore_id: str) -> list[ChoreAssociation]:
        """Retrieve all active associations for a master chore.

        Args:
            master_chore_id: Unique identifier for the master chore.

        Returns:
            List of active chore associations.
        """
        ...

    async def get_associations_by_member(self, member_id: str) -> list[ChoreAssociation]:
        """Retrieve all active associations for a member.

        Args:
            member_id: Unique identifier for the member.

        Returns:
            List of active chore associations.
        """
        ...

    async def get_instances_by_association(
        self, association_id: str, active_only: bool = True
    ) -> list[ChoreInstance]:
        """Retrieve instances linked to a specific association.

        Args:
            association_id: FK to the association.
            active_only: If True, only return non-completed/non-archived instances.

        Returns:
            List of matching ChoreInstance entities.
        """
        ...

    async def archive_instances_by_association(self, association_id: str) -> int:
        """Archive all active instances for an association.

        Sets status to ARCHIVED for instances that are ACTIVE or IN_PROGRESS.

        Args:
            association_id: FK to the association.

        Returns:
            Number of instances archived.
        """
        ...

    async def get_instance_for_period(
        self,
        association_id: str,
        period_start: date,
        period_end: date,
    ) -> ChoreInstance | None:
        """Find an existing instance for a specific period and association.

        Used by instance generation to avoid creating duplicates.

        Args:
            association_id: FK to the association.
            period_start: Period start date to match.
            period_end: Period end date to match.

        Returns:
            ChoreInstance if found, None otherwise.
        """
        ...

    async def get_expired_instances(self, today: date) -> list[ChoreInstance]:
        """Retrieve instances past their period_end with non-completed status.

        Used for expiration processing to apply expiration_behavior.

        Args:
            today: Current date to compare against period_end.

        Returns:
            List of ChoreInstance entities that are expired (period_end < today)
            and have status ACTIVE, IN_PROGRESS, or OVERDUE.
        """
        ...

    async def get_overdue_instances(self, today: date, current_time: str) -> list[ChoreInstance]:
        """Retrieve instances past their due time but within their period.

        Used for overdue detection to mark instances as OVERDUE.

        Args:
            today: Current date.
            current_time: Current time in HH:MM format.

        Returns:
            List of ChoreInstance entities that are overdue (due_time passed)
            but still within their period (period_end >= today) and have
            status ACTIVE or IN_PROGRESS.
        """
        ...

    async def bulk_update_master_status(
        self, master_ids: list[str], status: "MasterChoreStatus"
    ) -> int:
        """Update the status of multiple master chores at once.

        Used for bulk pause/resume operations.

        Args:
            master_ids: List of master chore IDs to update.
            status: New status to apply.

        Returns:
            Number of masters actually updated.
        """
        ...
