"""Mock chores adapter implementing ChoresRepository protocol.

Returns realistic mock data for development and testing, matching
the Haider family members (faiyaz, trisha, arya, raya).
"""

import copy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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

# Preset categories
_PRESET_CATEGORIES = [
    ChoreCategory(id="cat-kitchen", name="Kitchen"),
    ChoreCategory(id="cat-bathroom", name="Bathroom"),
    ChoreCategory(id="cat-outdoor", name="Outdoor"),
    ChoreCategory(id="cat-laundry", name="Laundry"),
    ChoreCategory(id="cat-general", name="General"),
]

# Sample tags
_SAMPLE_TAGS = [
    ChoreTag(id="tag-quick", name="Quick"),
    ChoreTag(id="tag-physical", name="Physical"),
    ChoreTag(id="tag-messy", name="Messy"),
    ChoreTag(id="tag-focus", name="Focus"),
    ChoreTag(id="tag-teamwork", name="Teamwork"),
]

_NOW = datetime.now(UTC)
_TODAY = _NOW.date()


def _iso(dt: datetime) -> str:
    """Format a datetime as ISO string.

    Args:
        dt: Datetime to format.

    Returns:
        ISO 8601 string.
    """
    return dt.isoformat()


def _date_str(d) -> str:
    """Format a date as ISO string.

    Args:
        d: Date to format.

    Returns:
        ISO 8601 date string.
    """
    return d.isoformat()


# Master chores
_MASTER_1 = MasterChore(
    id="master-001",
    name="Wipe Kitchen Counter",
    category_id="cat-kitchen",
    tags=[_SAMPLE_TAGS[0]],
    difficulty=1,
    recurrence_rule={"frequency": "daily", "time": "18:00"},
    estimated_minutes=5,
    expiration_behavior=ExpirationBehavior.CARRY_OVER,
    created_by="faiyaz",
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=14),
    updated_at=_NOW - timedelta(days=2),
)

_MASTER_2 = MasterChore(
    id="master-002",
    name="Clean Bathroom Sink",
    category_id="cat-bathroom",
    tags=[_SAMPLE_TAGS[0], _SAMPLE_TAGS[2]],
    difficulty=2,
    recurrence_rule={"frequency": "daily", "time": "20:00"},
    estimated_minutes=10,
    expiration_behavior=ExpirationBehavior.CARRY_OVER,
    created_by="trisha",
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=14),
    updated_at=_NOW - timedelta(days=1),
)

_MASTER_3 = MasterChore(
    id="master-003",
    name="Rake Leaves in Yard",
    category_id="cat-outdoor",
    tags=[_SAMPLE_TAGS[1]],
    difficulty=3,
    recurrence_rule={"frequency": "weekly", "day_of_week": 0, "time": "10:00"},
    estimated_minutes=30,
    expiration_behavior=ExpirationBehavior.CONVERT_TO_OPEN,
    created_by="faiyaz",
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=10),
    updated_at=_NOW - timedelta(days=3),
)

_MASTER_4 = MasterChore(
    id="master-004",
    name="Fold Laundry",
    category_id="cat-laundry",
    tags=[_SAMPLE_TAGS[0], _SAMPLE_TAGS[3]],
    difficulty=2,
    recurrence_rule={"frequency": "weekly", "day_of_week": 6, "time": "14:00"},
    estimated_minutes=20,
    expiration_behavior=ExpirationBehavior.CARRY_OVER,
    created_by="trisha",
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=7),
    updated_at=_NOW - timedelta(days=1),
)

_MASTER_5 = MasterChore(
    id="master-005",
    name="Organize Bookshelf",
    category_id="cat-general",
    tags=[_SAMPLE_TAGS[3]],
    difficulty=2,
    recurrence_rule={"frequency": "monthly", "day_of_month": 15, "time": "11:00"},
    estimated_minutes=45,
    expiration_behavior=ExpirationBehavior.STAY_VISIBLE,
    created_by="arya",
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=1),
    updated_at=_NOW - timedelta(days=1),
)

