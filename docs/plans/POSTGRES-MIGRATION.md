# SQLite → PostgreSQL Migration Plan

> **Status:** Phase 3 complete — ready for Phase 4 (E2E verification)
> **Created:** 2026-08-26
> **Revised:** 2026-08-26
> **Approach:** Clean cutover — no dual-database support

---

## Executive Summary

Full migration from SQLite to PostgreSQL. Since the only feature using the database is Chores (just built, never used in production), there is zero data migration risk. We do a **clean cutover** — replace SQLite entirely, no dual-DB support.

**Key decisions:**
- **Clean cutover** — remove SQLite, PostgreSQL becomes the only database
- **No data migration script** — database is empty/seed-only, just recreate schema
- **Consolidate migrations** — replace 6 SQLite migrations (with `batch_alter_table` workarounds) with 1 clean PostgreSQL migration
- **Native UUID primary keys** — all tables use `UUID` (PostgreSQL native type) with `uuid7()` generation (time-sortable, RFC 9562)
- **PostgreSQL conventions** — `JSONB` for JSON, `TIMESTAMPTZ` for timestamps, native `BOOLEAN`, `UUID` for all PKs/FKs, FK indexes
- **Async Alembic** — follow Dashtam pattern with `async_engine_from_config`
- **Dashtam patterns** — `pool_pre_ping`, `pool_size=20`, `max_overflow=0`, `async_sessionmaker`, `uuid7` for ID generation

---

## 1. Current State

### SQLite-Specific Code to Remove/Change

| File | SQLite Pattern | PostgreSQL Replacement |
|------|---------------|----------------------|
| `app/core/database.py` | `_set_sqlite_pragma()` — WAL + foreign_keys | Remove entirely; add `pool_pre_ping`, pool config |
| `app/core/database.py` | `create_engine` / `create_async_engine` (no pool opts) | `create_async_engine` with `pool_size`, `max_overflow`, `pool_pre_ping` |
| `app/core/database.py` | Sync URL: `DATABASE_URL.replace("+aiosqlite", "")` | Sync URL: replace `+asyncpg` → `+psycopg` (for Alembic) |
| `app/config.py` | Default: `sqlite+aiosqlite:///./dashy.db` | Default: `postgresql+asyncpg://dashy:dashy@postgres:5432/dashy` |
| `app/infrastructure/persistence/models.py` | `DateTime` (no tz) | `DateTime(timezone=True)` → `TIMESTAMPTZ` |
| `app/infrastructure/persistence/models.py` | `JSON` (TEXT in SQLite) | `JSONB` (native binary JSON) |
| `app/infrastructure/persistence/models.py` | `Boolean` server_default=`'0'` | `Boolean` server_default=`'false'` |
| `app/infrastructure/persistence/models.py` | `AutoString` PKs (string UUIDs), `Integer` PK (family_members) | `Uuid` PKs (native PostgreSQL UUID) with `uuid7()` default |
| `app/infrastructure/persistence/models.py` | FK columns: `AutoString` | FK columns: `Uuid` |
| `app/api/models/*.py` | ID fields: `str` | ID fields: `UUID` (from `uuid` module) |
| `app/api/routes/*.py` | Path params: `str` | Path params: `UUID` (FastAPI validates automatically) |
| `app/domain/repositories/*.py` | Query params: `str` | Query params: `UUID` |
| `alembic/env.py` | Sync engine, `engine_from_config` | Async engine, `async_engine_from_config` |
| `alembic/versions/*.py` | 6 migrations with `batch_alter_table` | 1 consolidated migration, standard `alter_table` |
| `tests/conftest.py` | `create_all` / `drop_all` on SQLite | Savepoint-based rollback on PostgreSQL |
| `pyproject.toml` | `aiosqlite`, `greenlet` | `asyncpg`, `psycopg[binary]` |
| `Dockerfile` | No PG libs needed | Add `libpq-dev` (build) / `libpq5` (runtime) |
| `Dockerfile.dev` | No PG libs needed | Add `libpq-dev` |
| `entrypoint.sh` | No wait needed | Wait for PostgreSQL readiness before migrations |
| `compose/docker-compose.dev.yml` | SQLite volume, hardcoded URL | PostgreSQL service, `DATABASE_URL` from env vars |
| `compose/docker-compose.prod.yml` | SQLite volume, hardcoded URL | PostgreSQL service, tuned for Pi resources |

