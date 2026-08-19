"""Chores API routes.

RESTful endpoints for the family chore management system.
"""

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.api.deps import ChoresServiceDep
from app.api.models.chores import (
    ApproveMasterChoreRequest,
    AssignInstanceRequest,
    ChoreCategoryResponse,
    ChoreInstanceResponse,
    ChoresResponse,
    ChoreTagResponse,
    ClaimInstanceRequest,
    CreateCategoryRequest,
    CreateMasterChoreRequest,
    CreateTagRequest,
    MasterChoreResponse,
    SignoffInstanceRequest,
    UpdateInstanceStatusRequest,
    UpdateMasterChoreRequest,
)
from app.domain.chores.models import (
    ChoreCategory,
    ChoreInstance,
    ChoreTag,
    ExpirationBehavior,
    Frequency,
    InstanceStatus,
    MasterChore,
)

router = APIRouter(prefix="/chores", tags=["chores"])


def _category_to_response(cat: ChoreCategory) -> ChoreCategoryResponse:
    """Map a domain ChoreCategory to the API response model.

    Args:
        cat: Domain entity.

    Returns:
        Pydantic response model.
    """
    return ChoreCategoryResponse(id=cat.id, name=cat.name)


def _tag_to_response(tag: ChoreTag) -> ChoreTagResponse:
    """Map a domain ChoreTag to the API response model.

    Args:
        tag: Domain entity.

    Returns:
        Pydantic response model.
    """
    return ChoreTagResponse(id=tag.id, name=tag.name)


def _master_to_response(
    master: MasterChore,
    category_map: dict[str, ChoreCategory],
) -> MasterChoreResponse:
    """Map a domain MasterChore to the API response model.

    Args:
        master: Domain entity.
        category_map: Lookup of category ID to category entity.

    Returns:
        Pydantic response model.
    """
    category = category_map.get(master.category_id)
    category_resp = (
        ChoreCategoryResponse(id=category.id, name=category.name)
        if category
        else ChoreCategoryResponse(id=master.category_id, name="Unknown")
    )
    return MasterChoreResponse(
        id=master.id,
        name=master.name,
        category=category_resp,
        tags=[_tag_to_response(t) for t in master.tags],
        difficulty=master.difficulty,
        frequency=master.frequency.value,
        estimated_minutes=master.estimated_minutes,
        due_time=master.due_time,
        due_date=master.due_date,
        expiration_behavior=master.expiration_behavior.value,
        created_by=master.created_by,
        approved_by=master.approved_by,
        status=master.status.value,
        created_at=master.created_at.isoformat(),
        updated_at=master.updated_at.isoformat(),
        deleted_at=master.deleted_at.isoformat() if master.deleted_at else None,
    )


def _instance_to_response(instance: ChoreInstance) -> ChoreInstanceResponse:
    """Map a domain ChoreInstance to the API response model.

    Args:
        instance: Domain entity.

    Returns:
        Pydantic response model.
    """
    return ChoreInstanceResponse(
        id=instance.id,
        master_chore_id=instance.master_chore_id,
        period_start=instance.period_start,
        period_end=instance.period_end,
        status=instance.status.value,
        claimed_by=instance.claimed_by,
        assigned_to=instance.assigned_to,
        assigned_by=instance.assigned_by,
        completed_by=instance.completed_by,
        signoff_by=instance.signoff_by,
        started_at=instance.started_at,
        completed_at=instance.completed_at,
        signed_off_at=instance.signed_off_at,
        created_at=instance.created_at.isoformat(),
        updated_at=instance.updated_at.isoformat(),
    )


