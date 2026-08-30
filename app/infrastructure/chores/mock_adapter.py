"""Mock chores adapter implementing ChoresRepository protocol.

Returns realistic mock data for development and testing, matching
the Haider family members (faiyaz, trisha, arya, raya).
"""

import copy
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from uuid6 import uuid7

from app.domain.chores.models import (
    ChoreAssociation,
    ChoreCategory,
    ChoreInstance,
    ChoreTag,
    InstanceStatus,
    MasterChore,
    MasterChoreStatus,
)

# Generate UUIDs for mock data
_CAT_KITCHEN = uuid7()
_CAT_BATHROOM = uuid7()
_CAT_OUTDOOR = uuid7()
_CAT_LAUNDRY = uuid7()
_CAT_GENERAL = uuid7()

_TAG_QUICK = uuid7()
_TAG_PHYSICAL = uuid7()
_TAG_MESSY = uuid7()
_TAG_FOCUS = uuid7()
_TAG_TEAMWORK = uuid7()

# Family member UUIDs (mock)
_MEMBER_FAIYAZ = uuid7()
_MEMBER_TRISHA = uuid7()
_MEMBER_ARYA = uuid7()
_MEMBER_RAYA = uuid7()

_MASTER_001 = uuid7()
_MASTER_002 = uuid7()
_MASTER_003 = uuid7()
_MASTER_004 = uuid7()
_MASTER_005 = uuid7()
_MASTER_006 = uuid7()
_MASTER_007 = uuid7()

_ASSOC_001 = uuid7()
_ASSOC_002 = uuid7()
_ASSOC_003 = uuid7()
_ASSOC_004 = uuid7()
_ASSOC_005 = uuid7()
_ASSOC_006 = uuid7()

_INST_001 = uuid7()
_INST_002 = uuid7()
_INST_003 = uuid7()
_INST_004 = uuid7()
_INST_005 = uuid7()
_INST_006 = uuid7()
_INST_007 = uuid7()

# Preset categories
_PRESET_CATEGORIES = [
    ChoreCategory(id=_CAT_KITCHEN, name="Kitchen"),
    ChoreCategory(id=_CAT_BATHROOM, name="Bathroom"),
    ChoreCategory(id=_CAT_OUTDOOR, name="Outdoor"),
    ChoreCategory(id=_CAT_LAUNDRY, name="Laundry"),
    ChoreCategory(id=_CAT_GENERAL, name="General"),
]

# Sample tags
_SAMPLE_TAGS = [
    ChoreTag(id=_TAG_QUICK, name="Quick"),
    ChoreTag(id=_TAG_PHYSICAL, name="Physical"),
    ChoreTag(id=_TAG_MESSY, name="Messy"),
    ChoreTag(id=_TAG_FOCUS, name="Focus"),
    ChoreTag(id=_TAG_TEAMWORK, name="Teamwork"),
]

_NOW = datetime.now(UTC)
_TODAY = _NOW.date()


# Master chores
_MASTER_1 = MasterChore(
    id=_MASTER_001,
    name="Wipe Kitchen Counter",
    category_id=_CAT_KITCHEN,
    created_by=_MEMBER_FAIYAZ,
    tags=[_SAMPLE_TAGS[0]],
    difficulty=1,
    frequency="daily",
    frequency_interval=1,
    due_time="18:00",
    estimated_minutes=5,
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=14),
    updated_at=_NOW - timedelta(days=2),
)

_MASTER_2 = MasterChore(
    id=_MASTER_002,
    name="Clean Bathroom Sink",
    category_id=_CAT_BATHROOM,
    created_by=_MEMBER_TRISHA,
    tags=[_SAMPLE_TAGS[0], _SAMPLE_TAGS[2]],
    difficulty=2,
    frequency="daily",
    frequency_interval=1,
    due_time="20:00",
    estimated_minutes=10,
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=14),
    updated_at=_NOW - timedelta(days=1),
)

