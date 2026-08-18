"""Family API routes.

RESTful CRUD endpoints for the family member registry.
The family member table is the canonical source of member identity
used across all features (calendar, rewards, permissions, etc.).
"""

from fastapi import APIRouter, HTTPException

from app.api.deps import FamilyServiceDep
from app.api.models.family import FamilyMember
from app.api.models.requests import CreateFamilyMemberRequest, UpdateFamilyMemberRequest
from app.domain.family.models import FamilyMember as DomainFamilyMember

router = APIRouter(prefix="/family", tags=["family"])


def _to_response(member: DomainFamilyMember) -> FamilyMember:
    """Map a domain FamilyMember to the API response model.

    Args:
        member: Domain entity.

    Returns:
        Pydantic response model.
    """
    return FamilyMember(
        name=member.name,
        key=member.id,
        email=member.email,
        color=member.color,
        initial=member.initial,
        date_of_birth=member.date_of_birth,
        relation=member.relation,
    )


@router.get("", response_model=list[FamilyMember])
async def list_family_members(
    family_service: FamilyServiceDep,
) -> list[FamilyMember]:
    """List all family members.

    Args:
        family_service: Injected family service.

    Returns:
        List of all registered family members.
    """
    members = await family_service.get_all_members()
    return [_to_response(m) for m in members]


@router.post("", response_model=FamilyMember, status_code=201)
async def create_family_member(
    body: CreateFamilyMemberRequest,
    family_service: FamilyServiceDep,
) -> FamilyMember:
    """Register a new family member.

    Args:
        body: Validated creation request.
        family_service: Injected family service.

    Returns:
        The newly created family member.

    Raises:
        HTTPException 409: A member with the given key already exists.
    """
    existing = await family_service.get_member(body.key)
    if existing:
        raise HTTPException(status_code=409, detail=f"Member '{body.key}' already exists")

    member = DomainFamilyMember(
        id=body.key,
        name=body.name,
        email=body.email,
        color=body.color,
        initial=body.initial,
        date_of_birth=body.date_of_birth,
        relation=body.relation,
    )
    await family_service.add_member(member)
    return _to_response(member)


@router.get("/{member_key}", response_model=FamilyMember)
async def get_family_member(
    member_key: str,
    family_service: FamilyServiceDep,
) -> FamilyMember:
    """Get a single family member by key.

    Args:
        member_key: Unique member identifier.
        family_service: Injected family service.

    Returns:
        The requested family member.

    Raises:
        HTTPException 404: No member found with the given key.
    """
    member = await family_service.get_member(member_key)
    if not member:
        raise HTTPException(status_code=404, detail=f"Member '{member_key}' not found")
    return _to_response(member)


@router.put("/{member_key}", response_model=FamilyMember)
async def replace_family_member(
    member_key: str,
    body: CreateFamilyMemberRequest,
    family_service: FamilyServiceDep,
) -> FamilyMember:
    """Fully replace a family member (upsert).

    If the member exists, all fields are replaced. If not, a new member
    is created with the provided key.

    Args:
        member_key: Unique member identifier.
        body: Complete member data.
        family_service: Injected family service.

    Returns:
        The replaced/created family member.
    """
    member = DomainFamilyMember(
        id=member_key,
        name=body.name,
        email=body.email,
        color=body.color,
        initial=body.initial,
        date_of_birth=body.date_of_birth,
        relation=body.relation,
    )
    await family_service.update_member(member)
    return _to_response(member)


@router.patch("/{member_key}", response_model=FamilyMember)
async def update_family_member(
    member_key: str,
    body: UpdateFamilyMemberRequest,
    family_service: FamilyServiceDep,
) -> FamilyMember:
    """Partially update a family member.

    Only the fields provided in the request body are updated.

    Args:
        member_key: Unique member identifier.
        body: Partial member data (only changed fields).
        family_service: Injected family service.

    Returns:
        The updated family member.

    Raises:
        HTTPException 404: No member found with the given key.
    """
    existing = await family_service.get_member(member_key)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Member '{member_key}' not found")

    updated = DomainFamilyMember(
        id=existing.id,
        name=body.name if body.name is not None else existing.name,
        email=body.email if body.email is not None else existing.email,
        color=body.color if body.color is not None else existing.color,
        initial=body.initial if body.initial is not None else existing.initial,
        date_of_birth=(
            body.date_of_birth if body.date_of_birth is not None
            else existing.date_of_birth
        ),
        relation=body.relation if body.relation is not None else existing.relation,
    )
    await family_service.update_member(updated)
    return _to_response(updated)


@router.delete("/{member_key}", status_code=204)
async def delete_family_member(
    member_key: str,
    family_service: FamilyServiceDep,
) -> None:
    """Delete a family member.

    Args:
        member_key: Unique member identifier.
        family_service: Injected family service.

    Raises:
        HTTPException 404: No member found with the given key.
    """
    existing = await family_service.get_member(member_key)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Member '{member_key}' not found")
    await family_service.delete_member(member_key)
