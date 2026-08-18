---
name: quality-gate
description: Run the backend quality gate — lint, typecheck, test, build
---

# Backend Quality Gate

Run the full backend quality gate. All steps must pass before declaring any change complete.

## Steps

### 1. Lint

```bash
uv run ruff check app/ tests/
```

Checks for errors, style issues, and import problems. Auto-fix what's possible:

```bash
uv run ruff check app/ tests/ --fix
```

### 2. Typecheck (compile check)

```bash
uv run python -m compileall app/
```

Verifies all Python files compile without syntax errors.

### 3. Test

```bash
uv run pytest tests/ -v
```

Runs all tests (unit, integration, API) with verbose output.

## Quick one-liner

Run all three steps in sequence:

```bash
uv run ruff check app/ tests/ && uv run python -m compileall app/ && uv run pytest tests/ -v
```

## Notes

- This runs natively (no Docker needed) since the backend repo has UV
- Fix lint issues before running tests
- Integration tests require Redis to be running (via Docker Compose in the orchestrator)
- If integration tests fail due to Redis, ensure the dev environment is up