_MASTER_3 = MasterChore(
    id=_MASTER_003,
    name="Rake Leaves in Yard",
    category_id=_CAT_OUTDOOR,
    created_by=_MEMBER_FAIYAZ,
    tags=[_SAMPLE_TAGS[1]],
    difficulty=3,
    frequency="weekly",
    frequency_interval=1,
    day_of_week=[0],  # Monday
    due_time="10:00",
    estimated_minutes=30,
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=10),
    updated_at=_NOW - timedelta(days=3),
)

_MASTER_4 = MasterChore(
    id=_MASTER_004,
    name="Fold Laundry",
    category_id=_CAT_LAUNDRY,
    created_by=_MEMBER_TRISHA,
    tags=[_SAMPLE_TAGS[0], _SAMPLE_TAGS[3]],
    difficulty=2,
    frequency="weekly",
    frequency_interval=1,
    day_of_week=[6],  # Sunday
    due_time="14:00",
    estimated_minutes=20,
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=7),
    updated_at=_NOW - timedelta(days=1),
)

_MASTER_5 = MasterChore(
    id=_MASTER_005,
    name="Organize Bookshelf",
    category_id=_CAT_GENERAL,
    created_by=_MEMBER_ARYA,
    tags=[_SAMPLE_TAGS[3]],
    difficulty=2,
    frequency="monthly",
    frequency_interval=1,
    day_of_month=15,
    due_time="11:00",
    estimated_minutes=45,
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=1),
    updated_at=_NOW - timedelta(days=1),
)

_MASTER_6 = MasterChore(
    id=_MASTER_006,
    name="Take Out Trash",
    category_id=_CAT_KITCHEN,
    created_by=_MEMBER_FAIYAZ,
    tags=[_SAMPLE_TAGS[0]],
    difficulty=1,
    frequency="daily",
    frequency_interval=1,
    due_time="19:00",
    estimated_minutes=5,
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=14),
    updated_at=_NOW - timedelta(days=7),
)

_MASTER_7_CONDITIONAL = MasterChore(
    id=_MASTER_007,
    name="Shovel Snow",
    category_id=_CAT_OUTDOOR,
    created_by=_MEMBER_FAIYAZ,
    tags=[_SAMPLE_TAGS[1]],
    difficulty=4,
    frequency="daily",
    frequency_interval=1,
    due_time="08:00",
    estimated_minutes=45,
    conditions={
        "logic": "and",
        "conditions": [
            {"type": "weather", "metric": "snowfall", "operator": "gt", "value": 0}
        ],
    },
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=5),
    updated_at=_NOW - timedelta(days=5),
)

_ALL_MASTERS = [
    _MASTER_1,
    _MASTER_2,
    _MASTER_3,
    _MASTER_4,
    _MASTER_5,
    _MASTER_6,
    _MASTER_7_CONDITIONAL,
]

# Mock associations
_ASSOCIATIONS = [
    ChoreAssociation(
        id=_ASSOC_001,
        master_chore_id=_MASTER_001,
        member_id=_MEMBER_ARYA,
        created_by=_MEMBER_FAIYAZ,
        created_at=_NOW - timedelta(days=10),
        updated_at=_NOW - timedelta(days=10),
    ),
    ChoreAssociation(
        id=_ASSOC_002,
        master_chore_id=_MASTER_003,
        member_id=None,  # Open pool
        created_by=_MEMBER_FAIYAZ,
        created_at=_NOW - timedelta(days=8),
        updated_at=_NOW - timedelta(days=8),
    ),
    ChoreAssociation(
        id=_ASSOC_003,
        master_chore_id=_MASTER_002,
        member_id=_MEMBER_ARYA,
        created_by=_MEMBER_TRISHA,
        created_at=_NOW - timedelta(days=7),
        updated_at=_NOW - timedelta(days=7),
    ),
    ChoreAssociation(
        id=_ASSOC_004,
        master_chore_id=_MASTER_004,
        member_id=_MEMBER_RAYA,
        created_by=_MEMBER_TRISHA,
        created_at=_NOW - timedelta(days=5),
        updated_at=_NOW - timedelta(days=5),
    ),
    ChoreAssociation(
        id=_ASSOC_005,
        master_chore_id=_MASTER_006,
        member_id=_MEMBER_ARYA,
        created_by=_MEMBER_FAIYAZ,
        created_at=_NOW - timedelta(days=10),
        updated_at=_NOW - timedelta(days=10),
    ),
    ChoreAssociation(
        id=_ASSOC_006,
        master_chore_id=_MASTER_007,
        member_id=_MEMBER_ARYA,
        created_by=_MEMBER_FAIYAZ,
        created_at=_NOW - timedelta(days=5),
        updated_at=_NOW - timedelta(days=5),
    ),
]

