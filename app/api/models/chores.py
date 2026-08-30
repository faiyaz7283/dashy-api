"""Chores API models.

Pydantic models for chores API requests and responses.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.chores.models import InstanceStatus, MasterChoreStatus


class ChoreCategoryResponse(BaseModel):
    """Response model for a chore category.

    Attributes:
        id: Unique identifier.
        name: Display name.
    """

    id: UUID
    name: str


class ChoreTagResponse(BaseModel):
    """Response model for a chore tag.

    Attributes:
        id: Unique identifier.
        name: Display name.
    """

    id: UUID
    name: str


class MasterChoreResponse(BaseModel):
    """Response model for a master chore template.

    Attributes:
        id: Unique identifier.
        name: Chore name.
        category: The chore's category.
        tags: Associated tags.
        difficulty: Difficulty level (1-5).
        frequency: Recurrence type (once, daily, weekly, monthly, yearly).
        frequency_interval: Every N days/weeks/months/years.
        day_of_week: Days of week for weekly/monthly (0=Mon..6=Sun).
        day_of_month: Day of month for monthly/yearly (1-31).
        week_of_month: Week of month for monthly (1-5).
        month: Month for yearly (1-12).
        estimated_minutes: Optional time estimate.
        due_time: Optional time-of-day deadline.
        due_date: Optional specific due date.
        end_date: Stop generating after this date.
        max_occurrences: Stop after N total instances.
        occurrence_count: Total instances generated so far.
        conditions: Conditional chore conditions (JSON).
        is_collaborative: Whether multiple members can have instances.
        created_by: Member UUID of the creator.
        status: Current lifecycle status.
        created_at: ISO datetime of creation.
        updated_at: ISO datetime of last update.
        deleted_at: ISO datetime of soft-delete (None if active).
    """

    id: UUID
    name: str
    category: ChoreCategoryResponse
    tags: list[ChoreTagResponse]
    difficulty: int
    frequency: str
    frequency_interval: int
    day_of_week: list[int] | None = None
    day_of_month: int | None = None
    week_of_month: int | None = None
    month: int | None = None
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: date | None = None
    end_date: date | None = None
    max_occurrences: int | None = None
    occurrence_count: int = 0
    conditions: dict | None = None
    is_collaborative: bool = False
    created_by: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class ChoreInstanceResponse(BaseModel):
    """Response model for a chore instance.

    Attributes:
        id: Unique identifier.
        master_chore_id: Parent master chore ID.
        association_id: FK to the association that generated this instance.
        period_start: Period start date (ISO string).
        period_end: Period end date (ISO string, None = no deadline).
        member_id: Member UUID who owns this instance (None for open pool).
        assigned_by: Member UUID who assigned (None = self-claimed).
        status: Current lifecycle status.
        started_at: ISO datetime when work began.
        completed_at: ISO datetime when marked complete.
        created_at: ISO datetime of creation.
        updated_at: ISO datetime of last update.
    """

    id: UUID
    master_chore_id: UUID
    association_id: UUID
    period_start: date
    period_end: date | None = None
    member_id: UUID | None = None
    assigned_by: UUID | None = None
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssociationResponse(BaseModel):
    """Response model for a chore association.

    Attributes:
        id: Unique identifier.
        master_chore_id: Parent master chore ID.
        member_id: Member UUID (None for open pool).
        created_by: Member UUID who created this association.
        created_at: ISO datetime of creation.
        updated_at: ISO datetime of last update.
        removed_at: ISO datetime of soft-delete (None if active).
    """

    id: UUID
    master_chore_id: UUID
    member_id: UUID | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    removed_at: datetime | None = None


class AssociationCreateResponse(BaseModel):
    """Response model for creating an association with optional auto-claim/assign.

    Extends the base association response with the generated instance,
    which is populated when auto_claim or auto_assign is used.

    Attributes:
        id: Unique identifier.
        master_chore_id: Parent master chore ID.
        member_id: Member UUID (None for open pool).
        created_by: Member UUID who created this association.
        created_at: ISO datetime of creation.
        updated_at: ISO datetime of last update.
        removed_at: ISO datetime of soft-delete (None if active).
        instance: The generated instance (None if generation was skipped).
    """

    id: UUID
    master_chore_id: UUID
    member_id: UUID | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    removed_at: datetime | None = None
    instance: ChoreInstanceResponse | None = None


class ChoresResponse(BaseModel):
    """Response model for the full chores data payload.

    Attributes:
        categories: All chore categories.
        tags: All chore tags.
        master_chores: All master chore templates.
        associations: All chore associations.
        instances: All chore instances.
    """

    categories: list[ChoreCategoryResponse]
    tags: list[ChoreTagResponse]
    master_chores: list[MasterChoreResponse]
    associations: list[AssociationResponse]
    instances: list[ChoreInstanceResponse]


class CreateMasterChoreRequest(BaseModel):
    """Request body for creating a master chore.

    Attributes:
        name: Chore name.
        category_id: Category to assign.
        tag_ids: Tags to associate.
        difficulty: Difficulty level (1-5).
        frequency: Recurrence type (once, daily, weekly, monthly, yearly).
        frequency_interval: Every N days/weeks/months/years.
        day_of_week: Days of week for weekly/monthly (0=Mon..6=Sun).
        day_of_month: Day of month for monthly/yearly (1-31).
        week_of_month: Week of month for monthly (1-5).
        month: Month for yearly (1-12).
        estimated_minutes: Optional time estimate.
        due_time: Optional time-of-day deadline.
        due_date: Optional specific due date.
        end_date: Stop generating after this date.
        max_occurrences: Stop after N total instances.
        conditions: Conditional chore conditions (JSON).
        is_collaborative: Whether multiple members can have instances.
        created_by: Member UUID of the creator.
    """

    name: str = Field(min_length=1, max_length=200)
    category_id: UUID
    tag_ids: list[UUID] = Field(default_factory=list)
    difficulty: int = Field(default=1, ge=1, le=5)
    frequency: str = Field(default="once")
    frequency_interval: int = Field(default=1, ge=1)
    day_of_week: list[int] | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    week_of_month: int | None = Field(default=None, ge=1, le=5)
    month: int | None = Field(default=None, ge=1, le=12)
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: date | None = None
    end_date: date | None = None
    max_occurrences: int | None = Field(default=None, ge=1)
    conditions: dict | None = None
    is_collaborative: bool = False
    created_by: UUID


class UpdateMasterChoreRequest(BaseModel):
    """Request body for updating a master chore.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Chore name.
        category_id: Category to assign.
        tag_ids: Tags to associate.
        difficulty: Difficulty level (1-5).
        frequency: Recurrence type (once, daily, weekly, monthly, yearly).
        frequency_interval: Every N days/weeks/months/years.
        day_of_week: Days of week for weekly/monthly (0=Mon..6=Sun).
        day_of_month: Day of month for monthly/yearly (1-31).
        week_of_month: Week of month for monthly (1-5).
        month: Month for yearly (1-12).
        estimated_minutes: Optional time estimate.
        due_time: Optional time-of-day deadline.
        due_date: Optional specific due date.
        end_date: Stop generating after this date.
        max_occurrences: Stop after N total instances.
        conditions: Conditional chore conditions (JSON).
        is_collaborative: Whether multiple members can have instances.
        status: Lifecycle status.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: UUID | None = None
    tag_ids: list[UUID] | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    frequency: str | None = None
    frequency_interval: int | None = Field(default=None, ge=1)
    day_of_week: list[int] | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    week_of_month: int | None = Field(default=None, ge=1, le=5)
    month: int | None = Field(default=None, ge=1, le=12)
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: date | None = None
    end_date: date | None = None
    max_occurrences: int | None = Field(default=None, ge=1)
    conditions: dict | None = None
    is_collaborative: bool | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate that status is a valid enum value."""
        if v is None:
            return v
        try:
            MasterChoreStatus(v)
        except ValueError:
            valid_values = [e.value for e in MasterChoreStatus]
            raise ValueError(
                f"Invalid status: {v}. Must be one of: {', '.join(valid_values)}"
            ) from None
        return v


class AutoAssignConfig(BaseModel):
    """Configuration for auto-assign on association creation.

    Attributes:
        assigner_id: Member UUID making the assignment.
    """

    assigner_id: UUID


class CreateAssociationRequest(BaseModel):
    """Request body for creating a chore association.

    Attributes:
        master_chore_id: Master chore to associate.
        member_id: Member UUID to associate (None for open pool).
        created_by: Member UUID creating the association.
        auto_claim: If True, automatically claim the generated instance for member_id.
        auto_assign: If provided, automatically assign the generated instance.
    """

    master_chore_id: UUID
    member_id: UUID | None = None
    created_by: UUID
    auto_claim: bool = False
    auto_assign: AutoAssignConfig | None = None

    @model_validator(mode="after")
    def validate_auto_flags_require_member(self) -> "CreateAssociationRequest":
        """Validate that auto_claim and auto_assign require member_id."""
        if self.auto_claim and self.member_id is None:
            raise ValueError("auto_claim requires member_id to be set")
        if self.auto_assign is not None and self.member_id is None:
            raise ValueError("auto_assign requires member_id to be set")
        if self.auto_claim and self.auto_assign is not None:
            raise ValueError("auto_claim and auto_assign are mutually exclusive")
        return self


class BulkUpdateMasterStatusRequest(BaseModel):
    """Request body for bulk updating master chore statuses.

    Attributes:
        master_ids: List of master chore IDs to update.
        status: New status to apply (active, inactive, archived).
    """

    master_ids: list[UUID] = Field(default_factory=list)
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate that status is a valid enum value."""
        try:
            MasterChoreStatus(v)
        except ValueError:
            valid_values = [e.value for e in MasterChoreStatus]
            raise ValueError(
                f"Invalid status: {v}. Must be one of: {', '.join(valid_values)}"
            ) from None
        return v


