---
name: quality-gate
description: Run the backend quality gate — lint, typecheck, test, build
---

# Backend Quality Gate

Run the full backend quality gate. All steps must pass before declaring any change complete.

## Steps

### 1. Lint

```bash
make lint-api
```

Checks for errors, style issues, and import problems. Auto-fix what's possible:

```bash
make format-api
```

### 2. Typecheck (compile check)

```bash
make build-api
```

Verifies all Python files compile without syntax errors.

### 3. Test

```bash
make test-api
```

Runs all tests (unit, integration, API) with verbose output.

## Quick one-liner

Run all three steps in sequence:

```bash
make lint-api && make build-api && make test-api
```

## Notes

- All commands run inside Docker containers via Makefile targets — ensure the dev environment is up (`make dev-up`)
- Fix lint issues before running tests
- Integration tests require Redis to be running (via Docker Compose in the orchestrator)
- If integration tests fail due to Redis, ensure the dev environment is up
