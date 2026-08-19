"""Chores domain services.

Business logic for chore management including approval flow,
claim/assign mutual exclusivity, and completion/signoff flow.
"""

from datetime import datetime

from app.core.logging import get_logger
from app.domain.chores.models import (
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
    categories, and tags. Handles approval flow, claim/assign exclusivity,
    and completion/signoff rules.
    """

    def __init__(self, repository: ChoresRepository) -> None:
        """Initialize chores service.

        Args:
            repository: Chores data repository.
        """
        self.repository = repository

    async def get_all_data(self) -> dict:
        """Retrieve all chores data in a single call.

        Returns categories, tags, master chores, and instances
        for the frontend to render the chore board.

        Returns:
            Dict with keys: categories, tags, master_chores, instances.
        """
        categories = await self.repository.get_categories()
        tags = await self.repository.get_tags()
        master_chores = await self.repository.get_master_chores()
        instances = await self.repository.get_instances()
        return {
            "categories": categories,
            "tags": tags,
            "master_chores": master_chores,
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
        is_adult_creator: bool,
        approver_id: str | None = None,
    ) -> MasterChore:
        """Create a master chore with approval logic.

        Approval rules:
        - Adult creators: auto-approve (status=active).
        - Kid creators with a selected approver: auto-approve (status=active).
        - Kid creators without an approver: pending_approval.

        Args:
            chore: MasterChore entity to create.
            tag_ids: List of tag IDs to associate.
            is_adult_creator: Whether the creator is an adult.
            approver_id: Optional approver member ID selected by a kid creator.

        Returns:
            The created master chore with appropriate status.
        """
        if is_adult_creator:
            chore.status = MasterChoreStatus.ACTIVE
            chore.approved_by = chore.created_by
        elif approver_id:
            chore.status = MasterChoreStatus.ACTIVE
            chore.approved_by = approver_id
        else:
            chore.status = MasterChoreStatus.PENDING_APPROVAL

        logger.info(
            "create_master_chore",
            chore_id=chore.id,
            name=chore.name,
            status=chore.status.value,
            created_by=chore.created_by,
        )
        return await self.repository.create_master_chore(chore, tag_ids)

    async def approve_master_chore(self, chore_id: str, approver_id: str) -> MasterChore:
        """Approve a pending master chore.

        Args:
            chore_id: Unique identifier for the master chore.
            approver_id: Member ID of the approving adult.

        Returns:
            The approved master chore.

        Raises:
            ValueError: If the master chore is not found or not pending.
        """
        chore = await self.repository.get_master_chore_by_id(chore_id)
        if not chore:
            raise ValueError(f"Master chore '{chore_id}' not found")
        if chore.status != MasterChoreStatus.PENDING_APPROVAL:
            raise ValueError(
                f"Master chore '{chore_id}' is not pending approval "
                f"(current status: {chore.status.value})"
            )

        logger.info(
            "approve_master_chore",
            chore_id=chore_id,
            approver_id=approver_id,
        )
        return await self.repository.update_master_chore(
            chore_id,
            {
                "status": MasterChoreStatus.ACTIVE,
                "approved_by": approver_id,
            },
        )

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
        updates["updated_at"] = datetime.utcnow()
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
            assigner_id: Member ID making the assignment (parent).

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
        is_adult: bool = True,
    ) -> ChoreInstance:
        """Update the status of a chore instance.

        Completion flow:
        - Kid completes: status becomes completed_pending_signoff.
        - Adult completes: status becomes completed immediately.
        - Parent signoff: status becomes completed.

        Args:
            instance_id: Unique identifier for the instance.
            new_status: The target status.
            actor_id: Member ID performing the action.
            is_adult: Whether the actor is an adult.

        Returns:
            The updated instance.

        Raises:
            ValueError: If the instance is not found.
        """
        instance = await self.repository.get_instance_by_id(instance_id)
        if not instance:
            raise ValueError(f"Instance '{instance_id}' not found")

        now_iso = datetime.utcnow().isoformat()
        updates: dict = {"updated_at": datetime.utcnow()}

        if new_status == InstanceStatus.IN_PROGRESS:
            updates["status"] = InstanceStatus.IN_PROGRESS
            updates["started_at"] = now_iso

        elif new_status == InstanceStatus.COMPLETED:
            if is_adult:
                # Adult self-completes — no signoff needed
                updates["status"] = InstanceStatus.COMPLETED
                updates["completed_by"] = actor_id
                updates["completed_at"] = now_iso
            else:
                # This shouldn't happen directly for kids — they get pending signoff
                updates["status"] = InstanceStatus.COMPLETED
                updates["completed_by"] = actor_id
                updates["completed_at"] = now_iso

        elif new_status == InstanceStatus.COMPLETED_PENDING_SIGNOFF:
            # Kid marks complete — awaiting parent signoff
            updates["status"] = InstanceStatus.COMPLETED_PENDING_SIGNOFF
            updates["completed_by"] = actor_id
            updates["completed_at"] = now_iso

        elif new_status == InstanceStatus.COMPLETED and not is_adult:
            # Signoff by parent
            updates["status"] = InstanceStatus.COMPLETED
            updates["signoff_by"] = actor_id
            updates["signed_off_at"] = now_iso

        else:
            updates["status"] = new_status

        logger.info(
            "update_instance_status",
            instance_id=instance_id,
            new_status=new_status.value,
            actor_id=actor_id,
        )
        return await self.repository.update_instance(instance_id, updates)

    async def signoff_instance(self, instance_id: str, signoff_member_id: str) -> ChoreInstance:
        """Sign off on a kid-completed chore instance.

        Transitions from completed_pending_signoff to completed.

        Args:
            instance_id: Unique identifier for the instance.
            signoff_member_id: Parent member ID signing off.

        Returns:
            The updated instance.

        Raises:
            ValueError: If the instance is not found or not pending signoff.
        """
        instance = await self.repository.get_instance_by_id(instance_id)
        if not instance:
            raise ValueError(f"Instance '{instance_id}' not found")
        if instance.status != InstanceStatus.COMPLETED_PENDING_SIGNOFF:
            raise ValueError(
                f"Instance '{instance_id}' is not pending signoff "
                f"(current status: {instance.status.value})"
            )

        now_iso = datetime.utcnow().isoformat()
        updates: dict = {
            "status": InstanceStatus.COMPLETED,
            "signoff_by": signoff_member_id,
            "signed_off_at": now_iso,
            "updated_at": datetime.utcnow(),
        }

        logger.info(
            "signoff_instance",
            instance_id=instance_id,
            signoff_member_id=signoff_member_id,
        )
        return await self.repository.update_instance(instance_id, updates)
