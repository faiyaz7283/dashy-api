"""Chores repository implementation using SQLModel."""

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.logging import get_logger
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
from app.infrastructure.persistence.models import (
    ChoreAssociationDB,
    ChoreCategoryDB,
    ChoreInstanceDB,
    ChoreTagDB,
    ChoreTagLinkDB,
    MasterChoreDB,
)

logger = get_logger(__name__)


class ChoresRepositoryImpl:
    """SQLModel implementation of ChoresRepository.

    Maps between domain entities and database models, handling
    tag relationships via the join table.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with async session.

        Args:
            session: Async database session.
        """
        self.session = session

    # ── Categories ──────────────────────────────────────────────

    async def get_categories(self) -> list[ChoreCategory]:
        """Retrieve all chore categories from database.

        Returns:
            List of domain ChoreCategory entities.
        """
        statement = select(ChoreCategoryDB).order_by(ChoreCategoryDB.name)
        result = await self.session.execute(statement)
        db_categories = result.scalars().all()
        return [self._category_to_domain(db_cat) for db_cat in db_categories]

    async def create_category(self, name: str) -> ChoreCategory:
        """Create a new chore category.

        Args:
            name: Category display name.

        Returns:
            The newly created domain ChoreCategory.
        """
        db_category = ChoreCategoryDB(
            id=str(uuid4()),
            name=name,
        )
        self.session.add(db_category)
        await self.session.commit()
        await self.session.refresh(db_category)
        return self._category_to_domain(db_category)

    # ── Tags ────────────────────────────────────────────────────

    async def get_tags(self) -> list[ChoreTag]:
        """Retrieve all chore tags from database.

        Returns:
            List of domain ChoreTag entities.
        """
        statement = select(ChoreTagDB).order_by(ChoreTagDB.name)
        result = await self.session.execute(statement)
        db_tags = result.scalars().all()
        return [self._tag_to_domain(db_tag) for db_tag in db_tags]

    async def create_tag(self, name: str) -> ChoreTag:
        """Create a new chore tag.

        Args:
            name: Tag display name.

        Returns:
            The newly created domain ChoreTag.
        """
        db_tag = ChoreTagDB(
            id=str(uuid4()),
            name=name,
        )
        self.session.add(db_tag)
        await self.session.commit()
        await self.session.refresh(db_tag)
        return self._tag_to_domain(db_tag)

    # ── Master Chores ───────────────────────────────────────────

    async def get_master_chores(self, include_archived: bool = False) -> list[MasterChore]:
        """Retrieve master chore templates from database.

        Args:
            include_archived: Whether to include soft-deleted masters.

        Returns:
            List of domain MasterChore entities with tags populated.
        """
        statement = select(MasterChoreDB)
        if not include_archived:
            statement = statement.where(MasterChoreDB.deleted_at.is_(None))
        statement = statement.order_by(MasterChoreDB.created_at.desc())
        result = await self.session.execute(statement)
        db_masters = result.scalars().all()

        masters = []
        for db_master in db_masters:
            tags = await self._get_tags_for_master(db_master.id)
            masters.append(self._master_to_domain(db_master, tags))
        return masters

    async def get_master_chore_by_id(self, chore_id: str) -> MasterChore | None:
        """Retrieve a single master chore by ID.

        Args:
            chore_id: Unique identifier for the master chore.

        Returns:
            Domain MasterChore if found, None otherwise.
        """
        statement = select(MasterChoreDB).where(MasterChoreDB.id == chore_id)
        result = await self.session.execute(statement)
        db_master = result.scalar_one_or_none()
        if not db_master:
            return None
        tags = await self._get_tags_for_master(chore_id)
        return self._master_to_domain(db_master, tags)

    async def create_master_chore(self, chore: MasterChore, tag_ids: list[str]) -> MasterChore:
        """Create a new master chore with tag associations.

        Args:
            chore: Domain MasterChore to persist.
            tag_ids: List of tag IDs to associate.

        Returns:
            The created domain MasterChore.
        """
        db_master = self._master_to_db(chore)
        self.session.add(db_master)
        await self.session.flush()

        # Add tag associations
        for tag_id in tag_ids:
            link = ChoreTagLinkDB(master_chore_id=chore.id, tag_id=tag_id)
            self.session.add(link)

        await self.session.commit()

        # Fetch tags for the return value
        tags = await self._get_tags_for_master(chore.id)
        return self._master_to_domain(db_master, tags)

    async def update_master_chore(self, chore_id: str, updates: dict) -> MasterChore:
        """Update a master chore with the given fields.

        Args:
            chore_id: Unique identifier for the master chore.
            updates: Dictionary of field names to new values.

        Returns:
            The updated domain MasterChore.

        Raises:
            ValueError: If the master chore is not found.
        """
        statement = select(MasterChoreDB).where(MasterChoreDB.id == chore_id)
        result = await self.session.execute(statement)
        db_master = result.scalar_one_or_none()
        if not db_master:
            raise ValueError(f"Master chore '{chore_id}' not found")

        # Handle tag_ids separately if present
        tag_ids = updates.pop("tag_ids", None)

        for key, value in updates.items():
            if hasattr(db_master, key):
                # Convert enums to their string values for DB storage
                if hasattr(value, "value"):
                    value = value.value
                setattr(db_master, key, value)

        self.session.add(db_master)

        # Update tag associations if provided
        if tag_ids is not None:
            await self._replace_tag_links(chore_id, tag_ids)

        await self.session.commit()
        await self.session.refresh(db_master)

        tags = await self._get_tags_for_master(chore_id)
        return self._master_to_domain(db_master, tags)

    async def delete_master_chore(self, chore_id: str) -> None:
        """Soft-delete a master chore by setting deleted_at.

        Args:
            chore_id: Unique identifier for the master chore.
        """
        statement = select(MasterChoreDB).where(MasterChoreDB.id == chore_id)
        result = await self.session.execute(statement)
        db_master = result.scalar_one_or_none()
        if db_master:
            db_master.deleted_at = datetime.now(UTC)
            db_master.status = MasterChoreStatus.ARCHIVED.value
            self.session.add(db_master)
            await self.session.commit()

    async def bulk_update_master_status(
        self, master_ids: list[str], status: MasterChoreStatus
    ) -> int:
        """Update the status of multiple master chores at once.

        Args:
            master_ids: List of master chore IDs to update.
            status: New status to apply.

        Returns:
            Number of masters actually updated.
        """
        if not master_ids:
            return 0

        from sqlmodel import update

        now = datetime.now(UTC)
        stmt = (
            update(MasterChoreDB)
            .where(MasterChoreDB.id.in_(master_ids))
            .values(status=status.value, updated_at=now)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    # ── Instances ───────────────────────────────────────────────

    async def get_instances(self, master_chore_id: str | None = None) -> list[ChoreInstance]:
        """Retrieve chore instances from database.

        Args:
            master_chore_id: If provided, only return instances for this master.

        Returns:
            List of domain ChoreInstance entities.
        """
        statement = select(ChoreInstanceDB)
        if master_chore_id:
            statement = statement.where(ChoreInstanceDB.master_chore_id == master_chore_id)
        statement = statement.order_by(ChoreInstanceDB.created_at.desc())
        result = await self.session.execute(statement)
        db_instances = result.scalars().all()
        return [self._instance_to_domain(db_inst) for db_inst in db_instances]

    async def get_instance_by_id(self, instance_id: str) -> ChoreInstance | None:
        """Retrieve a single chore instance by ID.

        Args:
            instance_id: Unique identifier for the instance.

        Returns:
            Domain ChoreInstance if found, None otherwise.
        """
        statement = select(ChoreInstanceDB).where(ChoreInstanceDB.id == instance_id)
        result = await self.session.execute(statement)
        db_instance = result.scalar_one_or_none()
        return self._instance_to_domain(db_instance) if db_instance else None

    async def create_instance(self, instance: ChoreInstance) -> ChoreInstance:
        """Create a new chore instance.

        Args:
            instance: Domain ChoreInstance to persist.

        Returns:
            The created domain ChoreInstance.
        """
        db_instance = self._instance_to_db(instance)
        self.session.add(db_instance)
        await self.session.commit()
        await self.session.refresh(db_instance)
        return self._instance_to_domain(db_instance)

    async def update_instance(self, instance_id: str, updates: dict) -> ChoreInstance:
        """Update a chore instance with the given fields.

        Args:
            instance_id: Unique identifier for the instance.
            updates: Dictionary of field names to new values.

        Returns:
            The updated domain ChoreInstance.

        Raises:
            ValueError: If the instance is not found.
        """
        statement = select(ChoreInstanceDB).where(ChoreInstanceDB.id == instance_id)
        result = await self.session.execute(statement)
        db_instance = result.scalar_one_or_none()
        if not db_instance:
            raise ValueError(f"Instance '{instance_id}' not found")

        for key, value in updates.items():
            if hasattr(db_instance, key):
                # Convert enums to their string values for DB storage
                if hasattr(value, "value"):
                    value = value.value
                # Convert datetime to ISO string for string-typed columns
                if key in (
                    "started_at",
                    "completed_at",
                    "period_start",
                    "period_end",
                ) and isinstance(value, datetime):
                    value = value.isoformat()
                setattr(db_instance, key, value)

        self.session.add(db_instance)
        await self.session.commit()
        await self.session.refresh(db_instance)
        return self._instance_to_domain(db_instance)

    async def delete_instance(self, instance_id: str) -> None:
        """Delete a chore instance permanently.

        Args:
            instance_id: Unique identifier for the instance.
        """
        statement = select(ChoreInstanceDB).where(ChoreInstanceDB.id == instance_id)
        result = await self.session.execute(statement)
        db_instance = result.scalar_one_or_none()
        if db_instance:
            await self.session.delete(db_instance)
            await self.session.commit()

    # ── Associations ───────────────────────────────────────────

    async def get_association(self, association_id: str) -> ChoreAssociation | None:
        """Retrieve a single chore association by ID.

        Args:
            association_id: Unique identifier for the association.

        Returns:
            Domain ChoreAssociation if found, None otherwise.
        """
        statement = select(ChoreAssociationDB).where(ChoreAssociationDB.id == association_id)
        result = await self.session.execute(statement)
        db_association = result.scalar_one_or_none()
        return self._association_to_domain(db_association) if db_association else None

    async def create_association(self, association: ChoreAssociation) -> ChoreAssociation:
        """Create a new chore association.

        Args:
            association: Domain ChoreAssociation to persist.

        Returns:
            The created domain ChoreAssociation.
        """
        db_association = self._association_to_db(association)
        self.session.add(db_association)
        await self.session.commit()
        await self.session.refresh(db_association)
        return self._association_to_domain(db_association)

    async def delete_association(self, association_id: str) -> None:
        """Soft-delete a chore association by setting removed_at.

        Args:
            association_id: Unique identifier for the association.
        """
        statement = select(ChoreAssociationDB).where(ChoreAssociationDB.id == association_id)
        result = await self.session.execute(statement)
        db_association = result.scalar_one_or_none()
        if db_association:
            db_association.removed_at = datetime.now(UTC)
            self.session.add(db_association)
            await self.session.commit()

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
            List of domain ChoreAssociation entities.
        """
        statement = select(ChoreAssociationDB)
        if not include_removed:
            statement = statement.where(ChoreAssociationDB.removed_at.is_(None))
        if master_chore_id:
            statement = statement.where(ChoreAssociationDB.master_chore_id == master_chore_id)
        if member_id:
            statement = statement.where(ChoreAssociationDB.member_id == member_id)
        statement = statement.order_by(ChoreAssociationDB.created_at.desc())
        result = await self.session.execute(statement)
        db_associations = result.scalars().all()
        return [self._association_to_domain(db_assoc) for db_assoc in db_associations]

    async def get_associations_by_master(self, master_chore_id: str) -> list[ChoreAssociation]:
        """Retrieve all active associations for a master chore.

        Args:
            master_chore_id: Unique identifier for the master chore.

        Returns:
            List of active domain ChoreAssociation entities.
        """
        return await self.list_associations(master_chore_id=master_chore_id)

    async def get_associations_by_member(self, member_id: str) -> list[ChoreAssociation]:
        """Retrieve all active associations for a member.

        Args:
            member_id: Unique identifier for the member.

        Returns:
            List of active domain ChoreAssociation entities.
        """
        return await self.list_associations(member_id=member_id)

    async def get_instances_by_association(
        self, association_id: str, active_only: bool = True
    ) -> list[ChoreInstance]:
        """Retrieve instances linked to a specific association.

        Args:
            association_id: FK to the association.
            active_only: If True, only return non-completed/non-archived instances.

        Returns:
            List of matching domain ChoreInstance entities.
        """
        statement = select(ChoreInstanceDB).where(
            ChoreInstanceDB.association_id == association_id
        )
        if active_only:
            statement = statement.where(
                ChoreInstanceDB.status.in_([
                    InstanceStatus.ACTIVE.value,
                    InstanceStatus.IN_PROGRESS.value,
                ])
            )
        statement = statement.order_by(ChoreInstanceDB.created_at.desc())
        result = await self.session.execute(statement)
        db_instances = result.scalars().all()
        return [self._instance_to_domain(db_inst) for db_inst in db_instances]

    async def archive_instances_by_association(self, association_id: str) -> int:
        """Archive all active instances for an association.

        Sets status to ARCHIVED for instances that are ACTIVE or IN_PROGRESS.

        Args:
            association_id: FK to the association.

        Returns:
            Number of instances archived.
        """
        statement = select(ChoreInstanceDB).where(
            ChoreInstanceDB.association_id == association_id,
            ChoreInstanceDB.status.in_([
                InstanceStatus.ACTIVE.value,
                InstanceStatus.IN_PROGRESS.value,
            ]),
        )
        result = await self.session.execute(statement)
        db_instances = result.scalars().all()

        archived_count = 0
        for db_instance in db_instances:
            db_instance.status = InstanceStatus.ARCHIVED.value
            db_instance.updated_at = datetime.now(UTC)
            self.session.add(db_instance)
            archived_count += 1

        await self.session.commit()
        return archived_count

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
            Domain ChoreInstance if found, None otherwise.
        """
        statement = (
            select(ChoreInstanceDB)
            .where(
                ChoreInstanceDB.association_id == association_id,
                ChoreInstanceDB.period_start == period_start,
                ChoreInstanceDB.period_end == period_end,
                ChoreInstanceDB.status != InstanceStatus.ARCHIVED.value,
            )
        )
        result = await self.session.execute(statement)
        db_instance = result.scalar_one_or_none()
        return self._instance_to_domain(db_instance) if db_instance else None

    async def get_expired_instances(self, today: date) -> list[ChoreInstance]:
        """Retrieve instances past their period_end with non-completed status.

        Args:
            today: Current date to compare against period_end.

        Returns:
            List of domain ChoreInstance entities that are expired.
        """
        statement = (
            select(ChoreInstanceDB)
            .where(
                ChoreInstanceDB.period_end < today,
                ChoreInstanceDB.status.in_([
                    InstanceStatus.ACTIVE.value,
                    InstanceStatus.IN_PROGRESS.value,
                    InstanceStatus.OVERDUE.value,
                ]),
            )
        )
        result = await self.session.execute(statement)
        db_instances = result.scalars().all()
        return [self._instance_to_domain(db_inst) for db_inst in db_instances]

    async def get_overdue_instances(self, today: date, current_time: str) -> list[ChoreInstance]:
        """Retrieve instances past their due time but within their period.

        Overdue detection requires joining with master_chores to check due_time.
        An instance is overdue if:
        - It's within its period (period_end >= today)
        - Its master's due_time has passed
        - Status is ACTIVE or IN_PROGRESS

        Args:
            today: Current date.
            current_time: Current time in HH:MM format.

        Returns:
            List of domain ChoreInstance entities that are overdue.
        """
        statement = (
            select(ChoreInstanceDB)
            .join(MasterChoreDB, ChoreInstanceDB.master_chore_id == MasterChoreDB.id)
            .where(
                ChoreInstanceDB.period_end >= today,
                ChoreInstanceDB.status.in_([
                    InstanceStatus.ACTIVE.value,
                    InstanceStatus.IN_PROGRESS.value,
                ]),
                MasterChoreDB.due_time.is_not(None),
                MasterChoreDB.due_time < current_time,
            )
        )
        result = await self.session.execute(statement)
        db_instances = result.scalars().all()
        return [self._instance_to_domain(db_inst) for db_inst in db_instances]

    # ── Private helpers ─────────────────────────────────────────

    async def _get_tags_for_master(self, master_chore_id: str) -> list[ChoreTag]:
        """Fetch tags associated with a master chore via the join table.

        Args:
            master_chore_id: The master chore's ID.

        Returns:
            List of domain ChoreTag entities.
        """
        statement = (
            select(ChoreTagDB)
            .join(ChoreTagLinkDB, ChoreTagDB.id == ChoreTagLinkDB.tag_id)
            .where(ChoreTagLinkDB.master_chore_id == master_chore_id)
        )
        result = await self.session.execute(statement)
        db_tags = result.scalars().all()
        return [self._tag_to_domain(db_tag) for db_tag in db_tags]

    async def _replace_tag_links(self, master_chore_id: str, tag_ids: list[str]) -> None:
        """Replace all tag associations for a master chore.

        Args:
            master_chore_id: The master chore's ID.
            tag_ids: New list of tag IDs to associate.
        """
        # Delete existing links
        delete_stmt = select(ChoreTagLinkDB).where(
            ChoreTagLinkDB.master_chore_id == master_chore_id
        )
        result = await self.session.execute(delete_stmt)
        for link in result.scalars().all():
            await self.session.delete(link)
        await self.session.flush()

        # Add new links
        for tag_id in tag_ids:
            link = ChoreTagLinkDB(master_chore_id=master_chore_id, tag_id=tag_id)
            self.session.add(link)

    @staticmethod
    def _category_to_domain(db_cat: ChoreCategoryDB) -> ChoreCategory:
        """Convert database model to domain model.

        Args:
            db_cat: Database ChoreCategoryDB row.

        Returns:
            Domain ChoreCategory entity.
        """
        return ChoreCategory(
            id=db_cat.id,
            name=db_cat.name,
            created_at=db_cat.created_at,
        )

    @staticmethod
    def _tag_to_domain(db_tag: ChoreTagDB) -> ChoreTag:
        """Convert database model to domain model.

        Args:
            db_tag: Database ChoreTagDB row.

        Returns:
            Domain ChoreTag entity.
        """
        return ChoreTag(
            id=db_tag.id,
            name=db_tag.name,
            created_at=db_tag.created_at,
        )

    @staticmethod
    def _master_to_domain(db_master: MasterChoreDB, tags: list[ChoreTag]) -> MasterChore:
        """Convert database model to domain model.

        Args:
            db_master: Database MasterChoreDB row.
            tags: Associated ChoreTag entities.

        Returns:
            Domain MasterChore entity.
        """
        return MasterChore(
            id=db_master.id,
            name=db_master.name,
            category_id=db_master.category_id,
            tags=tags,
            difficulty=db_master.difficulty,
            recurrence_rule=db_master.recurrence_rule,
            estimated_minutes=db_master.estimated_minutes,
            due_time=db_master.due_time,
            due_date=db_master.due_date,
            expiration_behavior=ExpirationBehavior(db_master.expiration_behavior),
            end_date=db_master.end_date,
            max_occurrences=db_master.max_occurrences,
            occurrence_count=db_master.occurrence_count,
            conditions=db_master.conditions,
            is_collaborative=db_master.is_collaborative,
            created_by=db_master.created_by,
            status=MasterChoreStatus(db_master.status),
            created_at=db_master.created_at,
            updated_at=db_master.updated_at,
            deleted_at=db_master.deleted_at,
        )

    @staticmethod
    def _master_to_db(chore: MasterChore) -> MasterChoreDB:
        """Convert domain model to database model.

        Args:
            chore: Domain MasterChore entity.

        Returns:
            Database MasterChoreDB row ready for insertion.
        """
        return MasterChoreDB(
            id=chore.id,
            name=chore.name,
            category_id=chore.category_id,
            difficulty=chore.difficulty,
            recurrence_rule=chore.recurrence_rule,
            estimated_minutes=chore.estimated_minutes,
            due_time=chore.due_time,
            due_date=chore.due_date,
            expiration_behavior=chore.expiration_behavior.value,
            end_date=chore.end_date,
            max_occurrences=chore.max_occurrences,
            occurrence_count=chore.occurrence_count,
            conditions=chore.conditions,
            is_collaborative=chore.is_collaborative,
            created_by=chore.created_by,
            status=chore.status.value,
            created_at=chore.created_at,
            updated_at=chore.updated_at,
            deleted_at=chore.deleted_at,
        )

    @staticmethod
    def _instance_to_domain(db_instance: ChoreInstanceDB) -> ChoreInstance:
        """Convert database model to domain model.

        Args:
            db_instance: Database ChoreInstanceDB row.

        Returns:
            Domain ChoreInstance entity.
        """
        return ChoreInstance(
            id=db_instance.id,
            master_chore_id=db_instance.master_chore_id,
            association_id=db_instance.association_id,
            period_start=db_instance.period_start,
            period_end=db_instance.period_end,
            status=InstanceStatus(db_instance.status),
            claimed_by=db_instance.claimed_by,
            assigned_to=db_instance.assigned_to,
            assigned_by=db_instance.assigned_by,
            completed_by=db_instance.completed_by,
            started_at=db_instance.started_at,
            completed_at=db_instance.completed_at,
            created_at=db_instance.created_at,
            updated_at=db_instance.updated_at,
        )

    @staticmethod
    def _instance_to_db(instance: ChoreInstance) -> ChoreInstanceDB:
        """Convert domain model to database model.

        Args:
            instance: Domain ChoreInstance entity.

        Returns:
            Database ChoreInstanceDB row ready for insertion.
        """
        return ChoreInstanceDB(
            id=instance.id,
            master_chore_id=instance.master_chore_id,
            association_id=instance.association_id,
            period_start=instance.period_start,
            period_end=instance.period_end,
            status=instance.status.value,
            claimed_by=instance.claimed_by,
            assigned_to=instance.assigned_to,
            assigned_by=instance.assigned_by,
            completed_by=instance.completed_by,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
        )

    @staticmethod
    def _association_to_domain(db_association: ChoreAssociationDB) -> ChoreAssociation:
        """Convert database model to domain model.

        Args:
            db_association: Database ChoreAssociationDB row.

        Returns:
            Domain ChoreAssociation entity.
        """
        return ChoreAssociation(
            id=db_association.id,
            master_chore_id=db_association.master_chore_id,
            member_id=db_association.member_id,
            is_open_pool=db_association.is_open_pool,
            created_by=db_association.created_by,
            created_at=db_association.created_at,
            updated_at=db_association.updated_at,
            removed_at=db_association.removed_at,
        )

    @staticmethod
    def _association_to_db(association: ChoreAssociation) -> ChoreAssociationDB:
        """Convert domain model to database model.

        Args:
            association: Domain ChoreAssociation entity.

        Returns:
            Database ChoreAssociationDB row ready for insertion.
        """
        return ChoreAssociationDB(
            id=association.id,
            master_chore_id=association.master_chore_id,
            member_id=association.member_id,
            is_open_pool=association.is_open_pool,
            created_by=association.created_by,
            created_at=association.created_at,
            updated_at=association.updated_at,
            removed_at=association.removed_at,
        )
