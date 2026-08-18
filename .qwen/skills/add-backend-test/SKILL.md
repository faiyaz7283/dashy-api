---
name: add-backend-test
description: Workflow for adding backend tests following Dashy's three-tier testing strategy (unit, integration, API).
---

# Add Backend Test

Workflow for adding tests following Dashy's three-tier testing strategy.

## Test tiers

| Tier | Location | Purpose | I/O | Speed |
|------|----------|---------|-----|-------|
| **Unit** | `tests/unit/` | Domain logic, pure functions | None | Fast |
| **Integration** | `tests/integration/` | Real infrastructure (Redis, SQLite) | Real DB/cache | Medium |
| **API** | `tests/api/` | HTTP endpoints via httpx | Full app stack | Slow |

## Prerequisites

- Understand which tier your test belongs to
- Review existing tests for patterns: `tests/conftest.py` for shared fixtures
- pytest config: `asyncio_mode = auto` in `pyproject.toml`

## Step 1: Determine test tier

**Unit test** if:
- Testing pure domain logic (value objects, services with mocked dependencies)
- No database, cache, or external API calls
- Fast execution (<100ms per test)

**Integration test** if:
- Testing repository implementations (real SQLite)
- Testing cache layer (real Redis)
- Testing adapter HTTP calls (mocked with pytest-httpx)

**API test** if:
- Testing HTTP endpoint behavior
- Testing request validation, error responses
- Testing full request/response cycle

## Step 2: Create test file

### Unit test example

```python
# tests/unit/test_weather_models.py
import pytest
from app.domain.weather.models import Temperature, TemperatureUnit

def test_temperature_conversion_celsius_to_fahrenheit():
    """Test temperature conversion logic."""
    temp = Temperature(value=0.0, unit=TemperatureUnit.CELSIUS)
    fahrenheit = temp.to_fahrenheit()

    assert fahrenheit.value == 32.0
    assert fahrenheit.unit == TemperatureUnit.FAHRENHEIT

def test_temperature_equality():
    """Test temperature value object equality."""
    temp1 = Temperature(value=20.0, unit=TemperatureUnit.CELSIUS)
    temp2 = Temperature(value=20.0, unit=TemperatureUnit.CELSIUS)

    assert temp1 == temp2
```

**Rules:**
- No `async` — unit tests are synchronous
- No I/O — no database, cache, or network calls
- Mock dependencies with `unittest.mock.Mock` or `AsyncMock`
- Test one behavior per test function

### Integration test example

```python
# tests/integration/test_family_repository.py
import pytest
from app.infrastructure.persistence.family_repository import FamilyRepositoryImpl
from app.core.database import get_async_session_factory
from app.domain.family.models import FamilyMember

@pytest.mark.asyncio
async def test_family_repository_crud():
    """Test family repository CRUD operations with real SQLite."""
    # Arrange
    async_session_factory = get_async_session_factory()
    async with async_session_factory() as session:
        repo = FamilyRepositoryImpl(session)

        member = FamilyMember(
            id="dad",
            name="Dad",
            calendar_id="dad@example.com",
            color="#0000FF",
            initial="D"
        )

        # Act
        await repo.save(member)
        result = await repo.get_by_id("dad")

        # Assert
        assert result is not None
        assert result.name == "Dad"

        # Cleanup
        await repo.delete("dad")
```

**Rules:**
- Use `@pytest.mark.asyncio` for async tests
- Real infrastructure (SQLite, Redis) — no mocks for the system under test
- Mock external APIs (OWM, Google) with `pytest-httpx`
- Clean up test data after test (or use transactions)

### API test example

```python
# tests/api/test_weather_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app
from app.domain.weather.models import WeatherResponse

@pytest.mark.asyncio
async def test_get_weather_returns_200():
    """Test weather endpoint returns successful response."""
    # Arrange
    mock_provider = AsyncMock()
    mock_provider.get_weather.return_value = WeatherResponse(
        current=...,
        forecast=[]
    )

    with patch("app.api.deps.get_weather_provider", return_value=mock_provider):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Act
            response = await client.get("/api/v1/weather?units=imperial")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "current" in data
            assert "forecast" in data

@pytest.mark.asyncio
async def test_get_weather_invalid_units_returns_422():
    """Test weather endpoint validates query parameters."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/weather?units=invalid")

        assert response.status_code == 422  # Validation error
```

