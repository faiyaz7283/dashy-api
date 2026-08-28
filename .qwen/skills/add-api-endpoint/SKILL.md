---
name: add-api-endpoint
description: Step-by-step workflow for adding a new REST API endpoint following Dashy's domain-driven architecture.
---

# Add API Endpoint

Workflow for adding a new REST API endpoint to the Dashy backend.

## Prerequisites

- Understand the domain you're adding the endpoint for (weather, calendar, family, or new domain)
- Check if the domain already exists in `app/domain/<domain>/`
- Review existing endpoints in `app/api/routes/` for patterns

## Steps

### 1. Define the route handler

Create or update `app/api/routes/<domain>.py`:

```python
from fastapi import APIRouter, Depends
from app.api.deps import CacheDep, WeatherProviderDep  # Adjust deps as needed
from app.api.models.<domain> import YourResponseModel

router = APIRouter(prefix="/<domain>", tags=["<domain>"])

@router.get("", response_model=YourResponseModel)
async def get_<domain>(
    provider: ProviderDep,
    cache: CacheDep,
) -> YourResponseModel:
    """Endpoint docstring (Google style)."""
    # Check cache first
    cached = await cache.get(cache_key)
    if cached:
        return YourResponseModel(**cached)

    # Fetch from provider
    result = await provider.get_data()
    await cache.set(cache_key, result.model_dump(), ttl=600)
    return result
```

### 2. Create request/response models

Add to `app/api/models/<domain>.py`:

```python
from pydantic import BaseModel, Field

class YourResponseModel(BaseModel):
    """Response model docstring."""
    field_name: str = Field(description="Field description")
    # ... more fields
```

Update `app/api/models/__init__.py` to export the new model.

### 3. Add dependencies (if needed)

If your endpoint needs a new provider or repository, add it to `app/api/deps.py`:

```python
from app.core.container import get_your_provider
from app.domain.<domain>.ports import YourProvider

YourProviderDep = Annotated[YourProvider, Depends(get_your_provider)]
```

### 4. Register the route

In `app/main.py`, add:

```python
from app.api.routes import <domain>

app.include_router(<domain>.router, prefix="/api/v1")
```

### 5. Add tests

Create `tests/api/test_<domain>_api.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_get_<domain>_returns_200(mock_container):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/<domain>")
        assert response.status_code == 200
        data = response.json()
        # Assert expected fields
```

### 6. Verify OpenAPI docs

Start the server and visit `/docs` to verify:
- Endpoint appears with correct path
- Request/response schemas are accurate
- Description and tags are correct

### 7. Run quality gate

```bash
make lint-api && make build-api && make test-api
```

## Conventions

### REST Compliance

- **HTTP methods**: Use correct methods for their intended purpose
  - `GET` — read-only operations, no side effects (cache writes acceptable)
  - `POST` — create new resources
  - `PATCH` — partial updates (most common for updates)
  - `PUT` — full resource replacement (rarely used)
  - `DELETE` — remove resources
- **URL structure**: `/api/v1/<domain>` (plural nouns, no verbs)
- **Route ordering**: Define fixed paths before parameterized paths (e.g., `/masters/bulk-status` before `/masters/{id}`)
- **Request bodies**: Use request body for mutations, not query parameters
- **Response models**: Always define explicit Pydantic models, don't return raw dicts
- **Error handling**: Raise `DashyError` subclasses or `HTTPException` — both are rendered as RFC 9457 responses
- **Caching**: Use cache for any endpoint that calls external APIs (weather, calendar)
- **Docstrings**: Google style for all functions and classes

### Timezone Handling

- **Timestamps** (created_at, updated_at, started_at, completed_at):
  - Store and transmit in UTC
  - Use `datetime.now(UTC)` for timestamp fields
  - Database columns use `DateTime(timezone=True)`

- **Date/time boundaries** (today, due_time, period calculations):
  - Use configured timezone from `settings.tz`
  - Use `datetime.now(settings.tz).date()` for "today"
  - Use `datetime.now(settings.tz).strftime("%H:%M")` for time comparisons
  - Ensures due times and period boundaries match user's local timezone

**Example:**
```python
from app.config import settings
from datetime import UTC, datetime

# Correct: Use configured timezone for date boundaries
today = datetime.now(settings.tz).date()
current_time = datetime.now(settings.tz).strftime("%H:%M")

# Correct: Use UTC for timestamps
created_at = datetime.now(UTC)
```

## Example: Adding a new endpoint to existing domain

If adding `GET /api/v1/weather/hourly` to the weather domain:

1. Add route handler to `app/api/routes/weather.py`
2. Add `HourlyWeatherResponse` model to `app/api/models/weather.py`
3. No new dependencies needed (reuse `WeatherProviderDep`)
4. Route already registered (weather router exists)
5. Add test to `tests/api/test_weather_api.py`
6. Verify docs, run quality gate

## Example: Adding a completely new domain

If adding a new "tasks" domain:

1. Create `app/api/routes/tasks.py` with router
2. Create `app/api/models/tasks.py` with request/response models
3. Add `TasksProviderDep` to `app/api/deps.py` (requires domain + provider to exist)
4. Register tasks router in `app/main.py`
5. Create `tests/api/test_tasks_api.py`
6. Verify docs, run quality gate

**Note:** For a completely new domain, you'll also need to create the domain layer (`app/domain/tasks/`) and provider adapter (`app/infrastructure/tasks/`). See `/add-domain` skill.