# Chore instances with various statuses
_INSTANCES = [
    # Active — open pool, unclaimed
    ChoreInstance(
        id=_INST_001,
        master_chore_id=_MASTER_001,
        association_id=_ASSOC_001,
        period_start=_TODAY,
        period_end=_TODAY,
        member_id=_MEMBER_ARYA,
        status=InstanceStatus.ACTIVE,
        created_at=_NOW - timedelta(hours=6),
        updated_at=_NOW - timedelta(hours=6),
    ),
    ChoreInstance(
        id=_INST_002,
        master_chore_id=_MASTER_003,
        association_id=_ASSOC_002,
        period_start=_TODAY - timedelta(days=_TODAY.weekday()),
        period_end=_TODAY - timedelta(days=_TODAY.weekday()) + timedelta(days=6),
        member_id=_MEMBER_FAIYAZ,  # Claimed from open pool
        status=InstanceStatus.ACTIVE,
        created_at=_NOW - timedelta(days=1),
        updated_at=_NOW - timedelta(days=1),
    ),
    # In progress by arya (self-claimed)
    ChoreInstance(
        id=_INST_003,
        master_chore_id=_MASTER_002,
        association_id=_ASSOC_003,
        period_start=_TODAY,
        period_end=_TODAY,
        member_id=_MEMBER_ARYA,
        status=InstanceStatus.IN_PROGRESS,
        started_at=_NOW - timedelta(hours=2),
        created_at=_NOW - timedelta(hours=8),
        updated_at=_NOW - timedelta(hours=2),
    ),
    # Assigned to raya by trisha
    ChoreInstance(
        id=_INST_004,
        master_chore_id=_MASTER_004,
        association_id=_ASSOC_004,
        period_start=_TODAY - timedelta(days=_TODAY.weekday()),
        period_end=_TODAY - timedelta(days=_TODAY.weekday()) + timedelta(days=6),
        member_id=_MEMBER_RAYA,
        assigned_by=_MEMBER_TRISHA,
        status=InstanceStatus.ACTIVE,
        created_at=_NOW - timedelta(days=2),
        updated_at=_NOW - timedelta(days=2),
    ),
    # Completed by arya (self-completed)
    ChoreInstance(
        id=_INST_005,
        master_chore_id=_MASTER_006,
        association_id=_ASSOC_005,
        period_start=_TODAY - timedelta(days=1),
        period_end=_TODAY - timedelta(days=1),
        member_id=_MEMBER_ARYA,
        status=InstanceStatus.COMPLETED,
        completed_at=_NOW - timedelta(hours=12),
        created_at=_NOW - timedelta(days=1),
        updated_at=_NOW - timedelta(hours=12),
    ),
    # Completed by faiyaz (self-completed)
    ChoreInstance(
        id=_INST_006,
        master_chore_id=_MASTER_001,
        association_id=_ASSOC_001,
        period_start=_TODAY - timedelta(days=1),
        period_end=_TODAY - timedelta(days=1),
        member_id=_MEMBER_FAIYAZ,
        status=InstanceStatus.COMPLETED,
        completed_at=_NOW - timedelta(hours=20),
        created_at=_NOW - timedelta(days=1),
        updated_at=_NOW - timedelta(hours=20),
    ),
    # In progress by raya (assigned by faiyaz)
    ChoreInstance(
        id=_INST_007,
        master_chore_id=_MASTER_002,
        association_id=_ASSOC_003,
        period_start=_TODAY - timedelta(days=1),
        period_end=_TODAY - timedelta(days=1),
        member_id=_MEMBER_RAYA,
        assigned_by=_MEMBER_FAIYAZ,
        started_at=_NOW - timedelta(hours=1),
        created_at=_NOW - timedelta(days=1),
        updated_at=_NOW - timedelta(hours=1),
    ),
]


