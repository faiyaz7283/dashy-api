---
name: code-review-gate
description: Manual code review before running automated quality gates. Check for pattern violations, code quality, and AGENTS.md compliance.
---

# Code Review Gate

Perform a manual code review **before running automated quality gates** (lint/test/build). This catches issues that automated tools miss.

## When to use

- Automatically invoked by `/quality-gate` (step 0)
- Can also be run standalone after completing implementation
- After running `/self-review`
- Before presenting code to the user

## Code Review Checklist

### 1. Re-read AGENTS.md Sections

Review the sections relevant to your change:

- [ ] **Section 4: Code style** — Google-style docstrings, naming conventions
- [ ] **Section 7: Universal coding standards** — Documentation, readable code, naming
- [ ] **Section 8: Testing** — Three-tier strategy, test isolation
- [ ] **Orchestrator Section 2: Docker-first** — No local package management

Read detailed guides if needed:
- `AGENTS.md` — Backend-specific rules
- `../AGENTS.md` — Orchestrator rules (Docker-first, git workflow)

### 2. Check for Pattern Violations

#### Hardcoded Values

```bash
# Search for hardcoded member names
grep -r '"faiyaz"' app/ | grep -v test
grep -r '"trisha"' app/ | grep -v test

# Search for hardcoded permissions
grep -r 'adult' app/ | grep -v test
grep -r 'is_adult' app/ | grep -v test

# Search for hardcoded numbers
grep -r '== [0-9]' app/ | grep -v test
grep -r '>= [0-9]' app/ | grep -v test
```

- [ ] No hardcoded member names — all data from database
- [ ] No hardcoded permissions or age checks
- [ ] No magic numbers — use named constants
- [ ] No hardcoded strings — use configuration

#### Domain/Infrastructure Separation

```bash
# Check for framework imports in domain layer
grep -r 'from fastapi' app/domain/
grep -r 'from sqlmodel' app/domain/
grep -r 'import httpx' app/domain/
```

- [ ] Domain layer has zero framework imports
- [ ] Domain models are pure Python (dataclasses, enums)
- [ ] Domain services use Protocol interfaces
- [ ] Infrastructure implements domain protocols

#### DRY Principle

```bash
# Look for duplicated patterns
grep -r 'def calculate_' app/domain/ | sort
grep -r 'def validate_' app/domain/ | sort
grep -r 'def generate_' app/domain/ | sort
```

- [ ] Is the code DRY (Don't Repeat Yourself)?
- [ ] Are there opportunities to extract common patterns?
- [ ] Check `app/utils/` for existing utilities
- [ ] Check `app/domain/<domain>/utils.py` for domain utilities

#### Single Source of Truth

```bash
# Check for duplicated logic
grep -r 'calculate_period' app/
grep -r 'evaluate_condition' app/
```

- [ ] Period calculation in one place (`app/domain/<domain>/utils/periods.py`)
- [ ] Condition evaluation in one place (`app/domain/<domain>/services/condition_evaluator.py`)
- [ ] Instance generation in one method (`ChoresService.generate_instance_for_association()`)
- [ ] Status transitions in one method (`ChoresService.update_instance_status()`)

### 3. Check for Code Quality

#### Google-Style Docstrings

```bash
# Check for missing docstrings
grep -r '^def ' app/ | grep -v test | grep -v '__' | head -20
grep -r '^class ' app/ | grep -v test | head -20
```

- [ ] Every public module has a module docstring
- [ ] Every public class has a class docstring
- [ ] Every public function/method has Args, Returns, Raises (if applicable)
- [ ] Docstrings follow Google style (not reST, not NumPy)

#### Naming Conventions

```bash
# Check for non-snake_case
grep -r 'def [a-zA-Z]*[A-Z]' app/ | grep -v test
grep -r 'class [a-z]' app/ | grep -v test
```

- [ ] Files: `snake_case.py`
- [ ] Classes: `PascalCase`
- [ ] Functions/methods: `snake_case`
- [ ] Variables: `snake_case`
- [ ] Constants: `UPPER_SNAKE_CASE`
- [ ] No abbreviations (except: id, url, api, tz)
- [ ] Descriptive names (no `data`, `info`, `result` without context)

#### Error Handling

```bash
# Check for proper error responses
grep -r 'raise HTTPException' app/api/
grep -r 'except:' app/ | grep -v test
```

- [ ] API errors use RFC 9457 format
- [ ] Domain errors raise appropriate exceptions
- [ ] No bare `except:` clauses
- [ ] Infrastructure errors converted to domain exceptions

#### REST Compliance

```bash
# Check for verbs in URLs
grep -r '@router\.' app/api/routes/
```

- [ ] Resources are nouns (not verbs)
- [ ] HTTP methods indicate action
- [ ] No verbs in URLs (no `/approve`, `/complete`)
- [ ] Proper status codes (201, 204, 404)
- [ ] PATCH for partial updates

### 4. Check for Test Coverage

```bash
# Check for test files
find tests/ -name "*.py" -newer app/ | head -20
```

- [ ] New domain logic has unit tests
- [ ] New repository methods have integration tests
- [ ] New API endpoints have API tests
- [ ] Tests follow three-tier strategy
- [ ] Test isolation maintained (tests use `dashy_test` database)
- [ ] Edge cases covered (boundaries, empty inputs, error conditions)

### 5. Check for Magic Numbers/Strings

```bash
# Search for magic numbers
grep -r 'sleep([0-9]' app/ | grep -v test
grep -r 'timeout=[0-9]' app/ | grep -v test
```

- [ ] Use named constants for magic numbers
- [ ] Use configuration for timeouts, retries, limits
- [ ] Use environment variables for environment-specific values

### 6. Fix Violations

If violations are found, **fix them before proceeding to quality gates**.

Common fixes:
- **Hardcoded values** → Use configuration, database, or environment variables
- **Missing docstrings** → Add Google-style docstrings
- **Duplicated logic** → Extract to utility function
- **Framework imports in domain** → Move to infrastructure layer
- **Non-snake_case** → Rename to follow conventions
- **Missing tests** → Add appropriate test tier
- **Magic numbers** → Use named constants
- **Verbs in URLs** → Refactor to RESTful resources

### 7. Verify Fixes

After fixing violations:

```bash
# Re-run the checks
grep -r '"faiyaz"' app/ | grep -v test
grep -r 'from fastapi' app/domain/
grep -r 'def [a-zA-Z]*[A-Z]' app/ | grep -v test
```

- [ ] All violations fixed
- [ ] No new violations introduced

## After Code Review

When invoked standalone:
1. Run `/quality-gate` for automated checks (which will re-invoke this skill)
2. Present code to user

When invoked by `/quality-gate`:
- Continue to the automated checks (lint, test, build)

## Notes

- This is a **manual review** — automated tools can't catch everything
- Automatically invoked by `/quality-gate` (step 0)
- Can also be run standalone after `/self-review`
- If violations are found, they are part of the current phase — do not defer
- All commands run inside Docker containers via Makefile targets