_MASTER_6 = MasterChore(
    id="master-006",
    name="Take Out Trash",
    category_id="cat-kitchen",
    tags=[_SAMPLE_TAGS[0]],
    difficulty=1,
    recurrence_rule={"frequency": "daily", "time": "19:00"},
    estimated_minutes=5,
    expiration_behavior=ExpirationBehavior.CARRY_OVER,
    created_by="faiyaz",
    status=MasterChoreStatus.ACTIVE,
    created_at=_NOW - timedelta(days=14),
    updated_at=_NOW - timedelta(days=7),
)

_ALL_MASTERS = [_MASTER_1, _MASTER_2, _MASTER_3, _MASTER_4, _MASTER_5, _MASTER_6]

# Mock associations
_ASSOCIATIONS = [
    ChoreAssociation(
        id="assoc-001",
        master_chore_id="master-001",
        member_id="arya",
        created_by="faiyaz",
        created_at=_NOW - timedelta(days=10),
        updated_at=_NOW - timedelta(days=10),
    ),
    ChoreAssociation(
        id="assoc-002",
        master_chore_id="master-003",
        is_open_pool=True,
        created_by="faiyaz",
        created_at=_NOW - timedelta(days=8),
        updated_at=_NOW - timedelta(days=8),
    ),
    ChoreAssociation(
        id="assoc-003",
        master_chore_id="master-002",
        member_id="arya",
        created_by="trisha",
        created_at=_NOW - timedelta(days=7),
        updated_at=_NOW - timedelta(days=7),
    ),
    ChoreAssociation(
        id="assoc-004",
        master_chore_id="master-004",
        member_id="raya",
        created_by="trisha",
        created_at=_NOW - timedelta(days=5),
        updated_at=_NOW - timedelta(days=5),
    ),
    ChoreAssociation(
        id="assoc-005",
        master_chore_id="master-006",
        member_id="arya",
        created_by="faiyaz",
        created_at=_NOW - timedelta(days=10),
        updated_at=_NOW - timedelta(days=10),
    ),
]

