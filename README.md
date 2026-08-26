# Dashy API

Backend API for the Dashy Family Calendar Dashboard.

## Overview

Dashy API provides REST endpoints for weather data, calendar events, family member management, and chore tracking. Built with FastAPI, designed for the Dashy kiosk display system.

## Tech Stack

- **Framework:** FastAPI
- **Python:** 3.13+
- **Package Manager:** UV
- **Database:** PostgreSQL (via SQLModel + Alembic)
- **Cache:** Redis
- **Testing:** pytest + pytest-asyncio + pytest-httpx
- **Linting:** Ruff

## API Endpoints

```
GET /api/v1/weather?units=imperial     → WeatherResponse
GET /api/v1/calendar?start_date=...&end_date=...  → WeekCalendar
GET /api/v1/family                     → FamilyMember[]
GET /api/v1/chores/masters             → ChoreMaster[]
GET /api/v1/chores/instances           → ChoreInstance[]
GET /api/v1/chores/categories          → ChoreCategory[]
POST /api/v1/chores/instances/{id}/complete → ChoreInstance
GET /health                            → { status, version, cache }
```

Interactive API docs available at `/docs` when running.

## Development

This repo is designed to run as part of the Dashy orchestrator (docker compose). See the [main dashy repo](https://github.com/faiyaz7283/dashy) for full setup instructions.

### Quick Start

```bash
# From the orchestrator repo (dashy/)
make dev-up  # Automatically applies database migrations

# API docs: https://api.dashy.local/docs
```

**Important:** All commands inside the API container must use `uv run` prefix to ensure the correct Python environment:

```bash
# Inside container (via docker compose exec or make dev-shell)
uv run pytest
uv run ruff check .
uv run alembic upgrade head
uv run python -c "..."
```

### Standalone Development

If developing outside the orchestrator:

```bash
# Install dependencies
make install

# Run locally (requires Redis and environment variables)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Code Quality

```bash
make lint        # Ruff linting
make format      # Ruff formatting
make typecheck   # Type checking
make test        # Run pytest
make build       # Compile-check all Python
```

## Architecture

```
app/
├── main.py              # FastAPI app entry point
├── core/                # Config, DI container, registry
├── domain/              # Domain models, protocols, value objects
│   ├── weather/         # Weather domain
│   ├── calendar/        # Calendar domain
│   ├── family/          # Family member domain
│   └── chores/          # Chore tracking domain (masters, instances, categories)
├── infrastructure/      # External service adapters (weather, calendar)
├── api/                 # HTTP routes, request/response models
└── registry.py          # Single source of truth for endpoints
```

**Key patterns:**
- **Domain-driven design** — domain layer separate from infrastructure
- **Protocol-based** — Python Protocol for provider interfaces
- **Centralized DI** — FastAPI Depends() + @lru_cache
- **Fail-open cache** — cache failures never break the app
- **RFC 9457 errors** — standard error format

## Environment Variables

See `env/.env.dev.example` in the orchestrator repo for required variables:

- `GOOGLE_SERVICE_ACCOUNT_JSON` — Google Calendar service account
- `OPENWEATHERMAP_API_KEY` — Weather API key
- `OPENWEATHERMAP_LAT`, `OPENWEATHERMAP_LON` — Location coordinates
- `REDIS_URL` — Redis connection string
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — PostgreSQL connection
- `POSTGRES_HOST`, `POSTGRES_PORT` — PostgreSQL host/port (defaults: `postgres`, `5432`)
- `CORS_ORIGINS` — Allowed CORS origins
- `CHORES_USE_MOCK` — Use mock chore repository (true/false)

## Database Architecture

**Development:** PostgreSQL database via Docker service `postgres:18-alpine`, connection configured via `POSTGRES_*` env vars. Data persists on `postgres-data` volume (not git-tracked).

**Production:** Separate PostgreSQL database on Pi's Docker volume, configured via `POSTGRES_*` env vars in production `.env`.

**Testing:** Tests use the same PostgreSQL instance but connect to a separate `dashy_test` database configured in `.env.test`.

**Migrations:** Alembic manages schema changes with async PostgreSQL support. Migrations run automatically on `make dev-up` via `entrypoint.sh` (which waits for PostgreSQL readiness). Manual migration commands:

```bash
make migrate              # Apply pending migrations
make migrate-status       # Show current migration status
make migrate-check        # Check if migrations are pending
make migrate-rollback     # Rollback last migration
make migrate-create MESSAGE="description"  # Generate new migration
```

## Testing

**Test isolation:** Tests use a separate PostgreSQL database (`dashy_test`) configured via `POSTGRES_*` env vars in `.env.test`. The `tests/conftest.py` sets up the test database and handles table cleanup between tests.

```bash
# Run all tests
make test

# Run specific test tiers
uv run pytest tests/ -m unit          # Unit tests (no I/O)
uv run pytest tests/ -m integration   # Integration tests (Redis, DB)
uv run pytest tests/ -m api           # API endpoint tests
```

## Deployment

This repo deploys as a Docker container via the orchestrator:

```bash
# From orchestrator repo
make deploy  # Deploys to Raspberry Pi via GitHub Actions
```

## Related Repos

- **[dashy](https://github.com/faiyaz7283/dashy)** — Orchestrator repo (compose, docs, deployment)
- **[dashy-kiosk](https://github.com/faiyaz7283/dashy-kiosk)** — Frontend React app

## License

MIT