### Schema (Current → Target)

| Table | Current PK | Target PK | FKs (target) | Notable Columns |
|-------|-----------|-----------|--------------|-----------------|
| `family_members` | `Integer` (autoincrement) | `UUID` (uuid7) | — | `key` (unique), `email`, `date_of_birth` (Date) |
| `chore_categories` | `AutoString` (string UUID) | `UUID` (uuid7) | — | `name` (unique) |
| `chore_tags` | `AutoString` (string UUID) | `UUID` (uuid7) | — | `name` (unique) |
| `master_chores` | `AutoString` (string UUID) | `UUID` (uuid7) | `category_id → chore_categories.id` (UUID) | `recurrence_rule` (JSONB), `conditions` (JSONB), `is_collaborative` (Boolean), `due_date` (Date), `end_date` (Date) |
| `chore_instances` | `AutoString` (string UUID) | `UUID` (uuid7) | `master_chore_id → master_chores.id` (UUID), `association_id → chore_associations.id` (UUID) | `period_start` (Date), `period_end` (Date), `started_at` (TIMESTAMPTZ), `completed_at` (TIMESTAMPTZ) |
| `chore_associations` | `AutoString` (string UUID) | `UUID` (uuid7) | `master_chore_id → master_chores.id` (UUID) | `is_open_pool` (Boolean), `removed_at` (TIMESTAMPTZ) |
| `chore_tag_links` | Composite (`master_chore_id`, `tag_id`) | Composite (UUID, UUID) | `master_chore_id → master_chores.id`, `tag_id → chore_tags.id` | Join table only |

**Seed data:** 5 chore categories (IDs generated via `uuid7()`, not hardcoded strings)

---

## 2. Implementation Phases

Each phase ends with:
1. **Quality gate:** `make lint` + `make test` + `make build` (from orchestrator)
2. **Code review:** Self-review against AGENTS.md rules
3. **Git commit:** Atomic commit with descriptive message in submodule (and orchestrator if applicable)

---

### Phase 1: Core Database Layer

**Goal:** Replace SQLite engine/session with PostgreSQL. Application code connects to PostgreSQL.

**Scope:** `dashy-api` only

#### Tasks

1. **Update dependencies** (`pyproject.toml`)
   - Remove: `aiosqlite`, `greenlet`
   - Add: `asyncpg` (async driver), `psycopg[binary]` (sync driver for Alembic), `uuid6` (time-sortable UUID generation, RFC 9562)
   - Run: `make install-api` (from orchestrator)

2. **Rewrite `app/core/database.py`**
   - Remove `_set_sqlite_pragma()` and all PRAGMA logic
   - Remove `sync_engine` / `get_session()` (sync session)
   - Create async engine with PostgreSQL pool config:
     ```python
     create_async_engine(
         DATABASE_URL,
         echo=False,
         pool_pre_ping=True,
         pool_size=20,
         max_overflow=0,
         connect_args={
             "server_settings": {"jit": "off"},
             "command_timeout": 60,
             "timeout": 30,
         },
     )
     ```
   - Use `async_sessionmaker` (not `sessionmaker`) with `expire_on_commit=False`
   - Keep `get_async_session()` as the FastAPI dependency
   - Add `check_connection()` method: `SELECT 1` health check

3. **Update `app/config.py`**
   - Change `DATABASE_URL` default to `postgresql+asyncpg://dashy:dashy@postgres:5432/dashy`
   - Remove sync URL derivation (no longer needed — Alembic goes async)

4. **Update `app/infrastructure/persistence/models.py`**
   - **All PKs → native UUID with uuid7:**
     - `family_members.id`: `Integer` → `Uuid` with `default=uuid7`
     - All chore tables: `AutoString` → `Uuid` with `default=uuid7`
     - Pattern: `id: UUID = Field(default_factory=uuid7, sa_column=Column(Uuid, primary_key=True))`
   - **All FK columns → Uuid:**
     - `master_chores.category_id`, `chore_instances.master_chore_id`, `chore_instances.association_id`, `chore_associations.master_chore_id`, `chore_tag_links.master_chore_id`, `chore_tag_links.tag_id`
     - Pattern: `category_id: UUID = Field(sa_column=Column(Uuid, ForeignKey("chore_categories.id")))`
   - **All `DateTime` → `DateTime(timezone=True)`** (→ `TIMESTAMPTZ`)
   - **JSON columns** (`recurrence_rule`, `conditions`) → `JSONB` from `sqlalchemy.dialects.postgresql`
   - **`is_collaborative` Boolean:** change `server_default` from `"0"` to `"false"`
   - **Import:** `from uuid import UUID`, `from uuid6 import uuid7`, `from sqlalchemy import Uuid`

