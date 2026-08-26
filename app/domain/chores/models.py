"""Chores domain entities.

Domain entities for the family chore management system, including
master chore templates, chore instances, associations, categories, and tags.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID


class ExpirationBehavior(StrEnum):
    """What happens to an instance when its period ends without completion.

    Attributes:
        DISAPPEAR: Instance is removed entirely.
        CARRY_OVER: A new instance is generated for the next period.
        STAY_VISIBLE: Instance remains, marked as missed.
        CONVERT_TO_OPEN: Instance moves to the open pool for anyone to claim.
    """

    DISAPPEAR = "disappear"
    CARRY_OVER = "carry_over"
    STAY_VISIBLE = "stay_visible"
    CONVERT_TO_OPEN = "convert_to_open"


class MasterChoreStatus(StrEnum):
    """Lifecycle status of a master chore template.

    Attributes:
        ACTIVE: Generating instances.
        INACTIVE: Temporarily paused, not generating instances.
        ARCHIVED: Soft-deleted, no longer generating instances.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class InstanceStatus(StrEnum):
    """Lifecycle status of a chore instance.

    Attributes:
        ACTIVE: Available to claim or be assigned.
        IN_PROGRESS: Work has started.
        COMPLETED: Fully done.
        OVERDUE: Past due and not completed.
        MISSED: Period ended without completion.
        ARCHIVED: Soft-deleted.
    """

    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    MISSED = "missed"
    ARCHIVED = "archived"


@dataclass
class ChoreCategory:
    """A chore category for organizing master chores.

    Attributes:
        id: Unique identifier (UUID).
        name: Display name for the category.
        created_at: When the category was created.
    """

    id: UUID
    name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __eq__(self, other: object) -> bool:
        """Check equality based on identity (id).

        Args:
            other: Another object to compare.

        Returns:
            True if same id, False otherwise.
        """
        if not isinstance(other, ChoreCategory):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity (id).

        Returns:
            Hash value based on id.
        """
        return hash(self.id)


@dataclass
class ChoreTag:
    """A tag for labeling master chores.

    Attributes:
        id: Unique identifier (UUID).
        name: Display name for the tag.
        created_at: When the tag was created.
    """

    id: UUID
    name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __eq__(self, other: object) -> bool:
        """Check equality based on identity (id).

        Args:
            other: Another object to compare.

        Returns:
            True if same id, False otherwise.
        """
        if not isinstance(other, ChoreTag):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity (id).

        Returns:
            Hash value based on id.
        """
        return hash(self.id)


@dataclass
class MasterChore:
    """Master chore template defining a recurring or one-time chore.

    A master chore produces chore instances for each period based on
    its recurrence_rule configuration.

    Attributes:
        id: Unique identifier (UUID string).
        name: Chore name (e.g. "Wipe Kitchen Counter").
        category_id: FK to the chore category.
        tags: Associated tags for this chore.
        difficulty: Difficulty level from 1 (easy) to 5 (hard).
        recurrence_rule: Recurrence pattern config (validated as RecurrenceRule).
            Contains frequency, time, day_of_week, day_of_month, week_of_month, month.
        estimated_minutes: Optional time estimate in minutes.
        due_time: Optional time-of-day deadline (ISO time string).
        due_date: Optional specific due date (ISO date string).
        expiration_behavior: What happens when the period ends.
        end_date: Stop generating after this date (ISO date string).
        max_occurrences: Stop after N total instances generated.
        occurrence_count: Total instances generated so far.
        conditions: Conditional chore conditions (validated as ConditionsConfig).
        is_collaborative: Whether multiple members can have simultaneous instances.
        created_by: Member ID of the creator.
        status: Current lifecycle status.
        created_at: When the master was created.
        updated_at: When the master was last updated.
        deleted_at: When the master was soft-deleted (None = active).
    """

    id: UUID
    name: str
    category_id: UUID
    tags: list[ChoreTag] = field(default_factory=list)
    difficulty: int = 1
    recurrence_rule: dict | None = None
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: date | None = None
    expiration_behavior: ExpirationBehavior = ExpirationBehavior.DISAPPEAR
    end_date: date | None = None
    max_occurrences: int | None = None
    occurrence_count: int = 0
    conditions: dict | None = None
    is_collaborative: bool = False
    created_by: str = ""
    status: MasterChoreStatus = MasterChoreStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None

    def __eq__(self, other: object) -> bool:
        """Check equality based on identity (id).

        Args:
            other: Another object to compare.

        Returns:
            True if same id, False otherwise.
        """
        if not isinstance(other, MasterChore):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity (id).

        Returns:
            Hash value based on id.
        """
        return hash(self.id)


@dataclass
class ChoreInstance:
    """A single occurrence of a chore for a specific period.

    Generated from a master chore template via an association. Each instance
    has its own status, claim/assignment, and completion tracking.

    Attributes:
        id: Unique identifier (UUID string).
        master_chore_id: FK to the parent master chore template.
        association_id: FK to the association that generated this instance.
        period_start: When this instance's period begins.
        period_end: When this instance's period ends.
        status: Current lifecycle status.
        claimed_by: Member ID who voluntarily claimed this instance.
        assigned_to: Member ID who was assigned this instance.
        assigned_by: Member ID who made the assignment.
        completed_by: Member ID who marked this as done.
        started_at: When work began.
        completed_at: When marked complete.
        created_at: When the instance was created.
        updated_at: When the instance was last updated.
    """

    id: UUID
    master_chore_id: UUID
    association_id: UUID | None = None
    period_start: date | None = None
    period_end: date | None = None
    status: InstanceStatus = InstanceStatus.ACTIVE
    claimed_by: str | None = None
    assigned_to: str | None = None
    assigned_by: str | None = None
    completed_by: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __eq__(self, other: object) -> bool:
        """Check equality based on identity (id).

        Args:
            other: Another object to compare.

        Returns:
            True if same id, False otherwise.
        """
        if not isinstance(other, ChoreInstance):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity (id).

        Returns:
            Hash value based on id.
        """
        return hash(self.id)


@dataclass
class ChoreAssociation:
    """Persistent link between a master chore and a member or open pool.

    Associations trigger instance generation and track who is responsible
    for a chore. Soft-deleted by setting removed_at.

    Attributes:
        id: Unique identifier (UUID string).
        master_chore_id: FK to the master chore template.
        member_id: FK to the family member (None for open pool).
        is_open_pool: Whether this is an open pool (anyone can claim).
        created_by: Member ID who created this association.
        created_at: When the association was created.
        updated_at: When the association was last updated.
        removed_at: When the association was soft-deleted (None = active).
    """

    id: UUID
    master_chore_id: UUID
    member_id: str | None = None
    is_open_pool: bool = False
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    removed_at: datetime | None = None

    def __eq__(self, other: object) -> bool:
        """Check equality based on identity (id).

        Args:
            other: Another object to compare.

        Returns:
            True if same id, False otherwise.
        """
        if not isinstance(other, ChoreAssociation):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on identity (id).

        Returns:
            Hash value based on id.
        """
        return hash(self.id)
