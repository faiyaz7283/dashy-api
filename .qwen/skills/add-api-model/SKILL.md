---
name: add-api-model
description: Add request/response Pydantic models for API endpoints — define schemas, validation, and serialization.
---

# Add API Model

Add request/response Pydantic models for API endpoints.

## When to use

- Adding a new endpoint and need request/response models
- Modifying an existing endpoint's contract
- Not for domain models — those go in `app/domain/<domain>/models.py`

## Prerequisites

- Understand the API contract (what data goes in, what comes out)
- Domain models exist if converting from domain entities
- Review existing models in `app/api/models/` for patterns

## Steps

### 1. Create or update model file

Edit `app/api/models/<domain>.py`:

```python
"""<Domain> API models.

Request and response models for <domain> endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class <Domain>Response(BaseModel):
    """Response model for <domain> data.

    Used for GET endpoints returning <domain> information.
    """

    id: str = Field(description="Unique identifier")
    name: str = Field(description="Display name", min_length=1, max_length=100)
    status: str = Field(description="Current status", pattern="^(active|inactive)$")
    created_at: datetime = Field(description="Creation timestamp")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field.

        Args:
            v: Name value.

        Returns:
            Validated name.

        Raises:
            ValueError: If name is invalid.
        """
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    @classmethod
    def from_entity(cls, entity: "<Domain>Entity") -> "<Domain>Response":
        """Create response model from domain entity.

        Args:
            entity: Domain entity instance.

        Returns:
            <Domain>Response instance.
        """
        return cls(
            id=entity.id.value,
            name=entity.name,
            status=entity.status.value,
            created_at=entity.created_at
        )


class Create<Domain>Request(BaseModel):
    """Request model for creating <domain>.

    Used for POST endpoints.
    """

    name: str = Field(description="Display name", min_length=1, max_length=100)
    status: str = Field(default="active", description="Initial status")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()


class Update<Domain>Request(BaseModel):
    """Request model for updating <domain>.

    Used for PUT/PATCH endpoints. All fields optional.
    """

    name: str | None = Field(default=None, description="Updated name", min_length=1, max_length=100)
    status: str | None = Field(default=None, description="Updated status", pattern="^(active|inactive)$")
```

### 2. Update exports

Edit `app/api/models/__init__.py`:

```python
"""API models for Dashy backend."""

from app.api.models.<domain> import (
    <Domain>Response,
    Create<Domain>Request,
    Update<Domain>Request,
)

__all__ = [
    "<Domain>Response",
    "Create<Domain>Request",
    "Update<Domain>Request",
]
```

### 3. Use in route handlers

```python
# app/api/routes/<domain>.py
from fastapi import APIRouter, Depends
from app.api.deps import <Domain>RepositoryDep
from app.api.models.<domain> import (
    <Domain>Response,
    Create<Domain>Request,
    Update<Domain>Request,
)

router = APIRouter(prefix="/<domain>", tags=["<domain>"])


@router.get("/{id}", response_model=<Domain>Response)
async def get_<domain>(
    id: str,
    repository: <Domain>RepositoryDep,
) -> <Domain>Response:
    """Get <domain> by ID.

    Args:
        id: Entity identifier.
        repository: Injected repository.

    Returns:
        <Domain>Response with entity data.

    Raises:
        HTTPException: If entity not found.
    """
    entity = await repository.get_by_id(id)
    if entity is None:
        raise HTTPException(status_code=404, detail="<Domain> not found")
    return <Domain>Response.from_entity(entity)


@router.post("", response_model=<Domain>Response, status_code=201)
async def create_<domain>(
    request: Create<Domain>Request,
    repository: <Domain>RepositoryDep,
) -> <Domain>Response:
    """Create new <domain>.

    Args:
        request: Creation request data.
        repository: Injected repository.

    Returns:
        <Domain>Response with created entity.
    """
    entity = <Domain>Entity(
        id=<Domain>Id(value=str(uuid.uuid4())),
        name=request.name,
        status=<Domain>Status(request.status)
    )
    await repository.save(entity)
    return <Domain>Response.from_entity(entity)


@router.put("/{id}", response_model=<Domain>Response)
async def update_<domain>(
    id: str,
    request: Update<Domain>Request,
    repository: <Domain>RepositoryDep,
) -> <Domain>Response:
    """Update existing <domain>.

    Args:
        id: Entity identifier.
        request: Update request data.
        repository: Injected repository.

    Returns:
        <Domain>Response with updated entity.
    """
    entity = await repository.get_by_id(id)
    if entity is None:
        raise HTTPException(status_code=404, detail="<Domain> not found")

    # Update fields if provided
    if request.name is not None:
        entity.name = request.name
    if request.status is not None:
        entity.status = <Domain>Status(request.status)

    await repository.save(entity)
    return <Domain>Response.from_entity(entity)
```