class MockChoresRepository:
    """Mock chores repository for development and testing.

    Implements the ChoresRepository protocol with realistic hardcoded
    data matching the Haider family.
    """

    def __init__(self) -> None:
        """Initialize mock data stores."""
        self._categories = copy.deepcopy(_PRESET_CATEGORIES)
        self._tags = copy.deepcopy(_SAMPLE_TAGS)
        self._masters = copy.deepcopy(_ALL_MASTERS)
        self._instances = copy.deepcopy(_INSTANCES)
        self._associations = copy.deepcopy(_ASSOCIATIONS)

    async def get_categories(self) -> list[ChoreCategory]:
        """Return mock chore categories.

        Returns:
            List of preset ChoreCategory entities.
        """
        return list(self._categories)

    async def create_category(self, name: str) -> ChoreCategory:
        """Create a mock chore category.

        Args:
            name: Category display name.

        Returns:
            The newly created category.
        """
        category = ChoreCategory(
            id=uuid7(),
            name=name,
        )
        self._categories.append(category)
        return category

    async def get_tags(self) -> list[ChoreTag]:
        """Return mock chore tags.

        Returns:
            List of sample ChoreTag entities.
        """
        return list(self._tags)

    async def create_tag(self, name: str) -> ChoreTag:
        """Create a mock chore tag.

        Args:
            name: Tag display name.

        Returns:
            The newly created tag.
        """
        tag = ChoreTag(
            id=uuid7(),
            name=name,
        )
        self._tags.append(tag)
        return tag

    async def get_master_chores(self, include_archived: bool = False) -> list[MasterChore]:
        """Return mock master chores.

        Args:
            include_archived: Whether to include archived masters.

        Returns:
            List of MasterChore entities.
        """
        if include_archived:
            return list(self._masters)
        return [m for m in self._masters if m.deleted_at is None]

    async def get_master_chore_by_id(self, chore_id: UUID) -> MasterChore | None:
        """Return a mock master chore by ID.

        Args:
            chore_id: Unique identifier for the master chore.

        Returns:
            MasterChore if found, None otherwise.
        """
        for master in self._masters:
            if master.id == chore_id:
                return master
        return None

    async def create_master_chore(self, chore: MasterChore, tag_ids: list[UUID]) -> MasterChore:
        """Create a mock master chore.

        Args:
            chore: MasterChore entity to add.
            tag_ids: List of tag IDs to associate.

        Returns:
            The created MasterChore with tags resolved.
        """
        tags = [t for t in self._tags if t.id in tag_ids]
        chore.tags = tags
        self._masters.append(chore)
        return chore

    async def update_master_chore(self, chore_id: UUID, updates: dict) -> MasterChore:
        """Update a mock master chore.

        Args:
            chore_id: Unique identifier for the master chore.
            updates: Dictionary of field names to new values.

        Returns:
            The updated MasterChore.

        Raises:
            ValueError: If the master chore is not found.
        """
        for master in self._masters:
            if master.id == chore_id:
                for key, value in updates.items():
                    if hasattr(master, key):
                        setattr(master, key, value)
                return master
        raise ValueError(f"Master chore '{chore_id}' not found")

    async def delete_master_chore(self, chore_id: UUID) -> None:
        """Soft-delete a mock master chore.

        Args:
            chore_id: Unique identifier for the master chore.
        """
        for master in self._masters:
            if master.id == chore_id:
                master.deleted_at = datetime.now(UTC)
                master.status = MasterChoreStatus.ARCHIVED
                return

    async def permanent_delete_master_chore(self, chore_id: UUID) -> None:
        """Hard-delete a mock master chore and all related data.

        Args:
            chore_id: Unique identifier for the master chore.
        """
        # Find association IDs for this master
        assoc_ids = [a.id for a in self._associations if a.master_chore_id == chore_id]

        # Delete instances belonging to those associations
        self._instances = [i for i in self._instances if i.association_id not in assoc_ids]

        # Delete associations for this master
        self._associations = [a for a in self._associations if a.master_chore_id != chore_id]

        # Delete the master itself
        self._masters = [m for m in self._masters if m.id != chore_id]

    async def get_instances(self, master_chore_id: UUID | None = None) -> list[ChoreInstance]:
        """Return mock chore instances.

        Args:
            master_chore_id: If provided, only return instances for this master.

        Returns:
            List of ChoreInstance entities.
        """
        if master_chore_id:
            return [i for i in self._instances if i.master_chore_id == master_chore_id]
        return list(self._instances)

    async def get_instance_by_id(self, instance_id: UUID) -> ChoreInstance | None:
        """Return a mock chore instance by ID.

        Args:
            instance_id: Unique identifier for the instance.

        Returns:
            ChoreInstance if found, None otherwise.
        """
        for instance in self._instances:
            if instance.id == instance_id:
                return instance
        return None

    async def create_instance(self, instance: ChoreInstance) -> ChoreInstance:
        """Create a mock chore instance.

        Args:
            instance: ChoreInstance entity to add.

        Returns:
            The created ChoreInstance.
        """
        self._instances.append(instance)
        return instance

    async def update_instance(self, instance_id: UUID, updates: dict) -> ChoreInstance:
        """Update a mock chore instance.

        Args:
            instance_id: Unique identifier for the instance.
            updates: Dictionary of field names to new values.

        Returns:
            The updated ChoreInstance.

        Raises:
            ValueError: If the instance is not found.
        """
        for instance in self._instances:
            if instance.id == instance_id:
                for key, value in updates.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                return instance
        raise ValueError(f"Instance '{instance_id}' not found")

    async def delete_instance(self, instance_id: UUID) -> None:
        """Delete a mock chore instance.

        Args:
            instance_id: Unique identifier for the instance.
        """
        self._instances = [i for i in self._instances if i.id != instance_id]

    # ── Associations ───────────────────────────────────────────

    async def get_association(self, association_id: UUID) -> ChoreAssociation | None:
        """Return a mock chore association by ID.

        Args:
            association_id: Unique identifier for the association.

        Returns:
            ChoreAssociation if found, None otherwise.
        """
        for association in self._associations:
            if association.id == association_id:
                return association
        return None

    async def create_association(self, association: ChoreAssociation) -> ChoreAssociation:
        """Create a mock chore association.

        Args:
            association: ChoreAssociation entity to add.

        Returns:
            The created ChoreAssociation.
        """
        self._associations.append(association)
        return association

    async def delete_association(self, association_id: UUID) -> None:
        """Soft-delete a mock chore association.

        Args:
            association_id: Unique identifier for the association.
        """
        for association in self._associations:
            if association.id == association_id:
                association.removed_at = datetime.now(UTC)
                return

    async def list_associations(
        self,
        master_chore_id: UUID | None = None,
        member_id: UUID | None = None,
        include_removed: bool = False,
    ) -> list[ChoreAssociation]:
        """Return mock chore associations with optional filters.

        Args:
            master_chore_id: Filter by master chore ID.
            member_id: Filter by member UUID (None = open pool).
            include_removed: Whether to include soft-deleted associations.

        Returns:
            List of ChoreAssociation entities.
        """
        result = self._associations
        if not include_removed:
            result = [a for a in result if a.removed_at is None]
        if master_chore_id:
            result = [a for a in result if a.master_chore_id == master_chore_id]
        if member_id is not None:
            result = [a for a in result if a.member_id == member_id]
        return result

    async def get_associations_by_master(self, master_chore_id: UUID) -> list[ChoreAssociation]:
        """Return all active associations for a master chore.

        Args:
            master_chore_id: Unique identifier for the master chore.

        Returns:
            List of active ChoreAssociation entities.
        """
        return await self.list_associations(master_chore_id=master_chore_id)

    async def get_associations_by_member(self, member_id: UUID) -> list[ChoreAssociation]:
        """Return all active associations for a member.

        Args:
            member_id: UUID of the member.

        Returns:
            List of active ChoreAssociation entities.
        """
        return await self.list_associations(member_id=member_id)

    async def get_instances_by_association(
        self, association_id: UUID, active_only: bool = True
    ) -> list[ChoreInstance]:
        """Return instances linked to a specific association.

        Args:
            association_id: FK to the association.
            active_only: If True, only return non-completed/non-archived instances.

        Returns:
            List of matching ChoreInstance entities.
        """
        instances = [i for i in self._instances if i.association_id == association_id]
        if active_only:
            instances = [
                i for i in instances
                if i.status in (InstanceStatus.ACTIVE, InstanceStatus.IN_PROGRESS)
            ]
        return instances

    async def archive_instances_by_association(self, association_id: UUID) -> int:
        """Archive all active instances for an association.

        Sets status to ARCHIVED for instances that are ACTIVE or IN_PROGRESS.

        Args:
            association_id: FK to the association.

        Returns:
            Number of instances archived.
        """
        archived_count = 0
        for instance in self._instances:
            if (
                instance.association_id == association_id
                and instance.status in (InstanceStatus.ACTIVE, InstanceStatus.IN_PROGRESS)
            ):
                instance.status = InstanceStatus.ARCHIVED
                instance.updated_at = datetime.now(UTC)
                archived_count += 1
        return archived_count

    async def get_instance_for_period(
        self,
        association_id: UUID,
        period_start: date,
    ) -> ChoreInstance | None:
        """Find an existing instance for a specific period and association.

        Matches on (association_id, period_start) per the unique constraint.

        Args:
            association_id: FK to the association.
            period_start: Period start date to match.

        Returns:
            ChoreInstance if found, None otherwise.
        """
        for instance in self._instances:
            if (
                instance.association_id == association_id
                and instance.period_start == period_start
                and instance.status != InstanceStatus.ARCHIVED
            ):
                return instance
        return None

    async def get_expired_instances(self, today: date) -> list[ChoreInstance]:
        """Return instances past their period_end with non-completed status.

        Args:
            today: Current date to compare against period_end.

        Returns:
            List of expired ChoreInstance entities.
        """
        return [
            instance
            for instance in self._instances
            if instance.period_end is not None
            and instance.period_end < today
            and instance.status
            in (InstanceStatus.ACTIVE, InstanceStatus.IN_PROGRESS, InstanceStatus.OVERDUE)
        ]

    async def get_overdue_instances(self, today: date, current_time: str) -> list[ChoreInstance]:
        """Return instances past their due time but within their period.

        Args:
            today: Current date.
            current_time: Current time in HH:MM format.

        Returns:
            List of overdue ChoreInstance entities.
        """
        overdue = []
        for instance in self._instances:
            if instance.status not in (InstanceStatus.ACTIVE, InstanceStatus.IN_PROGRESS):
                continue
            if instance.period_end is None or instance.period_end < today:
                continue

            master = next(
                (m for m in self._masters if m.id == instance.master_chore_id), None
            )
            if master and master.due_time and master.due_time < current_time:
                overdue.append(instance)
        return overdue

    async def bulk_update_master_status(
        self, master_ids: list[UUID], status: MasterChoreStatus
    ) -> int:
        """Update the status of multiple master chores at once.

        Args:
            master_ids: List of master chore IDs to update.
            status: New status to apply.

        Returns:
            Number of masters actually updated.
        """
        updated = 0
        now = datetime.now(UTC)
        for master in self._masters:
            if master.id in master_ids:
                master.status = status
                master.updated_at = now
                updated += 1
        return updated