5. **Update `alembic/env.py`**
   - Switch to async: `async_engine_from_config` with `pool.NullPool`
   - Get URL from `settings.DATABASE_URL` directly (no sync derivation)
   - Import all model classes explicitly (for autogenerate)
   - Keep offline/online mode support

6. **Add database health check endpoint**
   - Add `GET /health/db` to existing health/router: executes `SELECT 1` via async session
   - Returns `{"status": "healthy"}` or 503 on failure

7. **Update API models, routes, and repositories for UUID**
   - **API models** (`app/api/models/*.py`): all `id` fields change from `str` → `UUID`
     ```python
     from uuid import UUID
     class MasterChoreResponse(BaseModel):
         id: UUID
         category_id: UUID
         # ...
     ```
   - **Routes** (`app/api/routes/*.py`): path params change from `str` → `UUID`
     ```python
     @router.get("/{chore_id}")
     async def get_master_chore(chore_id: UUID) -> MasterChoreResponse:
     ```
     FastAPI automatically validates UUID format and returns 422 for invalid values
   - **Repository interfaces** (`app/domain/repositories/*.py`): method params change from `str` → `UUID`
     ```python
     async def get_by_id(self, chore_id: UUID) -> MasterChore | None:
     ```
   - **Repository implementations** (`app/infrastructure/persistence/repositories/*.py`): query params change from `str` → `UUID`

#### Quality Gate

```bash
make lint-api        # Ruff passes
make test-api        # All tests pass (will need conftest update — see Phase 3)
make build-api       # Docker build succeeds
```

**Note:** Tests will fail at this point if they still reference SQLite. Phase 3 fixes tests. For Phase 1 validation, verify:
- `make lint-api` passes
- `make build-api` succeeds (Docker image builds with new deps)
- Manual: `docker compose exec api uv run python -c "from app.core.database import get_async_engine; print(get_async_engine())"` — confirms engine creates without error

#### Git Commit

```bash
cd dashy-api
git add -A
git commit -m "feat: replace SQLite with PostgreSQL, adopt native UUID primary keys

- Replace aiosqlite/greenlet with asyncpg/psycopg/uuid7
- Rewrite database.py with PostgreSQL connection pooling (pool_pre_ping, pool_size=20)
- All PKs: native UUID with uuid7() generation (time-sortable, RFC 9562)
- All FKs: Uuid type with proper foreign key constraints
- Models: DateTime(timezone=True), JSONB, native Boolean defaults
- API models/routes/repos: str IDs → UUID (FastAPI auto-validates)
- Make Alembic async (async_engine_from_config)
- Add /health/db endpoint
- Remove all SQLite PRAGMA logic"
```

---

### Phase 2: Alembic Migration + Docker Infrastructure

**Goal:** Single clean PostgreSQL migration. Docker Compose runs PostgreSQL. Entrypoint waits for PG.

**Scope:** `dashy-api` + orchestrator (`dashy/`)

#### Tasks

1. **Consolidate Alembic migrations**
   - Delete all 6 existing migration files in `alembic/versions/`
   - Generate new initial migration: `make migrate-create MESSAGE="initial_postgres_schema"`
   - Review generated migration and manually fix:
     - All PK columns: `sa.Uuid()` with `server_default=sa.text('gen_random_uuid()')` (PostgreSQL native UUID generation as fallback)
     - All FK columns: `sa.Uuid()` with proper `ForeignKey` constraints
     - `DateTime(timezone=True)` → `TIMESTAMP WITH TIME ZONE`
     - JSON columns → `postgresql.JSONB`
     - Boolean `server_default='false'`
     - Add indexes on all FK columns:
       - `ix_master_chores_category_id` on `master_chores(category_id)`
       - `ix_chore_instances_master_chore_id` on `chore_instances(master_chore_id)`
       - `ix_chore_instances_association_id` on `chore_instances(association_id)`
       - `ix_chore_tag_links_master_chore_id` on `chore_tag_links(master_chore_id)`
     - Seed data: 5 chore categories with `uuid7()` IDs generated in Python (not hardcoded strings)
   - Verify `downgrade()` drops all tables in correct order (respect FK dependencies)