class CreateCategoryRequest(BaseModel):
    """Request body for creating a category.

    Attributes:
        name: Category display name.
    """

    name: str = Field(min_length=1, max_length=100)


class CreateTagRequest(BaseModel):
    """Request body for creating a tag.

    Attributes:
        name: Tag display name.
    """

    name: str = Field(min_length=1, max_length=100)


class ClaimInstanceRequest(BaseModel):
    """Request body for claiming a chore instance.

    Attributes:
        member_id: Member UUID claiming the instance.
    """

    member_id: UUID


class AssignInstanceRequest(BaseModel):
    """Request body for assigning a chore instance.

    Attributes:
        assignee_id: Member UUID being assigned.
        assigner_id: Member UUID making the assignment.
    """

    assignee_id: UUID
    assigner_id: UUID


class UpdateInstanceRequest(BaseModel):
    """Request body for updating a chore instance.

    Supports multiple operations via the action field:
    - claim: Set member_id, clear assigned_by (self-claim)
    - assign: Set member_id and assigned_by (assigned by another member)
    - revert: Revert status by one step
    - reset: Reset to active, clear progress fields
    - status: Generic status update (requires actor_id)

    Attributes:
        action: Operation to perform (claim, assign, revert, reset).
        status: Target status value (for generic status updates).
        member_id: Member UUID (for claim/assign operations).
        assigned_by: Member UUID who assigned (for assign operations).
        actor_id: Member UUID performing the action (for status updates).
    """

    action: str | None = None
    status: str | None = None
    member_id: UUID | None = None
    assigned_by: UUID | None = None
    actor_id: UUID | None = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str | None) -> str | None:
        """Validate that action is a valid value."""
        if v is None:
            return v
        valid_actions = {"claim", "assign", "revert", "reset"}
        if v not in valid_actions:
            raise ValueError(
                f"Invalid action: {v}. Must be one of: {', '.join(valid_actions)}"
            )
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate that status is a valid enum value."""
        if v is None:
            return v
        try:
            InstanceStatus(v)
        except ValueError:
            valid_values = [e.value for e in InstanceStatus]
            raise ValueError(
                f"Invalid status: {v}. Must be one of: {', '.join(valid_values)}"
            ) from None
        return v
