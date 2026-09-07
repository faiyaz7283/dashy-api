# Dashy API Project Skills

This directory contains ECC skills for the Dashy API (FastAPI + Python backend) submodule.

## Directory Structure

```
.agents/
  skills/
    <feature-name>/          # e.g., health-check/, migration-helper/, validation-patterns/
      SKILL.md
      (supporting files)
  README.md                  # This file
```

## Naming Convention

API skills use simple feature names focused on backend patterns. No suffixes are needed—the `.agents/` location makes it clear these are API-specific skills.

## Current Skills

Migrated from the legacy `.qwen/skills/` directory (ECC-formatted, `origin: community`):

- `add-api-endpoint/` — Adding a new REST API endpoint
- `add-api-model/` — Adding Pydantic request/response models
- `add-backend-test/` — Adding unit/integration/API tests
- `add-cache-layer/` — Adding caching to a provider or endpoint
- `add-calendar-source/` — Adding a new calendar data source
- `add-db-migration/` — Creating and applying Alembic migrations
- `add-domain/` — Adding a new domain module (entities, ports, adapters)
- `add-provider-adapter/` — Adding a new infrastructure provider adapter
- `add-repository/` — Adding a new repository for data access
- `add-weather-field/` — Adding a new field to the weather domain
- `code-review-gate/` — Manual code review checklist
- `pre-implementation-checklist/` — Mandatory pre-coding compliance check
- `quality-gate/` — Running lint/test/build gate
- `self-review/` — Self-review checklist before presenting code

## Related Skills

For orchestrator-level skills (deployments, multi-module coordination), see `dashy/.agents/skills/`.
For frontend skills (UI patterns, React conventions), see `dashy-kiosk/.agents/skills/`.

## Skill Format

Each skill is a directory containing:

```
skill-name/
  SKILL.md                   # Markdown with usage instructions
  (optional) examples/       # Python code examples
  (optional) templates/      # Code templates for common patterns
```

## Discovery

Skills are auto-discovered by ECC harnesses:
- **Claude Code:** Native discovery via `.agents/skills/`
- **Kimi Code:** Native discovery via `.agents/skills/`
- **Qwen Code:** Via settings configuration

Invoke skills using your harness's native syntax (e.g., `/skill:<name>` in Kimi Code).

## Adding a New Skill

1. Create a directory under `skills/` with your skill name
2. Add a `SKILL.md` file with:
   - Clear description of the backend pattern or workflow
   - When to use it (e.g., "When validating request data", "When setting up a new domain module")
   - Step-by-step usage instructions with code examples
   - Links to relevant sections in `AGENTS.md` or `README.md`
3. Add Python code examples if demonstrating patterns
4. The skill is immediately discoverable by all harnesses

## Guidelines

- Focus on **backend and API concerns only**
- Document FastAPI patterns (dependency injection, async routes, error handling)
- Document Python patterns (dataclass design, type hints, protocol-based architecture)
- Document database patterns (Alembic migrations, SQLModel relationships, async queries)
- Include code examples—link to real code in the `app/` directory when helpful
- Make skills reusable across different API endpoints and domain modules
- For orchestrator concerns (deployments, CI/CD), add skills to `dashy/.agents/skills/`

## Backend-Specific AGENTS.md Sections

Before creating a skill, check if the pattern is already documented in `AGENTS.md`:
- Domain-driven design (section 5)
- Database architecture (section 5)
- Testing strategy (section 8)
- REST compliance requirements (section 9)

Skills should extend and exemplify these guidelines, not duplicate them.