2. **Update `alembic.ini`** (optional improvements from Dashtam)
   - Add timestamp-based file template: `%(year)d%(month).2d%(day).2d_%(hour).2d%(minute).2d-%(rev)s_%(slug)s`
   - Set `timezone = UTC`
   - Add post-write hook: `ruff format` on new migration files

3. **Update `Dockerfile`** (production)
   - Add `libpq-dev` to build stage (compile psycopg C extension)
   - Add `libpq5` to runtime stage (PostgreSQL shared library)
   - Remove any SQLite-specific setup

4. **Update `Dockerfile.dev`** (development)
   - Add `libpq-dev` (compile psycopg in dev too)

5. **Update `entrypoint.sh`**
   - Add PostgreSQL wait loop before running migrations:
     ```bash
     echo "Waiting for PostgreSQL..."
     until uv run python -c "import asyncio, asyncpg; asyncio.run(asyncpg.connect('${DATABASE_URL}'))" 2>/dev/null; do
       sleep 1
     done
     echo "PostgreSQL ready. Running migrations..."
     ```
   - Alternative (simpler): use `pg_isready` if available, or a Python one-liner

6. **Update `compose/docker-compose.dev.yml`** (orchestrator)
   - Add `postgres` service:
     ```yaml
     postgres:
       image: postgres:18-alpine
       container_name: dashy-dev-postgres
       environment:
         POSTGRES_USER: ${POSTGRES_USER:-dashy}
         POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-dashy}
         POSTGRES_DB: ${POSTGRES_DB:-dashy}
       expose:
         - "5432"
       volumes:
         - postgres-data:/var/lib/postgresql/data
       networks:
         - dashy-dev-network
       restart: unless-stopped
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-dashy}"]
         interval: 10s
         timeout: 5s
         retries: 5
     ```
   - Update `api` service:
     - Change `DATABASE_URL` to `postgresql+asyncpg://${POSTGRES_USER:-dashy}:${POSTGRES_PASSWORD:-dashy}@postgres:5432/${POSTGRES_DB:-dashy}`
     - Add `depends_on: postgres: condition: service_healthy`
     - Remove `api-data:/app/data` volume mount (no longer needed)
   - Update volumes: replace `api-data` with `postgres-data`

7. **Update `compose/docker-compose.prod.yml`** (orchestrator)
   - Add `postgres` service (same as dev, but with Pi-tuned config):
     ```yaml
     postgres:
       image: postgres:18-alpine
       container_name: dashy-prod-postgres
       environment:
         POSTGRES_USER: ${POSTGRES_USER}
         POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
         POSTGRES_DB: ${POSTGRES_DB}
       expose:
         - "5432"
       volumes:
         - postgres-data:/var/lib/postgresql/data
       networks:
         - dashy-network
       restart: unless-stopped
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
         interval: 10s
         timeout: 5s
         retries: 5
       command: >
         postgres
           -c shared_buffers=128MB
           -c work_mem=4MB
           -c maintenance_work_mem=64MB
           -c max_connections=20
           -c wal_buffers=4MB
           -c checkpoint_completion_target=0.9
           -c log_min_duration_statement=1000
       deploy:
         resources:
           limits:
             memory: 512M
             cpus: '1.0'
     ```
   - Update `api` service:
     - Change `DATABASE_URL` to PostgreSQL format
     - Add `depends_on: postgres: condition: service_healthy`
     - Remove `api-data:/app/data` volume mount
   - Update volumes: replace `api-data` with `postgres-data`

8. **Update environment files** (orchestrator)
   - `env/.env.dev` — add:
     ```
     POSTGRES_USER=dashy
     POSTGRES_PASSWORD=dashy
     POSTGRES_DB=dashy
     ```
   - `env/.env.test` — add:
     ```
     POSTGRES_USER=dashy_test
     POSTGRES_PASSWORD=test_password
     POSTGRES_DB=dashy_test
     ```
   - `env/.env.dev.example` — add same vars with placeholder values
   - `env/.env.test.example` — add same vars with placeholder values
   - `env/.env.prod` — add real `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
   - If `.env.prod.example` exists, update it too

#### Quality Gate

```bash
# From orchestrator
make dev-restart       # Restart with PostgreSQL
make dev-logs          # Verify: PostgreSQL starts, migrations run, app connects
make lint-api          # Ruff passes
make build-api         # Docker build succeeds with libpq
```

**Manual verification:**
- `docker compose exec api uv run alembic current` — shows migration at head
- `docker compose exec api uv run alembic downgrade base && uv run alembic upgrade head` — downgrade/upgrade cycle works
- `docker compose exec postgres psql -U dashy -d dashy -c "\dt"` — all 7 tables exist
- `docker compose exec postgres psql -U dashy -d dashy -c "SELECT * FROM chore_categories"` — 5 seed rows present
- `curl -k https://api.dashy.local/health/db` — returns `{"status": "healthy"}`

