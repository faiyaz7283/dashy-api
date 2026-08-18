---
name: add-domain
description: Create a complete new domain following Dashy's domain-driven architecture — domain layer, infrastructure adapters, API models, routes, DI wiring, and tests.
---

# Add Domain

Create a complete new domain (like weather, calendar, or family) following Dashy's domain-driven architecture.

## When to use

- Adding a completely new feature area (e.g., shopping lists, chores, rewards)
- Not for adding endpoints to existing domains — use `/add-api-endpoint` instead
- Not for adding new provider implementations — use `/add-provider-adapter` instead

## Prerequisites

- Clear understanding of the domain's business logic
- Identified external integrations (APIs, databases) needed
- API contract defined (what the frontend will consume)

## Steps

### 1. Create domain layer (pure business logic)

Create `app/domain/<domain>/` with three files:

#### models.py — Value objects and entities

```python
"""<Domain> domain models.

Value objects and entities for <domain> business logic.
"""

from dataclasses import dataclass
from enum import Enum


class <Domain>Status(Enum):
    """Status enum docstring."""
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class <Domain>Id:
    """Value object for domain ID."""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("ID cannot be empty")


@dataclass
class <Domain>Entity:
    """Entity docstring."""
    id: <Domain>Id
    name: str
    status: <Domain>Status

    def is_active(self) -> bool:
        """Check if entity is active."""
        return self.status == <Domain>Status.ACTIVE
```

**Rules:**
- Zero framework imports (no FastAPI, httpx, etc.)
- Value objects are immutable (`frozen=True`)
- Entities have identity (ID-based equality)
- Business logic lives here, not in services

#### ports.py — Protocol definitions

```python
"""<Domain> domain ports.

Protocol definitions for <domain> providers and repositories.
"""

from typing import Protocol
from app.domain.<domain>.models import <Domain>Entity


class <Domain>Provider(Protocol):
    """Protocol for <domain> data providers."""

    async def get_data(self, id: str) -> <Domain>Entity:
        """Fetch <domain> data.

        Args:
            id: Entity identifier.

        Returns:
            <Domain>Entity instance.
        """
        ...


class <Domain>Repository(Protocol):
    """Protocol for <domain> persistence."""

    async def get_all(self) -> list[<Domain>Entity]:
        """Retrieve all entities."""
        ...

    async def save(self, entity: <Domain>Entity) -> None:
        """Save entity."""
        ...

    async def delete(self, id: str) -> None:
        """Delete entity."""
        ...
```

**Rules:**
- Use `Protocol` (not ABC) for interfaces
- All methods are `async def`
- Clear docstrings with Args/Returns sections

#### services.py — Use cases

```python
"""<Domain> domain services.

Pure business logic for <domain> operations.
"""

from app.domain.<domain>.models import <Domain>Entity
from app.domain.<domain>.ports import <Domain>Repository


class <Domain>Service:
    """Service for <domain> operations."""

    def __init__(self, repository: <Domain>Repository) -> None:
        """Initialize service.

        Args:
            repository: <Domain> repository instance.
        """
        self.repository = repository

    async def get_active_entities(self) -> list[<Domain>Entity]:
        """Get all active entities.

        Returns:
            List of active <Domain>Entity instances.
        """
        all_entities = await self.repository.get_all()
        return [e for e in all_entities if e.is_active()]
```

**Rules:**
- Pure business logic, no I/O
- Inject dependencies via constructor
- One responsibility per method

### 2. Create infrastructure adapters

Create `app/infrastructure/<domain>/` directory.

#### Provider adapter (if external API)

```python
# app/infrastructure/<domain>/<name>_adapter.py
"""<Name> adapter for <domain> provider."""

import httpx
from app.domain.<domain>.models import <Domain>Entity
from app.infrastructure.<domain>.http_client import get_http_client


class <Name><Domain>Adapter:
    """<Name> implementation of <Domain>Provider."""

    def __init__(self, api_key: str, base_url: str) -> None:
        """Initialize adapter.

        Args:
            api_key: API key for authentication.
            base_url: Base URL for API.
        """
        self.api_key = api_key
        self.base_url = base_url

    async def get_data(self, id: str) -> <Domain>Entity:
        """Fetch data from <Name> API.

        Args:
            id: Entity identifier.

        Returns:
            <Domain>Entity instance.
        """
        client = get_http_client()
        response = await client.get(
            f"{self.base_url}/data/{id}",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        response.raise_for_status()
        return self._parse_response(response.json())

    def _parse_response(self, data: dict) -> <Domain>Entity:
        """Parse API response to domain entity."""
        # Parsing logic here
        pass
```

#### Mock adapter

```python
# app/infrastructure/<domain>/mock_adapter.py
"""Mock adapter for <domain> provider."""

from app.domain.<domain>.models import <Domain>Entity, <Domain>Id, <Domain>Status


class Mock<Domain>Adapter:
    """Mock implementation of <Domain>Provider."""

    async def get_data(self, id: str) -> <Domain>Entity:
        """Return mock data.

        Args:
            id: Entity identifier.

        Returns:
            Mock <Domain>Entity instance.
        """
        return <Domain>Entity(
            id=<Domain>Id(value=id),
            name=f"Mock {id}",
            status=<Domain>Status.ACTIVE
        )
```

#### HTTP client (if needed)

```python
# app/infrastructure/<domain>/http_client.py
"""Shared HTTP client for <domain> adapters."""

import httpx
from functools import lru_cache


@lru_cache()
def get_http_client() -> httpx.AsyncClient:
    """Get shared async HTTP client.

    Returns:
        httpx.AsyncClient with connection pooling.
    """
    return httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_connections=10)
    )
```

