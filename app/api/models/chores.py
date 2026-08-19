"""Chores API models.

Pydantic models for chores API requests and responses.
"""

from pydantic import BaseModel, Field


class ChoreCategoryResponse(BaseModel):
    """Response model for a chore category.

    Attributes:
        id: Unique identifier.
        name: Display name.
    """

    id: str
    name: str


class ChoreTagResponse(BaseModel):
    """Response model for a chore tag.

    Attributes:
        id: Unique identifier.
        name: Display name.
    """

    id: str
    name: str


class MasterChoreResponse(BaseModel):
    """Response model for a master chore template.

    Attributes:
        id: Unique identifier.
        name: Chore name.
        category: The chore's category.
        tags: Associated tags.
        difficulty: Difficulty level (1-5).
        frequency: Recurrence frequency.
        estimated_minutes: Optional time estimate.
        due_time: Optional time-of-day deadline.
        due_date: Optional specific due date.
        expiration_behavior: What happens when period ends.
        created_by: Member ID of the creator.
        approved_by: Member ID of the approver.
        status: Current lifecycle status.
        created_at: ISO datetime of creation.
        updated_at: ISO datetime of last update.
        deleted_at: ISO datetime of soft-delete (None if active).
    """

    id: str
    name: str
    category: ChoreCategoryResponse
    tags: list[ChoreTagResponse]
    difficulty: int
    frequency: str
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: str | None = None
    expiration_behavior: str
    created_by: str
    approved_by: str | None = None
    status: str
    created_at: str
    updated_at: str
    deleted_at: str | None = None


class ChoreInstanceResponse(BaseModel):
    """Response model for a chore instance.

    Attributes:
        id: Unique identifier.
        master_chore_id: Parent master chore ID.
        period_start: Period start date (ISO string).
        period_end: Period end date (ISO string).
        status: Current lifecycle status.
        claimed_by: Member ID who claimed this instance.
        assigned_to: Member ID who was assigned.
        assigned_by: Member ID who made the assignment.
        completed_by: Member ID who marked complete.
        signoff_by: Member ID who signed off.
        started_at: ISO datetime when work began.
        completed_at: ISO datetime when marked complete.
        signed_off_at: ISO datetime when signed off.
        created_at: ISO datetime of creation.
        updated_at: ISO datetime of last update.
    """

    id: str
    master_chore_id: str
    period_start: str | None = None
    period_end: str | None = None
    status: str
    claimed_by: str | None = None
    assigned_to: str | None = None
    assigned_by: str | None = None
    completed_by: str | None = None
    signoff_by: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    signed_off_at: str | None = None
    created_at: str
    updated_at: str


class ChoresResponse(BaseModel):
    """Response model for the full chores data payload.

    Attributes:
        categories: All chore categories.
        tags: All chore tags.
        master_chores: All master chore templates.
        instances: All chore instances.
    """

    categories: list[ChoreCategoryResponse]
    tags: list[ChoreTagResponse]
    master_chores: list[MasterChoreResponse]
    instances: list[ChoreInstanceResponse]


class CreateMasterChoreRequest(BaseModel):
    """Request body for creating a master chore.

    Attributes:
        name: Chore name.
        category_id: Category to assign.
        tag_ids: Tags to associate.
        difficulty: Difficulty level (1-5).
        frequency: Recurrence frequency.
        estimated_minutes: Optional time estimate.
        due_time: Optional time-of-day deadline.
        due_date: Optional specific due date.
        expiration_behavior: What happens when period ends.
        created_by: Member ID of the creator.
        approved_by: Optional approver (for kid creators).
    """

    name: str = Field(min_length=1, max_length=200)
    category_id: str
    tag_ids: list[str] = Field(default_factory=list)
    difficulty: int = Field(default=1, ge=1, le=5)
    frequency: str = Field(default="once")
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: str | None = None
    expiration_behavior: str = Field(default="disappear")
    created_by: str
    approved_by: str | None = None


class UpdateMasterChoreRequest(BaseModel):
    """Request body for updating a master chore.

    All fields are optional — only provided fields are updated.

    Attributes:
        name: Chore name.
        category_id: Category to assign.
        tag_ids: Tags to associate.
        difficulty: Difficulty level (1-5).
        frequency: Recurrence frequency.
        estimated_minutes: Optional time estimate.
        due_time: Optional time-of-day deadline.
        due_date: Optional specific due date.
        expiration_behavior: What happens when period ends.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: str | None = None
    tag_ids: list[str] | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    frequency: str | None = None
    estimated_minutes: int | None = None
    due_time: str | None = None
    due_date: str | None = None
    expiration_behavior: str | None = None


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
        assigner_id: Member ID making the assignment (parent).
    """

    assignee_id: str
    assigner_id: str


class UpdateInstanceStatusRequest(BaseModel):
    """Request body for updating instance status.

    Attributes:
        status: Target status value.
        actor_id: Member ID performing the action.
        is_adult: Whether the actor is an adult (affects completion flow).
    """

    status: str
    actor_id: str
    is_adult: bool = True


class ApproveMasterChoreRequest(BaseModel):
    """Request body for approving a master chore.

    Attributes:
        approver_id: Member ID of the approving adult.
    """

    approver_id: str


class SignoffInstanceRequest(BaseModel):
    """Request body for signing off on a completed instance.

    Attributes:
        signoff_member_id: Parent member ID signing off.
    """

    signoff_member_id: str