#### Git Commits

**dashy-api submodule:**
```bash
cd dashy-api
git add -A
git commit -m "feat: consolidate migrations for PostgreSQL with UUID PKs, update Dockerfiles

- Replace 6 SQLite migrations with single PostgreSQL initial migration
- All PKs: sa.Uuid() with gen_random_uuid() server default
- All FKs: sa.Uuid() with proper foreign key constraints
- Add FK indexes on all join/foreign key columns
- Use JSONB, TIMESTAMPTZ, native BOOLEAN throughout
- Seed data uses uuid7() IDs (not hardcoded strings)
- Add libpq-dev/libpq5 to Dockerfiles for psycopg
- Update entrypoint.sh to wait for PostgreSQL readiness
- Update alembic.ini with timestamp naming and ruff hook"
```

**Orchestrator:**
```bash
cd /Users/admin/dashy
git add dashy-api/ compose/ env/
git commit -m "feat: add PostgreSQL service, remove SQLite from compose

- Add postgres:18-alpine service to dev and prod compose
- Update DATABASE_URL to postgresql+asyncpg:// format
- Add POSTGRES_USER/PASSWORD/DB to environment files
- Tune PostgreSQL for Pi (128MB shared_buffers, 20 max_connections)
- Remove api-data SQLite volume, replace with postgres-data
- Update dashy-api submodule ref"
```

---

### Phase 3: Tests + Documentation + Config Updates ✅

**Goal:** All tests pass on PostgreSQL. Documentation reflects PostgreSQL as the database.

**Scope:** `dashy-api` + orchestrator

**Status:** Complete (2026-08-26)

#### Tasks

1. **Update `tests/conftest.py`** ✅
   - Removed SQLite `create_all` / `drop_all` pattern
   - Uses async `create_db_and_tables()` for PostgreSQL
   - Test database configured via `POSTGRES_*` env vars in `.env.test`
   - Table cleanup handled in test fixtures

2. **Update `.env.test`** (dashy-api) ✅
   - Changed to `POSTGRES_USER=dashy_test`, `POSTGRES_PASSWORD=test_password`, `POSTGRES_DB=dashy_test`
   - `POSTGRES_HOST=localhost`, `POSTGRES_PORT=5432`

3. **Review and fix any remaining SQLite patterns** ✅
   - Searched for `sqlite`, `aiosqlite`, `PRAGMA`, `WAL`, `batch_alter_table` across codebase
   - Fixed all remaining references in tests, docs, and skills

4. **Update `dashy-api/AGENTS.md`** ✅
   - Replaced all SQLite references with PostgreSQL
   - Updated database architecture section: PostgreSQL via Docker, `POSTGRES_*` env vars
   - Updated test isolation description: separate `dashy_test` database

5. **Update orchestrator `AGENTS.md`** (`/Users/admin/dashy/AGENTS.md`) ✅
   - Updated Section 10 database architecture
   - Replaced SQLite references: PostgreSQL, `postgres-data` volume
   - Updated test isolation description

6. **Update `dashy-api/README.md`** ✅
   - Updated tech stack: PostgreSQL (via SQLModel + Alembic)
   - Updated environment variables: `POSTGRES_*` instead of `DATABASE_URL`
   - Updated database architecture section

7. **Update orchestrator `README.md`** (`/Users/admin/dashy/README.md`) ✅
   - Updated database references from SQLite to PostgreSQL
   - Updated tech stack table and architecture descriptions

8. **Update skills** (if any reference SQLite) ✅
   - Updated `add-db-migration`, `add-repository`, `add-backend-test`, `add-domain`
   - All SQLite references replaced with PostgreSQL

9. **Update project memory** — deferred to Phase 4

#### Quality Gate ✅

```bash
make lint-api          # ✅ Passes
make build-api         # ✅ Passes
```