### 3. Create repository (if persistence needed)

See `/add-repository` skill for detailed workflow.

### 4. Create API models

Create `app/api/models/<domain>.py`:

```python
"""<Domain> API models.

Request and response models for <domain> endpoints.
"""

from pydantic import BaseModel, Field


class <Domain>Response(BaseModel):
    """Response model for <domain> data."""

    id: str = Field(description="Entity identifier")
    name: str = Field(description="Entity name")
    status: str = Field(description="Entity status")

    @classmethod
    def from_entity(cls, entity: "<Domain>Entity") -> "<Domain>Response":
        """Create response from domain entity.

        Args:
            entity: Domain entity instance.

        Returns:
            <Domain>Response instance.
        """
        return cls(
            id=entity.id.value,
            name=entity.name,
            status=entity.status.value
        )
```

Update `app/api/models/__init__.py` to export the new model.

### 5. Create API routes

Create `app/api/routes/<domain>.py`:

```python
"""<Domain> API routes.

Endpoints for <domain> operations.
"""

from fastapi import APIRouter, Depends
from app.api.deps import <Domain>ProviderDep
from app.api.models.<domain> import <Domain>Response

router = APIRouter(prefix="/<domain>", tags=["<domain>"])


@router.get("/{id}", response_model=<Domain>Response)
async def get_<domain>(
    id: str,
    provider: <Domain>ProviderDep,
) -> <Domain>Response:
    """Get <domain> data by ID.

    Args:
        id: Entity identifier.
        provider: Injected <domain> provider.

    Returns:
        <Domain>Response with entity data.
    """
    entity = await provider.get_data(id)
    return <Domain>Response.from_entity(entity)
```

### 6. Wire up DI container

Add to `app/core/container.py`:

```python
from functools import lru_cache
from app.config import settings
from app.domain.<domain>.ports import <Domain>Provider
from app.infrastructure.<domain>.mock_adapter import Mock<Domain>Adapter
from app.infrastructure.<domain>.<name>_adapter import <Name><Domain>Adapter


@lru_cache
def get_<domain>_provider() -> <Domain>Provider:
    """Get <domain> provider based on configuration.

    Returns:
        <Domain>Provider instance.
    """
    if settings.<DOMAIN>_USE_MOCK:
        return Mock<Domain>Adapter()
    return <Name><Domain>Adapter(
        api_key=settings.<DOMAIN>_API_KEY,
        base_url=settings.<DOMAIN>_BASE_URL
    )
```

Add to `app/api/deps.py`:

```python
from typing import Annotated
from fastapi import Depends
from app.core.container import get_<domain>_provider
from app.domain.<domain>.ports import <Domain>Provider

<Domain>ProviderDep = Annotated[<Domain>Provider, Depends(get_<domain>_provider)]
```

### 7. Register route

In `app/main.py`:

```python
from app.api.routes import <domain>

app.include_router(<domain>.router, prefix="/api/v1")
```

### 8. Add configuration

In `app/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings

    # <Domain> settings
    <DOMAIN>_USE_MOCK: bool = True
    <DOMAIN>_API_KEY: str = ""
    <DOMAIN>_BASE_URL: str = "https://api.example.com"
```

Update `.env.example` and `.env.test` with new variables.

### 9. Add tests

Create tests following three-tier strategy:

- `tests/unit/domain/test_<domain>_models.py` — value object tests
- `tests/unit/domain/test_<domain>_services.py` — service tests with mocked repo
- `tests/integration/test_<name>_adapter.py` — adapter tests with pytest-httpx
- `tests/api/test_<domain>_api.py` — endpoint tests

See `/add-backend-test` skill for detailed patterns.

### 10. Update registry

Add to `app/core/registry.py`:

```python
class ProviderRegistry:
    # ... existing methods

    @staticmethod
    def get_<domain>_provider():
        """Get the registered <domain> provider."""
        return get_<domain>_provider()
```

### 11. Run quality gate

```bash
uv run ruff check app/ tests/ && uv run python -m compileall app/ && uv run pytest tests/ -v
```

### 12. Update documentation

- Add domain to `README.md` architecture section
- Add API endpoint to API documentation

## Checklist

- [ ] Domain layer created (models, ports, services)
- [ ] Infrastructure adapters created (provider + mock)
- [ ] Repository created (if persistence needed)
- [ ] API models created (request/response)
- [ ] API routes created
- [ ] DI container wired
- [ ] Configuration added
- [ ] Tests created (unit, integration, API)
- [ ] Registry updated
- [ ] Quality gate passes
- [ ] Documentation updated

## Example: Adding "shopping lists" domain

Following this skill to add a shopping lists domain:

1. `app/domain/lists/` — models (ListItem, ShoppingList), ports (ListProvider, ListRepository), services (ListService)
2. `app/infrastructure/lists/` — mock_adapter (no external API needed initially)
3. `app/infrastructure/persistence/list_repository.py` — SQLite-backed repository
4. `app/api/models/lists.py` — ListResponse, CreateListRequest
5. `app/api/routes/lists.py` — GET/POST/PUT/DELETE endpoints
6. Wire DI container, add config, register routes
7. Tests for all layers
8. Quality gate passes

## Notes

- This is a large skill — consider breaking into smaller tasks if needed
- Domain layer should have zero framework imports
- All infrastructure methods must be `async def`
- Use Protocol for interfaces, not ABC
- Follow Google-style docstrings everywhere
