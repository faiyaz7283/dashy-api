"""Chores domain services.

Business logic for chore management including claim/assign
mutual exclusivity and instance status transitions.
"""

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.domain.chores.models import (
    ChoreAssociation,
    ChoreCategory,
    ChoreInstance,
    ChoreTag,
    InstanceStatus,
    MasterChore,
    MasterChoreStatus,
)
from app.domain.chores.ports import ChoresRepository

logger = get_logger(__name__)


class ChoresService:
    """Service for chore operations.

    Encapsulates business logic for managing master chores, instances,
    associations, categories, and tags. Handles claim/assign exclusivity
    and instance status transitions.
    """

    def __init__(self, repository: ChoresRepository) -> None:
        """Initialize chores service.

        Args:
            repository: Chores data repository.
        """
        self.repository = repository

    async def get_all_data(self) -> dict:
        """Retrieve all chores data in a single call.

        Returns categories, tags, master chores, associations,
        and instances for the frontend to render the chore board.

        Returns:
            Dict with keys: categories, tags, master_chores, associations, instances.
        """
        categories = await self.repository.get_categories()
        tags = await self.repository.get_tags()
        master_chores = await self.repository.get_master_chores()
        associations = await self.repository.list_associations()
        instances = await self.repository.get_instances()
        return {
            "categories": categories,
            "tags": tags,
            "master_chores": master_chores,
            "associations": associations,
            "instances": instances,
        }

    async def get_categories(self) -> list[ChoreCategory]:
        """Retrieve all chore categories.

        Returns:
            List of all categories.
        """
        return await self.repository.get_categories()

    async def create_category(self, name: str) -> ChoreCategory:
        """Create a new chore category.

        Args:
            name: Category display name.

        Returns:
            The newly created category.
        """
        return await self.repository.create_category(name)

    async def get_tags(self) -> list[ChoreTag]:
        """Retrieve all chore tags.

        Returns:
            List of all tags.
        """
        return await self.repository.get_tags()

    async def create_tag(self, name: str) -> ChoreTag:
        """Create a new chore tag.

        Args:
            name: Tag display name.

        Returns:
            The newly created tag.
        """
        return await self.repository.create_tag(name)

    async def get_master_chores(self, include_archived: bool = False) -> list[MasterChore]:
        """Retrieve master chore templates.

        Args:
            include_archived: Whether to include soft-deleted masters.

        Returns:
            List of master chores.
        """
        return await self.repository.get_master_chores(include_archived=include_archived)

    async def create_master_chore(
        self,
        chore: MasterChore,
        tag_ids: list[str],
    ) -> MasterChore:
        """Create a new master chore.

        All masters start as active — no approval flow.

        Args:
            chore: MasterChore entity to create.
            tag_ids: List of tag IDs to associate.

        Returns:
            The created master chore.
        """
        chore.status = MasterChoreStatus.ACTIVE

        logger.info(
            "create_master_chore",
            chore_id=chore.id,
            name=chore.name,
            created_by=chore.created_by,
        )
        return await self.repository.create_master_chore(chore, tag_ids)

    async def update_master_chore(
        self, chore_id: str, updates: dict, tag_ids: list[str] | None = None
    ) -> MasterChore:
        """Update a master chore.

        Args:
            chore_id: Unique identifier for the master chore.
            updates: Dictionary of field names to new values.
            tag_ids: If provided, replace the tag associations.

        Returns:
            The updated master chore.
        """
        updates["updated_at"] = datetime.now(UTC)
        return await self.repository.update_master_chore(chore_id, updates)

    async def delete_master_chore(self, chore_id: str) -> None:
        """Soft-delete (archive) a master chore.

        Sets the deleted_at timestamp to mark the chore as archived.

        Args:
            chore_id: Unique identifier for the master chore.
        """
        logger.info("delete_master_chore", chore_id=chore_id)
        await self.repository.delete_master_chore(chore_id)

    async def get_instances(self, master_chore_id: str | None = None) -> list[ChoreInstance]:
        """Retrieve chore instances.

        Args:
            master_chore_id: Optional filter by master chore.

        Returns:
            List of chore instances.
        """
        return await self.repository.get_instances(master_chore_id=master_chore_id)

    async def claim_instance(self, instance_id: str, member_id: str) -> ChoreInstance:
        """Claim a chore instance for a member.

        Setting claimed_by clears assigned_to and assigned_by
        (mutual exclusivity between claim and assign).

        Args:
            instance_id: Unique identifier for the instance.
            member_id: Member ID claiming the instance.

        Returns:
            The updated instance.

        Raises:
            ValueError: If the instance is not found.
        """
        instance = await self.repository.get_instance_by_id(instance_id)
        if not instance:
            raise ValueError(f"Instance '{instance_id}' not found")

        updates: dict = {
            "claimed_by": member_id,
            "assigned_to": None,
            "assigned_by": None,
        }

        logger.info(
            "claim_instance",
            instance_id=instance_id,
            member_id=member_id,
        )
        return await self.repository.update_instance(instance_id, updates)

    async def assign_instance(
        self,
        instance_id: str,
        assignee_id: str,
        assigner_id: str,
    ) -> ChoreInstance:
        """Assign a chore instance to a member.

        Setting assigned_to clears claimed_by (mutual exclusivity
        between claim and assign).

        Args:
            instance_id: Unique identifier for the instance.
            assignee_id: Member ID being assigned.
            assigner_id: Member ID making the assignment.

        Returns:
            The updated instance.

        Raises:
            ValueError: If the instance is not found.
        """
        instance = await self.repository.get_instance_by_id(instance_id)
        if not instance:
            raise ValueError(f"Instance '{instance_id}' not found")

        updates: dict = {
            "assigned_to": assignee_id,
            "assigned_by": assigner_id,
            "claimed_by": None,
        }

        logger.info(
            "assign_instance",
            instance_id=instance_id,
            assignee_id=assignee_id,
            assigner_id=assigner_id,
        )
        return await self.repository.update_instance(instance_id, updates)

    async def update_instance_status(
        self,
        instance_id: str,
        new_status: InstanceStatus,
        actor_id: str,
    ) -> ChoreInstance:
        """Update the status of a chore instance.

        Any member can complete any instance — no approval or signoff required.

        Args:
            instance_id: Unique identifier for the instance.
            new_status: The target status.
            actor_id: Member ID performing the action.

        Returns:
            The updated instance.

        Raises:
            ValueError: If the instance is not found.
        """
        instance = await self.repository.get_instance_by_id(instance_id)
        if not instance:
            raise ValueError(f"Instance '{instance_id}' not found")

        now_iso = datetime.now(UTC).isoformat()
        updates: dict = {"updated_at": datetime.now(UTC)}

        if new_status == InstanceStatus.IN_PROGRESS:
            updates["status"] = InstanceStatus.IN_PROGRESS
            updates["started_at"] = now_iso

        elif new_status == InstanceStatus.COMPLETED:
            updates["status"] = InstanceStatus.COMPLETED
            updates["completed_by"] = actor_id
            updates["completed_at"] = now_iso

        else:
            updates["status"] = new_status

        logger.info(
            "update_instance_status",
            instance_id=instance_id,
            new_status=new_status.value,
            actor_id=actor_id,
        )
        return await self.repository.update_instance(instance_id, updates)

    # ── Associations ───────────────────────────────────────────

    async def get_associations(
        self,
        master_chore_id: str | None = None,
        member_id: str | None = None,
    ) -> list[ChoreAssociation]:
        """Retrieve chore associations with optional filters.

        Args:
            master_chore_id: Filter by master chore ID.
            member_id: Filter by member ID.

        Returns:
            List of active chore associations.
        """
        return await self.repository.list_associations(
            master_chore_id=master_chore_id,
            member_id=member_id,
        )

    async def create_association(self, association: ChoreAssociation) -> ChoreAssociation:
        """Create a new association between a master chore and a member/pool.

        Args:
            association: ChoreAssociation entity to create.

        Returns:
            The created association.
        """
        logger.info(
            "create_association",
            association_id=association.id,
            master_chore_id=association.master_chore_id,
            member_id=association.member_id,
        )
        return await self.repository.create_association(association)

    async def delete_association(self, association_id: str) -> None:
        """Soft-delete an association.

        Args:
            association_id: Unique identifier for the association.
        """
        logger.info("delete_association", association_id=association_id)
        await self.repository.delete_association(association_id)
