"""Chores domain services.

Business logic for chore management including claim/assign
mutual exclusivity, instance status transitions, association
collaborative enforcement, and instance generation.
"""

from datetime import UTC, datetime
from uuid import UUID

from uuid6 import uuid7

from app.core.logging import get_logger
from app.domain.chores.condition_evaluator import ConditionEvaluator
from app.domain.chores.models import (
    ChoreAssociation,
    ChoreCategory,
    ChoreInstance,
    ChoreTag,
    ExpirationBehavior,
    InstanceStatus,
    MasterChore,
    MasterChoreStatus,
)
from app.domain.chores.ports import ChoresRepository
from app.domain.chores.schemas import ConditionsConfig, RecurrenceRule
from app.domain.chores.utils.periods import calculate_period, get_next_occurrence

logger = get_logger(__name__)


class AssociationConflictError(Exception):
    """Raised when an association violates collaborative constraints.

    Attributes:
        message: Human-readable description of the conflict.
    """

    def __init__(self, message: str) -> None:
        """Initialize with a conflict description.

        Args:
            message: Human-readable description of the conflict.
        """
        self.message = message
        super().__init__(message)


class ChoresService:
    """Service for chore operations.

    Encapsulates business logic for managing master chores, instances,
    associations, categories, and tags. Handles claim/assign exclusivity
    and instance status transitions.
    """

    def __init__(
        self,
        repository: ChoresRepository,
        condition_evaluator: ConditionEvaluator | None = None,
    ) -> None:
        """Initialize chores service.

        Args:
            repository: Chores data repository.
            condition_evaluator: Optional evaluator for conditional chores.
        """
        self.repository = repository
        self.condition_evaluator = condition_evaluator

    async def get_all_data(self) -> dict:
        """Retrieve all chores data in a single call.

        Runs the safety net (ensure_current_instances) before fetching
        data, so the board always shows up-to-date instances.

        Returns categories, tags, master chores, associations,
        and instances for the frontend to render the chore board.

        Returns:
            Dict with keys: categories, tags, master_chores, associations, instances.
        """
        await self.ensure_current_instances()

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
        tag_ids: list[UUID],
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
        self, chore_id: UUID, updates: dict, tag_ids: list[UUID] | None = None
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

    async def delete_master_chore(self, chore_id: UUID) -> None:
        """Soft-delete (archive) a master chore.

        Sets the deleted_at timestamp to mark the chore as archived.

        Args:
            chore_id: Unique identifier for the master chore.
        """
        logger.info("delete_master_chore", chore_id=chore_id)
        await self.repository.delete_master_chore(chore_id)

    async def get_instances(self, master_chore_id: UUID | None = None) -> list[ChoreInstance]:
        """Retrieve chore instances.

        Args:
            master_chore_id: Optional filter by master chore.

        Returns:
            List of chore instances.
        """
        return await self.repository.get_instances(master_chore_id=master_chore_id)

    async def claim_instance(self, instance_id: UUID, member_id: str) -> ChoreInstance:
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
        instance_id: UUID,
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
        instance_id: UUID,
        new_status: InstanceStatus,
        actor_id: str,
    ) -> ChoreInstance:
        """Update the status of a chore instance.

        Any member can complete any instance — no approval or signoff required.
        When an instance is completed, triggers generation of the next instance
        for the same association.

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
        updated = await self.repository.update_instance(instance_id, updates)

        if new_status == InstanceStatus.COMPLETED and instance.association_id:
            await self.generate_instance_for_association(instance.association_id)

        return updated

    # ── Associations ───────────────────────────────────────────

    async def get_associations(
        self,
        master_chore_id: UUID | None = None,
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

        Validates collaborative constraints before creating, then generates
        the first instance for the new association.

        Args:
            association: ChoreAssociation entity to create.

        Returns:
            The created association.

        Raises:
            ValueError: If the master chore is not found or not active.
            AssociationConflictError: If collaborative constraints are violated.
        """
        master = await self.repository.get_master_chore_by_id(association.master_chore_id)
        if not master:
            raise ValueError(f"Master chore '{association.master_chore_id}' not found")
        if master.status != MasterChoreStatus.ACTIVE:
            raise ValueError(
                f"Master chore '{association.master_chore_id}' is not active "
                f"(status: {master.status.value})"
            )

        existing = await self.repository.get_associations_by_master(association.master_chore_id)
        self._validate_association(master, association, existing)

        logger.info(
            "create_association",
            association_id=association.id,
            master_chore_id=association.master_chore_id,
            member_id=association.member_id,
            is_open_pool=association.is_open_pool,
        )
        created = await self.repository.create_association(association)

        await self.generate_instance_for_association(created.id, master)

        return created

    async def delete_association(self, association_id: UUID) -> int:
        """Soft-delete an association and archive its active instances.

        Archives all ACTIVE/IN_PROGRESS instances linked to this association
        before soft-deleting the association itself.

        Args:
            association_id: Unique identifier for the association.

        Returns:
            Number of instances archived.

        Raises:
            ValueError: If the association is not found.
        """
        association = await self.repository.get_association(association_id)
        if not association:
            raise ValueError(f"Association '{association_id}' not found")

        archived_count = await self.repository.archive_instances_by_association(association_id)

        logger.info(
            "delete_association",
            association_id=association_id,
            archived_instances=archived_count,
        )
        await self.repository.delete_association(association_id)
        return archived_count

    @staticmethod
    def _validate_association(
        master: MasterChore,
        new_association: ChoreAssociation,
        existing_associations: list[ChoreAssociation],
    ) -> None:
        """Enforce collaborative rules for association creation.

        Rules:
        - Open pool: only one per master (regardless of collaborative flag)
        - Non-collaborative: only one non-open-pool association allowed
        - Collaborative: multiple non-open-pool associations allowed
        - Duplicate member: same member can't have two active associations
          for the same master

        Args:
            master: The master chore being associated.
            new_association: The proposed association to validate.
            existing_associations: Currently active associations for this master.

        Raises:
            AssociationConflictError: If any constraint is violated.
        """
        if new_association.is_open_pool:
            open_pool_exists = [a for a in existing_associations if a.is_open_pool]
            if open_pool_exists:
                raise AssociationConflictError(
                    f"Master '{master.id}' already has an open pool association"
                )
            return

        if not master.is_collaborative:
            member_associations = [
                a for a in existing_associations
                if not a.is_open_pool and a.member_id == new_association.member_id
            ]
            if member_associations:
                raise AssociationConflictError(
                    f"Member '{new_association.member_id}' already has an active "
                    f"association for non-collaborative master '{master.id}'"
                )

            non_open_pool = [a for a in existing_associations if not a.is_open_pool]
            if non_open_pool:
                raise AssociationConflictError(
                    f"Non-collaborative master '{master.id}' already has an active "
                    f"member association"
                )
        else:
            duplicate = [
                a for a in existing_associations
                if not a.is_open_pool and a.member_id == new_association.member_id
            ]
            if duplicate:
                raise AssociationConflictError(
                    f"Member '{new_association.member_id}' already has an active "
                    f"association for collaborative master '{master.id}'"
                )

    # ── Instance Generation ────────────────────────────────────

    async def generate_instance_for_association(
        self,
        association_id: UUID,
        master: MasterChore | None = None,
    ) -> ChoreInstance | None:
        """Generate the next instance for an association.

        Called by: association creation, instance completion, safety net.
        Checks limits (end_date, max_occurrences), calculates the next period,
        and creates an instance if one doesn't already exist for that period.

        Args:
            association_id: FK to the association to generate for.
            master: Optional pre-fetched master chore (avoids extra query).

        Returns:
            The newly created ChoreInstance, or None if limits reached
            or an instance already exists for the target period.
        """
        if master is None:
            association = await self.repository.get_association(association_id)
            if not association:
                return None
            master = await self.repository.get_master_chore_by_id(association.master_chore_id)
            if not master:
                return None

        if master.status != MasterChoreStatus.ACTIVE:
            return None

        if master.recurrence_rule is None:
            return None

        if master.conditions and self.condition_evaluator:
            conditions_config = ConditionsConfig(**master.conditions)
            conditions_met = await self.condition_evaluator.evaluate(conditions_config)
            if not conditions_met:
                logger.info(
                    "generate_instance_skipped_conditions",
                    association_id=association_id,
                    master_id=master.id,
                )
                return None

        rule = RecurrenceRule(**master.recurrence_rule)
        today = datetime.now(UTC).date()
        now_time = datetime.now(UTC).strftime("%H:%M")

        next_date = get_next_occurrence(rule, today, now_time)

        if master.end_date and next_date > master.end_date:
            logger.info(
                "generate_instance_skipped_end_date",
                association_id=association_id,
                next_date=next_date.isoformat(),
                end_date=master.end_date.isoformat(),
            )
            return None

        if master.max_occurrences and master.occurrence_count >= master.max_occurrences:
            logger.info(
                "generate_instance_skipped_max_occurrences",
                association_id=association_id,
                occurrence_count=master.occurrence_count,
                max_occurrences=master.max_occurrences,
            )
            return None

        period_start, period_end = calculate_period(rule, next_date)

        if period_start is None or period_end is None:
            return None

        existing = await self.repository.get_instance_for_period(
            association_id, period_start, period_end
        )
        if existing:
            return existing

        association = await self.repository.get_association(association_id)
        if not association:
            return None

        instance = ChoreInstance(
            id=uuid7(),
            master_chore_id=master.id,
            association_id=association_id,
            period_start=period_start,
            period_end=period_end,
            status=InstanceStatus.ACTIVE,
            claimed_by=association.member_id if not association.is_open_pool else None,
            assigned_to=association.member_id if not association.is_open_pool else None,
        )

        created = await self.repository.create_instance(instance)

        await self.repository.update_master_chore(
            master.id,
            {"occurrence_count": master.occurrence_count + 1},
        )

        logger.info(
            "generate_instance",
            instance_id=created.id,
            association_id=association_id,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        )

        return created

    async def ensure_current_instances(self) -> list[ChoreInstance]:
        """Safety net: ensure every active association has a current instance.

        Called on board load to catch any missed generations. For each active
        association with an active master, checks if an instance exists for
        the current period and generates one if missing.

        Also processes expired instances and marks overdue instances.

        Returns:
            List of newly created instances (empty if all were up to date).
        """
        await self.process_expired_instances()
        await self.mark_overdue_instances()

        generated: list[ChoreInstance] = []

        associations = await self.repository.list_associations()
        masters_cache: dict[UUID, MasterChore | None] = {}

        for association in associations:
            master_id = association.master_chore_id
            if master_id not in masters_cache:
                masters_cache[master_id] = await self.repository.get_master_chore_by_id(master_id)

            master = masters_cache[master_id]
            if not master or master.status != MasterChoreStatus.ACTIVE:
                continue

            if master.recurrence_rule is None:
                continue

            result = await self.generate_instance_for_association(association.id, master)
            if result and result.status == InstanceStatus.ACTIVE:
                generated.append(result)

        if generated:
            logger.info("ensure_current_instances", count=len(generated))

        return generated

    async def process_expired_instances(self) -> list[ChoreInstance]:
        """Process instances past their period_end with non-completed status.

        Applies the master's expiration_behavior to each expired instance:
        - DISAPPEAR: Delete the instance
        - CARRY_OVER: Mark as MISSED, generate new instance for next period
        - STAY_VISIBLE: Mark as MISSED, leave instance visible
        - CONVERT_TO_OPEN: Clear assignment, move to open pool

        Returns:
            List of processed ChoreInstance entities.
        """
        today = datetime.now(UTC).date()
        expired = await self.repository.get_expired_instances(today)

        if not expired:
            return []

        processed: list[ChoreInstance] = []
        masters_cache: dict[UUID, MasterChore | None] = {}

        for instance in expired:
            master_id = instance.master_chore_id
            if master_id not in masters_cache:
                masters_cache[master_id] = await self.repository.get_master_chore_by_id(master_id)

            master = masters_cache[master_id]
            if not master:
                continue

            behavior = master.expiration_behavior

            if behavior == ExpirationBehavior.DISAPPEAR:
                await self.repository.delete_instance(instance.id)
                logger.info(
                    "process_expired_disappear",
                    instance_id=instance.id,
                    master_id=master_id,
                )

            elif behavior == ExpirationBehavior.CARRY_OVER:
                await self.repository.update_instance(
                    instance.id,
                    {
                        "status": InstanceStatus.MISSED,
                        "updated_at": datetime.now(UTC),
                    },
                )
                if instance.association_id:
                    await self.generate_instance_for_association(instance.association_id, master)
                logger.info(
                    "process_expired_carry_over",
                    instance_id=instance.id,
                    master_id=master_id,
                )

            elif behavior == ExpirationBehavior.STAY_VISIBLE:
                await self.repository.update_instance(
                    instance.id,
                    {
                        "status": InstanceStatus.MISSED,
                        "updated_at": datetime.now(UTC),
                    },
                )
                logger.info(
                    "process_expired_stay_visible",
                    instance_id=instance.id,
                    master_id=master_id,
                )

            elif behavior == ExpirationBehavior.CONVERT_TO_OPEN:
                await self.repository.update_instance(
                    instance.id,
                    {
                        "claimed_by": None,
                        "assigned_to": None,
                        "assigned_by": None,
                        "updated_at": datetime.now(UTC),
                    },
                )
                logger.info(
                    "process_expired_convert_to_open",
                    instance_id=instance.id,
                    master_id=master_id,
                )

            processed.append(instance)

        if processed:
            logger.info("process_expired_instances", count=len(processed))

        return processed

    async def mark_overdue_instances(self) -> list[ChoreInstance]:
        """Mark instances as OVERDUE if their due_time has passed.

        An instance is overdue if:
        - It's within its period (period_end >= today)
        - Its master's due_time has passed
        - Status is ACTIVE or IN_PROGRESS

        Returns:
            List of newly marked overdue ChoreInstance entities.
        """
        now = datetime.now(UTC)
        today = now.date()
        current_time = now.strftime("%H:%M")

        overdue = await self.repository.get_overdue_instances(today, current_time)

        if not overdue:
            return []

        marked: list[ChoreInstance] = []

        for instance in overdue:
            await self.repository.update_instance(
                instance.id,
                {
                    "status": InstanceStatus.OVERDUE,
                    "updated_at": datetime.now(UTC),
                },
            )
            marked.append(instance)
            logger.info(
                "mark_overdue",
                instance_id=instance.id,
                master_id=instance.master_chore_id,
            )

        if marked:
            logger.info("mark_overdue_instances", count=len(marked))

        return marked

    # ── Bulk Operations ───────────────────────────────────────

    async def bulk_update_master_status(
        self,
        master_ids: list[UUID],
        status: MasterChoreStatus,
    ) -> int:
        """Update the status of multiple master chores at once.

        Used for bulk pause/resume operations. Updates status and
        updated_at timestamp for all specified masters.

        Args:
            master_ids: List of master chore IDs to update.
            status: New status to apply.

        Returns:
            Number of masters actually updated.
        """
        if not master_ids:
            return 0

        updated_count = await self.repository.bulk_update_master_status(
            master_ids, status
        )

        logger.info(
            "bulk_update_master_status",
            count=updated_count,
            status=status.value,
            master_ids=master_ids,
        )

        return updated_count