# Chore instances with various statuses
_INSTANCES = [
    # Active — open pool, unclaimed
    ChoreInstance(
        id="inst-001",
        master_chore_id="master-001",
        association_id="assoc-001",
        period_start=_date_str(_TODAY),
        period_end=_date_str(_TODAY),
        status=InstanceStatus.ACTIVE,
        created_at=_NOW - timedelta(hours=6),
        updated_at=_NOW - timedelta(hours=6),
    ),
    ChoreInstance(
        id="inst-002",
        master_chore_id="master-003",
        association_id="assoc-002",
        period_start=_date_str(_TODAY - timedelta(days=_TODAY.weekday())),
        period_end=_date_str(_TODAY - timedelta(days=_TODAY.weekday()) + timedelta(days=6)),
        status=InstanceStatus.ACTIVE,
        created_at=_NOW - timedelta(days=1),
        updated_at=_NOW - timedelta(days=1),
    ),
    # Claimed by arya, in progress
    ChoreInstance(
        id="inst-003",
        master_chore_id="master-002",
        association_id="assoc-003",
        period_start=_date_str(_TODAY),
        period_end=_date_str(_TODAY),
        status=InstanceStatus.IN_PROGRESS,
        claimed_by="arya",
        started_at=_iso(_NOW - timedelta(hours=2)),
        created_at=_NOW - timedelta(hours=8),
        updated_at=_NOW - timedelta(hours=2),
    ),
    # Assigned to raya
    ChoreInstance(
        id="inst-004",
        master_chore_id="master-004",
        association_id="assoc-004",
        period_start=_date_str(_TODAY - timedelta(days=_TODAY.weekday())),
        period_end=_date_str(_TODAY - timedelta(days=_TODAY.weekday()) + timedelta(days=6)),
        status=InstanceStatus.ACTIVE,
        assigned_to="raya",
        assigned_by="trisha",
        created_at=_NOW - timedelta(days=2),
        updated_at=_NOW - timedelta(days=2),
    ),
    # Completed (arya self-completed)
    ChoreInstance(
        id="inst-005",
        master_chore_id="master-006",
        association_id="assoc-005",
        period_start=_date_str(_TODAY - timedelta(days=1)),
        period_end=_date_str(_TODAY - timedelta(days=1)),
        status=InstanceStatus.COMPLETED,
        claimed_by="arya",
        completed_by="arya",
        completed_at=_iso(_NOW - timedelta(hours=12)),
        created_at=_NOW - timedelta(days=1),
        updated_at=_NOW - timedelta(hours=12),
    ),
    # Completed (faiyaz self-completed)
    ChoreInstance(
        id="inst-006",
        master_chore_id="master-001",
        association_id="assoc-001",
        period_start=_date_str(_TODAY - timedelta(days=1)),
        period_end=_date_str(_TODAY - timedelta(days=1)),
        status=InstanceStatus.COMPLETED,
        claimed_by="faiyaz",
        completed_by="faiyaz",
        completed_at=_iso(_NOW - timedelta(hours=20)),
        created_at=_NOW - timedelta(days=1),
        updated_at=_NOW - timedelta(hours=20),
    ),
    # In progress by raya
    ChoreInstance(
        id="inst-007",
        master_chore_id="master-002",
        association_id="assoc-003",
        period_start=_date_str(_TODAY - timedelta(days=1)),
        period_end=_date_str(_TODAY - timedelta(days=1)),
        status=InstanceStatus.IN_PROGRESS,
        assigned_to="raya",
        assigned_by="faiyaz",
        started_at=_iso(_NOW - timedelta(hours=1)),
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
            id=f"cat-{uuid4().hex[:8]}",
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
            id=f"tag-{uuid4().hex[:8]}",
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

    async def get_master_chore_by_id(self, chore_id: str) -> MasterChore | None:
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

    async def create_master_chore(self, chore: MasterChore, tag_ids: list[str]) -> MasterChore:
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

    async def update_master_chore(self, chore_id: str, updates: dict) -> MasterChore:
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

    async def delete_master_chore(self, chore_id: str) -> None:
        """Soft-delete a mock master chore.

        Args:
            chore_id: Unique identifier for the master chore.
        """
        for master in self._masters:
            if master.id == chore_id:
                master.deleted_at = datetime.now(UTC)
                master.status = MasterChoreStatus.ARCHIVED
                return

    async def get_instances(self, master_chore_id: str | None = None) -> list[ChoreInstance]:
        """Return mock chore instances.

        Args:
            master_chore_id: If provided, only return instances for this master.

        Returns:
            List of ChoreInstance entities.
        """
        if master_chore_id:
            return [i for i in self._instances if i.master_chore_id == master_chore_id]
        return list(self._instances)

    async def get_instance_by_id(self, instance_id: str) -> ChoreInstance | None:
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

    async def update_instance(self, instance_id: str, updates: dict) -> ChoreInstance:
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

    async def delete_instance(self, instance_id: str) -> None:
        """Delete a mock chore instance.

        Args:
            instance_id: Unique identifier for the instance.
        """
        self._instances = [i for i in self._instances if i.id != instance_id]

    # ── Associations ───────────────────────────────────────────

    async def get_association(self, association_id: str) -> ChoreAssociation | None:
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

    async def delete_association(self, association_id: str) -> None:
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
        master_chore_id: str | None = None,
        member_id: str | None = None,
        include_removed: bool = False,
    ) -> list[ChoreAssociation]:
        """Return mock chore associations with optional filters.

        Args:
            master_chore_id: Filter by master chore ID.
            member_id: Filter by member ID.
            include_removed: Whether to include soft-deleted associations.

        Returns:
            List of ChoreAssociation entities.
        """
        result = self._associations
        if not include_removed:
            result = [a for a in result if a.removed_at is None]
        if master_chore_id:
            result = [a for a in result if a.master_chore_id == master_chore_id]
        if member_id:
            result = [a for a in result if a.member_id == member_id]
        return result

    async def get_associations_by_master(self, master_chore_id: str) -> list[ChoreAssociation]:
        """Return all active associations for a master chore.

        Args:
            master_chore_id: Unique identifier for the master chore.

        Returns:
            List of active ChoreAssociation entities.
        """
        return await self.list_associations(master_chore_id=master_chore_id)

    async def get_associations_by_member(self, member_id: str) -> list[ChoreAssociation]:
        """Return all active associations for a member.

        Args:
            member_id: Unique identifier for the member.

        Returns:
            List of active ChoreAssociation entities.
        """
        return await self.list_associations(member_id=member_id)