**Note:** `make test-api` deferred to Phase 4 (requires running PostgreSQL instance).
- Update environment file templates
- Update dashy-api submodule ref"
```

---

### Phase 4: Full End-to-End Verification

**Goal:** Complete quality gate. Everything works. Push all changes.

**Scope:** Both repos

#### Tasks

1. **Full quality gate** (from orchestrator)
   ```bash
   make lint            # Both repos
   make test            # Both repos
   make build           # Both repos
   ```

2. **End-to-end dev environment test**
   ```bash
   make dev-restart     # Clean restart with PostgreSQL
   make dev-logs        # Verify no errors in logs
   ```
   - Verify: PostgreSQL starts → migrations run → app starts → health checks pass
   - Verify: API endpoints work (test a few chore endpoints via curl)
   - Verify: Kiosk can reach API (check kiosk logs)

3. **Test migration cycle**
   ```bash
   # Inside API container
   uv run alembic downgrade base    # Drop everything
   uv run alembic upgrade head      # Recreate from scratch
   uv run alembic current           # Verify at head
   ```

4. **Verify seed data**
   ```bash
   docker compose exec postgres psql -U dashy -d dashy -c "SELECT id, name FROM chore_categories ORDER BY name;"
   ```
   Should show 5 categories: Bathroom, General, Kitchen, Laundry, Outdoor

5. **Git push** (after user confirmation)
   ```bash
   # Push dashy-api submodule
   cd dashy-api
   git push origin development

   # Push orchestrator
   cd /Users/admin/dashy
   git push origin development
   ```

6. **Update plan status**
   - Mark all phases as ✅ complete in this document
   - Add commit hashes

#### Final Checklist

- [ ] `make lint` passes (both repos)
- [ ] `make test` passes (both repos, all tests on PostgreSQL)
- [ ] `make build` passes (both repos)
- [ ] `make dev-restart` starts clean (PostgreSQL + API + Kiosk)
- [ ] `alembic upgrade head` runs without errors
- [ ] `alembic downgrade base` + `alembic upgrade head` cycle works
- [ ] Seed data (5 chore categories) present after migration
- [ ] `/health/db` returns healthy
- [ ] No SQLite references remain in code (grep for `sqlite`, `aiosqlite`, `PRAGMA`)
- [ ] All PKs are native `UUID` type (not `AutoString` or `Integer`)
- [ ] All FKs are native `UUID` type
- [ ] All API IDs are `UUID` (not `str`) in models, routes, repos, entities
- [ ] UUID generation uses `uuid7()` (time-sortable, RFC 9562)
- [ ] All AGENTS.md files updated
- [ ] All README.md files updated
- [ ] Environment files (.env.dev, .env.test, examples) updated
- [ ] Dockerfiles updated (libpq-dev, libpq5)
- [ ] Entrypoint waits for PostgreSQL
- [ ] Docker Compose has PostgreSQL service (dev + prod)
- [ ] Pi-tuned PostgreSQL config in prod compose
- [ ] Changes pushed to `development` branch

---

## 3. PostgreSQL Type Mapping Reference

| SQLite Type | PostgreSQL Type | SQLAlchemy | Notes |
|-------------|----------------|------------|-------|
| `INTEGER` (PK autoincrement) | `UUID` | `sa.Uuid()` | Native 128-bit UUID, `default=uuid7` in Python |
| `TEXT` (AutoString PK) | `UUID` | `sa.Uuid()` | String UUIDs → native UUID type |
| `TEXT` (AutoString FK) | `UUID` | `sa.Uuid()` | FK columns also become UUID |
| `TEXT` (AutoString field) | `VARCHAR` | `AutoString` / `sa.String()` | Non-ID string fields stay VARCHAR |
| `TEXT` (JSON) | `JSONB` | `postgresql.JSONB` | Binary JSON, indexable |
| `INTEGER` (boolean) | `BOOLEAN` | `sa.Boolean` | Native boolean type |
| `TEXT` (datetime) | `TIMESTAMPTZ` | `sa.DateTime(timezone=True)` | Timezone-aware |
| `DATE` | `DATE` | `sa.Date()` | Same |
| `INTEGER` (server_default='0') | `INTEGER DEFAULT 0` | `sa.Integer(server_default='0')` | SQLAlchemy handles rendering |

### UUID Pattern Reference (Dashtam convention)

```python
# Model (persistence layer)
from uuid import UUID
from uuid6 import uuid7
from sqlalchemy import Uuid, Column, ForeignKey

