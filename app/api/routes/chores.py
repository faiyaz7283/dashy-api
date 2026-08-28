"""Chores API routes.

RESTful endpoints for the family chore management system.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from uuid6 import uuid7

from app.api.deps import ChoresServiceDep
from app.api.models.chores import (
    AssignInstanceRequest,
    AssociationCreateResponse,
    AssociationResponse,
    BulkUpdateMasterStatusRequest,
    ChoreCategoryResponse,
    ChoreInstanceResponse,
    ChoresResponse,
    ChoreTagResponse,
    ClaimInstanceRequest,
    CreateAssociationRequest,
    CreateCategoryRequest,
    CreateMasterChoreRequest,
    CreateTagRequest,
    MasterChoreResponse,
    UpdateInstanceStatusRequest,
    UpdateMasterChoreRequest,
)
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
from app.domain.chores.services import AssociationConflictError

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
    category_map: dict[UUID, ChoreCategory],
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
        recurrence_rule=master.recurrence_rule,
        estimated_minutes=master.estimated_minutes,
        due_time=master.due_time,
        due_date=master.due_date,
        expiration_behavior=master.expiration_behavior.value,
        end_date=master.end_date,
        max_occurrences=master.max_occurrences,
        occurrence_count=master.occurrence_count,
        conditions=master.conditions,
        is_collaborative=master.is_collaborative,
        created_by=master.created_by,
        status=master.status.value,
        created_at=master.created_at,
        updated_at=master.updated_at,
        deleted_at=master.deleted_at,
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


def _association_to_response(association: ChoreAssociation) -> AssociationResponse:
    """Map a domain ChoreAssociation to the API response model.

    Args:
        association: Domain entity.

    Returns:
        Pydantic response model.
    """
    return AssociationResponse(
        id=association.id,
        master_chore_id=association.master_chore_id,
        member_id=association.member_id,
        is_open_pool=association.is_open_pool,
        created_by=association.created_by,
        created_at=association.created_at,
        updated_at=association.updated_at,
        removed_at=association.removed_at,
    )


@router.get("", response_model=ChoresResponse)
async def get_all_chores(
    chores_service: ChoresServiceDep,
) -> ChoresResponse:
    """Get all chores data (categories, tags, masters, associations, instances).

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
        associations=[_association_to_response(a) for a in data["associations"]],
        instances=[_instance_to_response(i) for i in data["instances"]],
    )


@router.post("/sync", status_code=204)
async def sync_chores(
    chores_service: ChoresServiceDep,
) -> None:
    """Synchronize chore instance state.

    Runs the safety net to generate missing instances, mark overdue
    instances, and process expired instances. This is a write operation
    that should be called explicitly by the frontend on mount/refresh.

    Args:
        chores_service: Injected chores service.
    """
    await chores_service.sync()


@router.patch("/masters/bulk-status")
async def bulk_update_master_status(
    body: BulkUpdateMasterStatusRequest,
    chores_service: ChoresServiceDep,
) -> dict:
    """Bulk update the status of multiple master chores.

    Args:
        body: Request body with master IDs and new status.
        chores_service: Injected chores service dependency.

    Returns:
        Dict with updated count.

    Raises:
        HTTPException: If status is invalid.
    """
    try:
        status_enum = MasterChoreStatus(body.status)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {body.status}. Must be one of: active, inactive, archived",
        ) from e

    updated_count = await chores_service.bulk_update_master_status(body.master_ids, status_enum)

    return {"updated_count": updated_count}


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
    chore = MasterChore(
        id=uuid7(),
        name=body.name,
        category_id=body.category_id,
        difficulty=body.difficulty,
        recurrence_rule=body.recurrence_rule,
        estimated_minutes=body.estimated_minutes,
        due_time=body.due_time,
        due_date=body.due_date,
        expiration_behavior=(
            ExpirationBehavior(body.expiration_behavior)
            if body.expiration_behavior
            else ExpirationBehavior.DISAPPEAR
        ),
        end_date=body.end_date,
        max_occurrences=body.max_occurrences,
        conditions=body.conditions,
        is_collaborative=body.is_collaborative,
        created_by=body.created_by,
    )

    created = await chores_service.create_master_chore(
        chore=chore,
        tag_ids=body.tag_ids,
    )

    # Build category map for response
    categories = await chores_service.get_categories()
    category_map = {cat.id: cat for cat in categories}

    return _master_to_response(created, category_map)