@router.get("", response_model=ChoresResponse)
async def get_all_chores(
    chores_service: ChoresServiceDep,
) -> ChoresResponse:
    """Get all chores data (categories, tags, masters, instances).

    Args:
        chores_service: Injected chores service.

    Returns:
        Full chores data payload.
    """
    data = await chores_service.get_all_data()

    category_map = {cat.id: cat for cat in data["categories"]}

    return ChoresResponse(
        categories=[_category_to_response(c) for c in data["categories"]],
        tags=[_tag_to_response(t) for t in data["tags"]],
        master_chores=[_master_to_response(m, category_map) for m in data["master_chores"]],
        instances=[_instance_to_response(i) for i in data["instances"]],
    )


@router.post("/masters", response_model=MasterChoreResponse, status_code=201)
async def create_master_chore(
    body: CreateMasterChoreRequest,
    chores_service: ChoresServiceDep,
) -> MasterChoreResponse:
    """Create a new master chore template.

    Args:
        body: Validated creation request.
        chores_service: Injected chores service.

    Returns:
        The newly created master chore.
    """
    # Determine if creator is adult (faiyaz/trisha are adults)
    adult_members = {"faiyaz", "trisha"}
    is_adult = body.created_by in adult_members

    chore = MasterChore(
        id=str(uuid4()),
        name=body.name,
        category_id=body.category_id,
        difficulty=body.difficulty,
        frequency=Frequency(body.frequency),
        estimated_minutes=body.estimated_minutes,
        due_time=body.due_time,
        due_date=body.due_date,
        expiration_behavior=ExpirationBehavior(body.expiration_behavior),
        created_by=body.created_by,
    )

    created = await chores_service.create_master_chore(
        chore=chore,
        tag_ids=body.tag_ids,
        is_adult_creator=is_adult,
        approver_id=body.approved_by,
    )

    # Build category map for response
    categories = await chores_service.get_categories()
    category_map = {cat.id: cat for cat in categories}

    return _master_to_response(created, category_map)