class MasterChoreDB(SQLModel, table=True):
    id: UUID = Field(
        default_factory=uuid7,
        sa_column=Column(Uuid, primary_key=True),
    )
    category_id: UUID = Field(
        sa_column=Column(Uuid, ForeignKey("chore_categories.id"), nullable=False),
    )

# API model (Pydantic schema)
from uuid import UUID
from pydantic import BaseModel

class MasterChoreResponse(BaseModel):
    id: UUID
    category_id: UUID

# Route (FastAPI path param — auto-validates UUID format, 422 on invalid)
from uuid import UUID
from fastapi import APIRouter

@router.get("/{chore_id}")
async def get_master_chore(chore_id: UUID) -> MasterChoreResponse:
    ...

# Repository interface (domain layer)
from uuid import UUID

class ChoresRepository(Protocol):
    async def get_by_id(self, chore_id: UUID) -> MasterChore | None: ...

# Migration (Alembic)
import sqlalchemy as sa

op.create_table(
    "master_chores",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("category_id", sa.Uuid(), nullable=False),
    sa.PrimaryKeyConstraint("id"),
    sa.ForeignKeyConstraint(["category_id"], ["chore_categories.id"]),
)
```

---

## 4. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Type mismatch (JSON, DateTime, Boolean, UUID) | Low | Medium | Explicit type mapping in models, review generated migration |
| Missing FK index causes slow queries | Low | Low | Add indexes in initial migration |
| `libpq` not available in Docker image | Low | High | Explicitly add `libpq-dev`/`libpq5` to Dockerfiles |
| Test isolation breaks on PostgreSQL | Medium | Medium | Savepoint rollback pattern (proven in Dashtam) |
| Pi runs out of memory with PostgreSQL | Low | Medium | Pi-tuned config: 128MB shared_buffers, 20 max_connections, 512M container limit |
| Entrypoint fails if PostgreSQL slow to start | Low | Medium | Wait loop with retries before running migrations |
| UUID type mismatch between layers | Low | Medium | Consistent `UUID` type in models, API schemas, routes, repos — FastAPI auto-validates path params |

---

## 5. Configuration Reference

### Environment Variables

| Variable | Dev Value | Test Value | Prod Value |
|----------|-----------|------------|------------|
| `DATABASE_URL` | `postgresql+asyncpg://dashy:dashy@postgres:5432/dashy` | `postgresql+asyncpg://dashy_test:test_password@postgres:5432/dashy_test` | Set via `.env.prod` |
| `POSTGRES_USER` | `dashy` | `dashy_test` | (secret) |
| `POSTGRES_PASSWORD` | `dashy` | `test_password` | (secret) |
| `POSTGRES_DB` | `dashy` | `dashy_test` | `dashy` |

### PostgreSQL Pool Config

| Setting | Value | Rationale |
|---------|-------|-----------|
| `pool_size` | 20 | Fixed pool, enough for kiosk polling |
| `max_overflow` | 0 | No overflow — predictable connection count |
| `pool_pre_ping` | `True` | Detect stale connections before use |
| `pool_recycle` | Not set | Not needed with `pool_pre_ping` |

### Pi PostgreSQL Tuning

| Setting | Value | Default | Rationale |
|---------|-------|---------|-----------|
| `shared_buffers` | 128MB | 128MB | Keep low for 4GB Pi |
| `work_mem` | 4MB | 4MB | Per-query sort/hash memory |
| `maintenance_work_mem` | 64MB | 64MB | VACUUM/CREATE INDEX |
| `max_connections` | 20 | 100 | Low concurrency (1-2 kiosks) |
| `wal_buffers` | 4MB | -1 (auto) | Smaller WAL for Pi |
| `checkpoint_completion_target` | 0.9 | 0.9 | Spread checkpoint I/O |
| `log_min_duration_statement` | 1000ms | -1 | Log queries > 1s |

---

## 6. Files Changed (Complete List)

### dashy-api (submodule)