@router.patch("/masters/{chore_id}", response_model=MasterChoreResponse)
async def update_master_chore(
    chore_id: UUID,
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
    if body.recurrence_rule is not None:
        updates["recurrence_rule"] = body.recurrence_rule
    if body.estimated_minutes is not None:
        updates["estimated_minutes"] = body.estimated_minutes
    if body.due_time is not None:
        updates["due_time"] = body.due_time
    if body.due_date is not None:
        updates["due_date"] = body.due_date
    if body.expiration_behavior is not None:
        updates["expiration_behavior"] = ExpirationBehavior(body.expiration_behavior)
    if body.end_date is not None:
        updates["end_date"] = body.end_date
    if body.max_occurrences is not None:
        updates["max_occurrences"] = body.max_occurrences
    if body.conditions is not None:
        updates["conditions"] = body.conditions
    if body.is_collaborative is not None:
        updates["is_collaborative"] = body.is_collaborative
    if body.status is not None:
        updates["status"] = MasterChoreStatus(body.status)
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
    chore_id: UUID,
    chores_service: ChoresServiceDep,
) -> None:
    """Soft-delete (archive) a master chore.

    Args:
        chore_id: Master chore identifier.
        chores_service: Injected chores service.
    """
    await chores_service.delete_master_chore(chore_id)


@router.post("/associations", response_model=AssociationCreateResponse, status_code=201)
async def create_association(
    body: CreateAssociationRequest,
    chores_service: ChoresServiceDep,
) -> AssociationCreateResponse:
    """Create a new association between a master chore and a member/pool.

    Optionally auto-claims or auto-assigns the generated instance.

    Args:
        body: Association creation request with optional auto_claim/auto_assign.
        chores_service: Injected chores service.

    Returns:
        The newly created association with the generated instance.

    Raises:
        HTTPException 404: Master chore not found or not active.
        HTTPException 409: Association violates collaborative constraints.
        HTTPException 422: Validation error (e.g. auto_claim without member_id).
    """
    association = ChoreAssociation(
        id=uuid7(),
        master_chore_id=body.master_chore_id,
        member_id=body.member_id,
        is_open_pool=body.is_open_pool,
        created_by=body.created_by,
    )

    try:
        created, instance = await chores_service.create_association(
            association,
            auto_claim=body.auto_claim,
            auto_assign=body.auto_assign.model_dump() if body.auto_assign else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AssociationConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc

    return AssociationCreateResponse(
        id=created.id,
        master_chore_id=created.master_chore_id,
        member_id=created.member_id,
        is_open_pool=created.is_open_pool,
        created_by=created.created_by,
        created_at=created.created_at,
        updated_at=created.updated_at,
        removed_at=created.removed_at,
        instance=_instance_to_response(instance) if instance else None,
    )


@router.delete("/associations/{association_id}", status_code=204)
async def delete_association(
    association_id: UUID,
    chores_service: ChoresServiceDep,
) -> None:
    """Soft-delete an association and archive its active instances.

    Args:
        association_id: Association identifier.
        chores_service: Injected chores service.

    Raises:
        HTTPException 404: Association not found.
    """
    try:
        await chores_service.delete_association(association_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/instances/{instance_id}/claim", response_model=ChoreInstanceResponse)
async def claim_instance(
    instance_id: UUID,
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
        HTTPException 422: Member already has an association for this master.
    """
    try:
        updated = await chores_service.claim_instance(instance_id, body.member_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AssociationConflictError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _instance_to_response(updated)


@router.post("/instances/{instance_id}/assign", response_model=ChoreInstanceResponse)
async def assign_instance(
    instance_id: UUID,
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
        HTTPException 422: Member already has an association for this master.
    """
    try:
        updated = await chores_service.assign_instance(
            instance_id, body.assignee_id, body.assigner_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AssociationConflictError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _instance_to_response(updated)


@router.patch("/instances/{instance_id}/status", response_model=ChoreInstanceResponse)
async def update_instance_status(
    instance_id: UUID,
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
        )
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
