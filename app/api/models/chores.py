"""Chores API models.

Pydantic models for chores API requests and responses.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
        recurrence_rule: Recurrence pattern config (JSON).
        estimated_minutes: Optional time estimate.
        due_time: Optional time-of-day deadline.
        due_date: Optional specific due date.
        expiration_behavior: What happens when period ends.
        end_date: Stop generating after this date.
        max_occurrences: Stop after N total instances.
        occurrence_count: Total instances generated so far.
        conditions: Conditional chore conditions (JSON).
        is_collaborative: Whether multiple members can have instances.
        created_by: Member ID of the creator.
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
    recurrence_rule: dict | None = None
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: date | None = None
    expiration_behavior: str
    end_date: date | None = None
    max_occurrences: int | None = None
    occurrence_count: int = 0
    conditions: dict | None = None
    is_collaborative: bool = False
    created_by: str
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
        period_end: Period end date (ISO string).
        status: Current lifecycle status.
        claimed_by: Member ID who claimed this instance.
        assigned_to: Member ID who was assigned.
        assigned_by: Member ID who made the assignment.
        completed_by: Member ID who marked complete.
        started_at: ISO datetime when work began.
        completed_at: ISO datetime when marked complete.
        created_at: ISO datetime of creation.
        updated_at: ISO datetime of last update.
    """

    id: UUID
    master_chore_id: UUID
    association_id: UUID | None = None
    period_start: date | None = None
    period_end: date | None = None
    status: str
    claimed_by: str | None = None
    assigned_to: str | None = None
    assigned_by: str | None = None
    completed_by: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssociationResponse(BaseModel):
    """Response model for a chore association.

    Attributes:
        id: Unique identifier.
        master_chore_id: Parent master chore ID.
        member_id: Member ID (None for open pool).
        is_open_pool: Whether this is an open pool.
        created_by: Member ID who created this association.
        created_at: ISO datetime of creation.
        updated_at: ISO datetime of last update.
        removed_at: ISO datetime of soft-delete (None if active).
    """

    id: UUID
    master_chore_id: UUID
    member_id: str | None = None
    is_open_pool: bool = False
    created_by: str
    created_at: datetime
    updated_at: datetime
    removed_at: datetime | None = None


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
        recurrence_rule: Recurrence pattern config (JSON).
        estimated_minutes: Optional time estimate.
        due_time: Optional time-of-day deadline.
        due_date: Optional specific due date.
        expiration_behavior: What happens when period ends.
        end_date: Stop generating after this date.
        max_occurrences: Stop after N total instances.
        conditions: Conditional chore conditions (JSON).
        is_collaborative: Whether multiple members can have instances.
        created_by: Member ID of the creator.
    """

    name: str = Field(min_length=1, max_length=200)
    category_id: UUID
    tag_ids: list[UUID] = Field(default_factory=list)
    difficulty: int = Field(default=1, ge=1, le=5)
    recurrence_rule: dict | None = None
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: date | None = None
    expiration_behavior: str = Field(default="disappear")
    end_date: date | None = None
    max_occurrences: int | None = None
    conditions: dict | None = None
    is_collaborative: bool = False
    created_by: str


class UpdateMasterChoreRequest(BaseModel):
    """Request body for updating a master chore.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Chore name.
        category_id: Category to assign.
        tag_ids: Tags to associate.
        difficulty: Difficulty level (1-5).
        recurrence_rule: Recurrence pattern config (JSON).
        estimated_minutes: Optional time estimate.
        due_time: Optional time-of-day deadline.
        due_date: Optional specific due date.
        expiration_behavior: What happens when period ends.
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
    recurrence_rule: dict | None = None
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: date | None = None
    expiration_behavior: str | None = None
    end_date: date | None = None
    max_occurrences: int | None = None
    conditions: dict | None = None
    is_collaborative: bool | None = None
    status: str | None = None


class CreateAssociationRequest(BaseModel):
    """Request body for creating a chore association.

    Attributes:
        master_chore_id: Master chore to associate.
        member_id: Member to associate (None for open pool).
        is_open_pool: Whether this is an open pool.
        created_by: Member ID creating the association.
    """

    master_chore_id: UUID
    member_id: str | None = None
    is_open_pool: bool = False
    created_by: str


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
        member_id: Member ID claiming the instance.
    """

    member_id: str


class AssignInstanceRequest(BaseModel):
    """Request body for assigning a chore instance.

    Attributes:
        assignee_id: Member ID being assigned.
        assigner_id: Member ID making the assignment.
    """

    assignee_id: str
    assigner_id: str


class UpdateInstanceStatusRequest(BaseModel):
    """Request body for updating instance status.

    Attributes:
        status: Target status value.
        actor_id: Member ID performing the action.
    """

    status: str
    actor_id: str