@router.put("/masters/{chore_id}", response_model=MasterChoreResponse)
async def update_master_chore(
    chore_id: str,
    body: UpdateMasterChoreRequest,
    chores_service: ChoresServiceDep,
) -> MasterChoreResponse:
    """Update a master chore template.

    Args:
        chore_id: Master chore identifier.
        body: Fields to update.
        chores_service: Injected chores service.

    Returns:
        The updated master chore.

    Raises:
        HTTPException 404: Master chore not found.
    """
    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.category_id is not None:
        updates["category_id"] = body.category_id
    if body.difficulty is not None:
        updates["difficulty"] = body.difficulty
    if body.frequency is not None:
        updates["frequency"] = Frequency(body.frequency)
    if body.estimated_minutes is not None:
        updates["estimated_minutes"] = body.estimated_minutes
    if body.due_time is not None:
        updates["due_time"] = body.due_time
    if body.due_date is not None:
        updates["due_date"] = body.due_date
    if body.expiration_behavior is not None:
        updates["expiration_behavior"] = ExpirationBehavior(body.expiration_behavior)
    if body.tag_ids is not None:
        updates["tag_ids"] = body.tag_ids

    try:
        updated = await chores_service.update_master_chore(chore_id, updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    categories = await chores_service.get_categories()
    category_map = {cat.id: cat for cat in categories}

    return _master_to_response(updated, category_map)


@router.delete("/masters/{chore_id}", status_code=204)
async def delete_master_chore(
    chore_id: str,
    chores_service: ChoresServiceDep,
) -> None:
    """Soft-delete (archive) a master chore.

    Args:
        chore_id: Master chore identifier.
        chores_service: Injected chores service.
    """
    await chores_service.delete_master_chore(chore_id)


@router.post("/masters/{chore_id}/approve", response_model=MasterChoreResponse)
async def approve_master_chore(
    chore_id: str,
    body: ApproveMasterChoreRequest,
    chores_service: ChoresServiceDep,
) -> MasterChoreResponse:
    """Approve a pending master chore.

    Args:
        chore_id: Master chore identifier.
        body: Approval request with approver ID.
        chores_service: Injected chores service.

    Returns:
        The approved master chore.

    Raises:
        HTTPException 400: Master chore not pending approval.
        HTTPException 404: Master chore not found.
    """
    try:
        approved = await chores_service.approve_master_chore(chore_id, body.approver_id)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    categories = await chores_service.get_categories()
    category_map = {cat.id: cat for cat in categories}

    return _master_to_response(approved, category_map)


@router.post("/instances/{instance_id}/claim", response_model=ChoreInstanceResponse)
async def claim_instance(
    instance_id: str,
    body: ClaimInstanceRequest,
    chores_service: ChoresServiceDep,
) -> ChoreInstanceResponse:
    """Claim a chore instance for a member.

    Args:
        instance_id: Instance identifier.
        body: Claim request with member ID.
        chores_service: Injected chores service.

    Returns:
        The updated instance.

    Raises:
        HTTPException 404: Instance not found.
    """
    try:
        updated = await chores_service.claim_instance(instance_id, body.member_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _instance_to_response(updated)


@router.post("/instances/{instance_id}/assign", response_model=ChoreInstanceResponse)
async def assign_instance(
    instance_id: str,
    body: AssignInstanceRequest,
    chores_service: ChoresServiceDep,
) -> ChoreInstanceResponse:
    """Assign a chore instance to a member.

    Args:
        instance_id: Instance identifier.
        body: Assign request with assignee and assigner IDs.
        chores_service: Injected chores service.

    Returns:
        The updated instance.

    Raises:
        HTTPException 404: Instance not found.
    """
    try:
        updated = await chores_service.assign_instance(
            instance_id, body.assignee_id, body.assigner_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _instance_to_response(updated)


@router.put("/instances/{instance_id}/status", response_model=ChoreInstanceResponse)
async def update_instance_status(
    instance_id: str,
    body: UpdateInstanceStatusRequest,
    chores_service: ChoresServiceDep,
) -> ChoreInstanceResponse:
    """Update the status of a chore instance.

    Args:
        instance_id: Instance identifier.
        body: Status update request.
        chores_service: Injected chores service.

    Returns:
        The updated instance.

    Raises:
        HTTPException 404: Instance not found.
    """
    try:
        new_status = InstanceStatus(body.status)
        updated = await chores_service.update_instance_status(
            instance_id,
            new_status,
            body.actor_id,
            is_adult=body.is_adult,
        )
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _instance_to_response(updated)


@router.post("/instances/{instance_id}/signoff", response_model=ChoreInstanceResponse)
async def signoff_instance(
    instance_id: str,
    body: SignoffInstanceRequest,
    chores_service: ChoresServiceDep,
) -> ChoreInstanceResponse:
    """Sign off on a kid-completed chore instance.

    Args:
        instance_id: Instance identifier.
        body: Signoff request with parent member ID.
        chores_service: Injected chores service.

    Returns:
        The updated instance.

    Raises:
        HTTPException 400: Instance not pending signoff.
        HTTPException 404: Instance not found.
    """
    try:
        updated = await chores_service.signoff_instance(instance_id, body.signoff_member_id)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _instance_to_response(updated)


@router.post("/categories", response_model=ChoreCategoryResponse, status_code=201)
async def create_category(
    body: CreateCategoryRequest,
    chores_service: ChoresServiceDep,
) -> ChoreCategoryResponse:
    """Create a new chore category.

    Args:
        body: Category creation request.
        chores_service: Injected chores service.

    Returns:
        The newly created category.
    """
    created = await chores_service.create_category(body.name)
    return _category_to_response(created)


@router.post("/tags", response_model=ChoreTagResponse, status_code=201)
async def create_tag(
    body: CreateTagRequest,
    chores_service: ChoresServiceDep,
) -> ChoreTagResponse:
    """Create a new chore tag.

    Args:
        body: Tag creation request.
        chores_service: Injected chores service.

    Returns:
        The newly created tag.
    """
    created = await chores_service.create_tag(body.name)
    return _tag_to_response(created)