**Rules:**
- Use `httpx.AsyncClient` with `ASGITransport`
- Mock dependencies via `app.dependency_overrides` or `patch()`
- Test both success and error cases
- Verify response status codes and data structure

## Step 3: Use shared fixtures

Check `tests/conftest.py` for reusable fixtures:

```python
# Available fixtures
test_settings          # Test configuration from .env.test
mock_weather_provider  # AsyncMock weather provider
mock_calendar_provider # AsyncMock calendar provider
mock_container         # DI container with mocked providers
```

Add new fixtures to `conftest.py` if they're used across multiple test files.

## Step 4: Run tests

```bash
# Run all tests
make test-api

# Run specific tier
docker compose -f compose/docker-compose.dev.yml exec -T api uv run pytest tests/unit/ -v
docker compose -f compose/docker-compose.dev.yml exec -T api uv run pytest tests/integration/ -v
docker compose -f compose/docker-compose.dev.yml exec -T api uv run pytest tests/api/ -v

# Run specific file
docker compose -f compose/docker-compose.dev.yml exec -T api uv run pytest tests/unit/test_weather_models.py -v

# Run with coverage
docker compose -f compose/docker-compose.dev.yml exec -T api uv run pytest tests/ --cov=app --cov-report=html
```

## Step 5: Run quality gate

```bash
make lint-api && make build-api && make test-api
```

## Test naming conventions

- **File names**: `test_<module>.py` (e.g., `test_weather_models.py`)
- **Function names**: `test_<behavior>` (e.g., `test_temperature_conversion_celsius_to_fahrenheit`)
- **Class names**: `Test<Component>` (e.g., `TestTemperature`)

## Mocking strategy

| What to mock | How | When |
|--------------|-----|------|
| External APIs (OWM, Google) | `pytest-httpx` | Integration tests |
| Repositories | `AsyncMock()` | Unit tests |
| Providers | `AsyncMock()` | Unit tests, API tests |
| Cache | `AsyncMock()` | Unit tests, API tests |
| Database | Real SQLite | Integration tests |
| Redis | Real Redis | Integration tests |

## Common patterns

### Testing async functions

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

### Testing with mocked dependencies

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_service_with_mocked_repo():
    mock_repo = AsyncMock()
    mock_repo.get_all.return_value = [FamilyMember(...)]

    service = FamilyService(repository=mock_repo)
    result = await service.get_all_members()

    assert len(result) == 1
    mock_repo.get_all.assert_called_once()
```

### Testing error handling

```python
@pytest.mark.asyncio
async def test_service_handles_repository_error():
    mock_repo = AsyncMock()
    mock_repo.get_all.side_effect = Exception("DB error")

    service = FamilyService(repository=mock_repo)

    with pytest.raises(Exception, match="DB error"):
        await service.get_all_members()
```

### Testing HTTP mocking with pytest-httpx

```python
@pytest.mark.asyncio
async def test_owm_adapter_parses_response(httpx_mock):
    httpx_mock.add_response(
        url="https://api.openweathermap.org/data/4.0/onecall/current",
        json={"current": {"temp": 22.5}},
    )

    adapter = OWMWeatherAdapter(api_key="test", lat=40.7, lon=-73.5)
    result = await adapter.get_current(units="metric")

    assert result.temperature.value == 22.5
```

## Troubleshooting

**"Event loop is closed"**
- Ensure `asyncio_mode = auto` in `pyproject.toml`
- Use `@pytest.mark.asyncio` on async test functions

**"Fixture not found"**
- Check fixture is defined in `tests/conftest.py` or same file
- Verify fixture name spelling

**Integration tests fail but unit tests pass**
- Ensure Redis is running
- Check database file exists and has correct permissions
- Verify environment variables in `.env.test`

## Coverage goals

- **Domain layer**: 100% coverage (pure logic, easy to test)
- **Infrastructure adapters**: 80%+ coverage (mock external APIs)
- **API routes**: 70%+ coverage (test success + error paths)
- **Overall**: 80%+ coverage

View coverage report:
```bash
docker compose -f compose/docker-compose.dev.yml exec -T api uv run pytest tests/ --cov=app --cov-report=html
# Coverage HTML is generated inside the container; copy it out or use make dev-shell to access
```