### 4. Verify OpenAPI docs

Start the server and visit `/docs`:

- Check request/response schemas are correct
- Verify field descriptions appear
- Test validation rules (min_length, pattern, etc.)

### 5. Add tests

```python
# tests/api/test_<domain>_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_create_<domain>_validates_name():
    """Test name validation on create."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Empty name should fail
        response = await client.post(
            "/api/v1/<domain>",
            json={"name": "", "status": "active"}
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_<domain>_response_format():
    """Test response model format."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/<domain>/test-id")

        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "name" in data
            assert "status" in data
            assert "created_at" in data
```

### 6. Run quality gate

```bash
make lint-api && make build-api && make test-api
```

## Common patterns

### Nested models

```python
class Address(BaseModel):
    """Address model."""
    street: str
    city: str
    zip_code: str


class PersonResponse(BaseModel):
    """Person response with nested address."""
    name: str
    address: Address
```

### Optional fields

```python
class UpdateRequest(BaseModel):
    """Update request with optional fields."""
    name: str | None = None
    email: str | None = None

    # Only update provided fields
    def get_updates(self) -> dict:
        """Get non-None fields."""
        return {k: v for k, v in self.model_dump().items() if v is not None}
```

### List responses

```python
class ListResponse(BaseModel):
    """Paginated list response."""
    items: list[<Domain>Response]
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page")
    per_page: int = Field(description="Items per page")
```

### Enum fields

```python
from enum import Enum


class StatusEnum(str, Enum):
    """Status enum for API."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class <Domain>Response(BaseModel):
    """Response with enum field."""
    status: StatusEnum
```

### Custom validation

```python
from pydantic import field_validator


class CreateRequest(BaseModel):
    """Request with custom validation."""
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()
```

## Validation rules

| Rule | Example | Use case |
|------|---------|----------|
| `min_length` | `Field(min_length=1)` | Non-empty strings |
| `max_length` | `Field(max_length=100)` | Limit string length |
| `pattern` | `Field(pattern="^[a-z]+$")` | Regex validation |
| `gt`, `lt` | `Field(gt=0)` | Numeric ranges |
| `field_validator` | Custom method | Complex validation |

## Checklist

- [ ] Response model created with all required fields
- [ ] Request models created (Create, Update) if needed
- [ ] Field descriptions added
- [ ] Validation rules applied (min_length, pattern, etc.)
- [ ] Custom validators added if needed
- [ ] `from_entity()` method for converting domain entities
- [ ] Models exported in `__init__.py`
- [ ] Models used in route handlers
- [ ] OpenAPI docs verified
- [ ] Tests added for validation
- [ ] Quality gate passes

## Notes

- Use Pydantic v2 syntax (`model_dump()` not `dict()`)
- Field descriptions appear in OpenAPI docs
- Validators run before data reaches route handler
- Use `| None` for optional fields (not `Optional[]`)
- Follow Google-style docstrings
- Keep models focused — don't create god models