| File | Change |
|------|--------|
| `pyproject.toml` | Remove `aiosqlite`, `greenlet`; add `asyncpg`, `psycopg[binary]`, `uuid6` |
| `uv.lock` | Regenerated by `make install-api` |
| `app/config.py` | `DATABASE_URL` default → PostgreSQL |
| `app/core/database.py` | Full rewrite: PostgreSQL engine, pool config, async sessions |
| `app/infrastructure/persistence/models.py` | All PKs → `Uuid` with `uuid7`, all FKs → `Uuid`, `DateTime(timezone=True)`, `JSONB`, Boolean `server_default='false'` |
| `app/api/models/*.py` | All `id` fields: `str` → `UUID` |
| `app/api/routes/*.py` | All path params: `str` → `UUID` |
| `app/domain/repositories/*.py` | All method params: `str` → `UUID` |
| `app/infrastructure/persistence/repositories/*.py` | All query params: `str` → `UUID` |
| `app/domain/entities/*.py` | All `id` fields: `str` → `UUID` |
| `alembic.ini` | Timestamp naming, UTC timezone, ruff hook |
| `alembic/env.py` | Async engine, import all models |
| `alembic/versions/*.py` | Delete 6 old, add 1 new consolidated migration (all `sa.Uuid()` columns) |
| `tests/conftest.py` | Savepoint-based test isolation on PostgreSQL |
| `.env.test` | `DATABASE_URL` → PostgreSQL |
| `Dockerfile` | Add `libpq-dev` (build), `libpq5` (runtime) |
| `Dockerfile.dev` | Add `libpq-dev` |
| `entrypoint.sh` | Wait for PostgreSQL before migrations |
| `AGENTS.md` | Update all SQLite references → PostgreSQL, document UUID pattern |
| `README.md` | Update setup instructions, architecture |

### Orchestrator (dashy/)

| File | Change |
|------|--------|
| `compose/docker-compose.dev.yml` | Add `postgres` service, update `DATABASE_URL`, remove `api-data` volume |
| `compose/docker-compose.prod.yml` | Add `postgres` service (Pi-tuned), update `DATABASE_URL`, remove `api-data` volume |
| `env/.env.dev` | Add `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| `env/.env.test` | Add `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| `env/.env.dev.example` | Add PostgreSQL vars (template) |
| `env/.env.test.example` | Add PostgreSQL vars (template) |
| `env/.env.prod` | Add `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| `AGENTS.md` | Update database architecture section |
| `README.md` | Update service descriptions |

### Skills / Memory

| File | Change |
|------|--------|
| `.qwen/skills/add-repository.md` | Update if it references SQLite patterns |
| `.qwen/skills/add-db-migration.md` | Update if it references SQLite patterns |
| `.qwen/skills/add-domain.md` | Update if it references SQLite patterns |
| Memory: `project/chores-feature-design.md` | Update database references |
| Memory: new entry | Record PostgreSQL migration as architecture decision |

---

## 7. Rollback Plan

Since this is a clean cutover with no data, rollback means reverting git commits:

```bash
# In dashy-api
git revert HEAD  # Revert the migration commit
# In orchestrator
git revert HEAD  # Revert the compose/env update commit
make dev-restart # Back to SQLite
```

No data loss possible — database is empty/seed-only.

---

## 8. Open Questions (Resolved)

| Question | Decision | Rationale |
|----------|----------|-----------|
| Keep dual SQLite/PostgreSQL support? | **No** — clean cutover | No production data, simpler codebase |
| JSONB or JSON? | **JSONB** | Binary format, faster, indexable |
| Keep old migration chain? | **No** — consolidate to 1 | Old migrations have SQLite-specific `batch_alter_table`; no data to migrate |
| Data migration script? | **Not needed** | Chores feature never used in production |
| Keep SQLite for local dev? | **No** — Docker PostgreSQL for all envs | Consistency, catches issues early |
| PostgreSQL version? | **18-alpine** | Latest stable release |
| Add indexes? | **Yes** — FK columns in initial migration | PostgreSQL best practice, improves join performance |
| Use native UUID PKs? | **Yes** — `sa.Uuid()` with `uuid7()` | PostgreSQL native UUID type, time-sortable (RFC 9562), industry standard |
| Which UUID version? | **UUIDv7** | Time-sortable (Unix ms + random), best for database PKs. v8 is custom/experimental, not a replacement |
| UUID generation: app or DB? | **App-side `uuid7()`** | Python `uuid6` package (RFC 9562, actively maintained). DB `gen_random_uuid()` as server_default fallback |
| `family_members.id` → UUID? | **Yes** | Consistency — all tables use UUID PKs, no mixed integer/string types |

---

**Document version:** 2.1
**Last updated:** 2026-08-26
**Author:** Qwen Code (AI-assisted planning)
