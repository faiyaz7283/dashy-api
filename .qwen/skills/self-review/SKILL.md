---
name: self-review
description: Run this checklist before presenting code to the user. Self-review against AGENTS.md rules to catch violations before they're seen.
---

# Self-Review Checklist

Run this checklist **before presenting code to the user**. This is your responsibility — do not wait for the user to catch violations.

## When to use

- After completing implementation
- Before presenting code to the user
- Before running quality gates
- After making significant changes

## Checklist

### 1. Re-read Relevant AGENTS.md Sections

- [ ] Section 4: Code style (Google-style docstrings, naming conventions)
- [ ] Section 7: Universal coding standards (documentation, readable code, naming)
- [ ] Section 8: Testing (three-tier strategy, test isolation)
- [ ] Orchestrator AGENTS.md Section 2: Docker-first development

### 2. Search for Hardcoded Values

```bash
# Search for hardcoded member names
grep -r '"faiyaz"' app/
grep -r '"trisha"' app/
grep -r '"admin"' app/

# Search for hardcoded permissions/ages
grep -r 'adult' app/
grep -r 'is_adult' app/
grep -r 'age' app/

# Search for hardcoded numbers (except in tests)
grep -r '== [0-9]' app/ | grep -v test
grep -r '>= [0-9]' app/ | grep -v test
```

- [ ] No hardcoded member names — all data comes from database
- [ ] No hardcoded permissions or age checks
- [ ] No magic numbers — use named constants
- [ ] No hardcoded strings — use configuration or database

### 3. Verify Google-Style Docstrings

```bash
# Check for missing docstrings on public functions/classes
grep -r '^def ' app/ | grep -v test | grep -v '__'
grep -r '^class ' app/ | grep -v test
```

- [ ] Every public module has a module docstring
- [ ] Every public class has a class docstring
- [ ] Every public function/method has a docstring with Args, Returns, Raises (if applicable)
- [ ] Docstrings follow Google style (not reST, not NumPy)
- [ ] Private helpers have docstrings when logic is non-obvious

### 4. Verify DRY Principle

```bash
# Search for duplicated logic patterns
grep -r 'def calculate_' app/domain/
grep -r 'def validate_' app/domain/
grep -r 'def generate_' app/domain/
```

- [ ] If the same logic appears in 2+ places → Extract to utility function
- [ ] Check `app/utils/` for existing utilities
- [ ] Check `app/domain/<domain>/utils.py` for domain-specific utilities
- [ ] No copy-pasted code blocks

### 5. Verify Domain/Infrastructure Separation

```bash
# Check for framework imports in domain layer
grep -r 'from fastapi' app/domain/
grep -r 'from sqlmodel' app/domain/
grep -r 'import httpx' app/domain/
grep -r 'import redis' app/domain/
```

- [ ] Domain layer (`app/domain/`) has zero framework imports
- [ ] Domain models are pure Python (dataclasses, enums)
- [ ] Domain services use Protocol interfaces, not concrete implementations
- [ ] Infrastructure adapters (`app/infrastructure/`) implement domain protocols

### 6. Verify Error Handling

```bash
# Check for proper error responses
grep -r 'raise HTTPException' app/api/
grep -r 'raise ValueError' app/domain/
```

- [ ] API errors use RFC 9457 format (via `app/core/errors.py`)
- [ ] Domain errors raise appropriate exceptions (ValueError, TypeError, custom exceptions)
- [ ] Infrastructure errors are caught and converted to domain exceptions
- [ ] No bare `except:` clauses

### 7. Verify Naming Conventions

```bash
# Check for non-snake_case in Python files
grep -r 'def [a-zA-Z]*[A-Z]' app/ | grep -v test
grep -r 'class [a-z]' app/ | grep -v test
```

- [ ] Files: `snake_case.py`
- [ ] Classes: `PascalCase`
- [ ] Functions/methods: `snake_case`
- [ ] Variables: `snake_case`
- [ ] Constants: `UPPER_SNAKE_CASE`
- [ ] No abbreviations (except universally understood: id, url, api, tz)
- [ ] No single-letter variables (except loop indices: i, j)

### 8. Verify Test Coverage

```bash
# Check for test files
find tests/ -name "*.py" | grep -E "(test_|_test\.py)"
```

- [ ] New domain logic has unit tests (`tests/unit/`)
- [ ] New repository methods have integration tests (`tests/integration/`)
- [ ] New API endpoints have API tests (`tests/api/`)
- [ ] Tests follow three-tier strategy (unit, integration, API)
- [ ] Test isolation maintained (tests use `test.db`, not `dashy.db`)
- [ ] No tests modify the development database

### 9. Check for Magic Numbers/Strings

```bash
# Search for magic numbers
grep -r 'sleep([0-9]' app/ | grep -v test
grep -r 'timeout=[0-9]' app/ | grep -v test
grep -r 'max_retries=[0-9]' app/ | grep -v test
```

- [ ] Use named constants for magic numbers
- [ ] Use configuration for timeouts, retries, limits
- [ ] Use environment variables for environment-specific values

### 10. Verify REST Compliance

```bash
# Check for verbs in URLs
grep -r '@router\.' app/api/routes/
```

- [ ] Resources are nouns (not verbs)
- [ ] HTTP methods indicate action (GET=read, POST=create, PATCH=update, DELETE=remove)
- [ ] No verbs in URLs (no `/approve`, `/complete`, `/claim`)
- [ ] Proper status codes (201 Created, 204 No Content, 404 Not Found)
- [ ] PATCH for partial updates (not PUT for everything)

## If Violations Found

**Fix them before presenting the code.** Do not present code with known violations.

Common fixes:
- Hardcoded values → Use configuration, database, or environment variables
- Missing docstrings → Add Google-style docstrings
- Duplicated logic → Extract to utility function
- Framework imports in domain → Move to infrastructure layer
- Non-snake_case → Rename to follow conventions
- Missing tests → Add appropriate test tier
- Magic numbers → Use named constants
- Verbs in URLs → Refactor to RESTful resources

## After Self-Review

1. Run `/quality-gate` (which includes code review + automated checks)
2. Present code to user

## Notes

- This checklist is **mandatory** before presenting code
- Run after completing implementation
- Run before `/quality-gate`
- All commands run inside Docker containers via Makefile targets
