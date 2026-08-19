"""Chores domain entities.

Domain entities for the family chore management system, including
master chore templates, chore instances, categories, and tags.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Frequency(StrEnum):
    """How often a master chore recurs.

    Attributes:
        ONCE: One-time chore, no recurring period.
        DAILY: Recurs every calendar day.
        WEEKLY: Recurs every week (configurable start day).
        MONTHLY: Recurs every calendar month.
    """

    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


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
        PENDING_APPROVAL: Created by a kid, awaiting adult approval.
        ACTIVE: Approved and generating instances.
        ARCHIVED: Soft-deleted, no longer generating instances.
    """

    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    ARCHIVED = "archived"


class InstanceStatus(StrEnum):
    """Lifecycle status of a chore instance.

    Attributes:
        ACTIVE: Available to claim or be assigned.
        IN_PROGRESS: Work has started.
        COMPLETED_PENDING_SIGNOFF: Kid marked complete, awaiting parent signoff.
        COMPLETED: Fully done (signed off or adult self-completed).
        OVERDUE: Past due and not completed.
        MISSED: Period ended without completion.
        ARCHIVED: Soft-deleted.
    """

    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED_PENDING_SIGNOFF = "completed_pending_signoff"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    MISSED = "missed"
    ARCHIVED = "archived"


@dataclass
class ChoreCategory:
    """A chore category for organizing master chores.

    Attributes:
        id: Unique identifier (UUID string).
        name: Display name for the category.
        created_at: When the category was created.
    """

    id: str
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)

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
        id: Unique identifier (UUID string).
        name: Display name for the tag.
        created_at: When the tag was created.
    """

    id: str
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)

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
    its frequency setting.

    Attributes:
        id: Unique identifier (UUID string).
        name: Chore name (e.g. "Wipe Kitchen Counter").
        category_id: FK to the chore category.
        tags: Associated tags for this chore.
        difficulty: Difficulty level from 1 (easy) to 5 (hard).
        frequency: How often this chore recurs.
        estimated_minutes: Optional time estimate in minutes.
        due_time: Optional time-of-day deadline (ISO time string).
        due_date: Optional specific due date (ISO date string).
        expiration_behavior: What happens when the period ends.
        created_by: Member ID of the creator.
        approved_by: Member ID of the approver (None = auto-approved).
        status: Current lifecycle status.
        created_at: When the master was created.
        updated_at: When the master was last updated.
        deleted_at: When the master was soft-deleted (None = active).
    """

    id: str
    name: str
    category_id: str
    tags: list[ChoreTag] = field(default_factory=list)
    difficulty: int = 1
    frequency: Frequency = Frequency.ONCE
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: str | None = None
    expiration_behavior: ExpirationBehavior = ExpirationBehavior.DISAPPEAR
    created_by: str = ""
    approved_by: str | None = None
    status: MasterChoreStatus = MasterChoreStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
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

    Generated from a master chore template. Each instance has its own
    status, claim/assignment, and completion tracking.

    Attributes:
        id: Unique identifier (UUID string).
        master_chore_id: FK to the parent master chore template.
        period_start: When this instance's period begins.
        period_end: When this instance's period ends.
        status: Current lifecycle status.
        claimed_by: Member ID who voluntarily claimed this instance.
        assigned_to: Member ID who was assigned this instance by a parent.
        assigned_by: Member ID of the parent who made the assignment.
        completed_by: Member ID who marked this as done.
        signoff_by: Member ID of the parent who signed off.
        started_at: When work began.
        completed_at: When marked complete.
        signed_off_at: When parent signed off.
        created_at: When the instance was created.
        updated_at: When the instance was last updated.
    """

    id: str
    master_chore_id: str
    period_start: str | None = None
    period_end: str | None = None
    status: InstanceStatus = InstanceStatus.ACTIVE
    claimed_by: str | None = None
    assigned_to: str | None = None
    assigned_by: str | None = None
    completed_by: str | None = None
    signoff_by: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    signed_off_at: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

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
