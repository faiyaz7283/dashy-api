---
name: pre-implementation-checklist
description: Run this checklist before writing any implementation code to catch violations early. Preventive, not detective.
---

# Pre-Implementation Checklist

Run this checklist **before writing any implementation code**. This is preventive — catch violations before they happen.

## When to use

- Before starting any new feature implementation
- Before adding new endpoints, services, or models
- Before modifying existing code with architectural implications
- After planning, before coding

## Checklist

### 1. AGENTS.md Compliance

- [ ] Read relevant sections of AGENTS.md:
  - Section 4: Code style (Google-style docstrings, naming)
  - Section 7: Universal coding standards
  - Section 8: Testing (three-tier strategy)
- [ ] Read orchestrator AGENTS.md Section 2: Docker-first development
- [ ] Understand the domain's business logic and data flow

### 2. Duplication Check

```bash
# Search for existing services, utilities, patterns
grep -r 'def calculate_' app/domain/
grep -r 'def validate_' app/domain/
grep -r 'def generate_' app/domain/
ls app/utils/
ls app/domain/<domain>/utils/
```

- [ ] If duplicating logic → Extract to utility function instead
- [ ] Check `app/utils/` for existing shared utilities
- [ ] Check `app/domain/<domain>/utils/` for domain-specific utilities
- [ ] Check existing services for similar methods

### 3. Hardcoded Values Check

- [ ] Am I about to hardcode any of these?
  - Member names (e.g., `"faiyaz"`, `"trisha"`)
  - Permissions or age checks (e.g., `is_adult`, `adult_members`)
  - Magic numbers (e.g., `max_retries=3`, `timeout=30`)
  - Magic strings (e.g., `"active"`, `"completed"`)
  - Environment-specific values (e.g., database URLs, API keys)
- [ ] If YES → Use configuration, database, environment variables, or named constants instead

### 4. Domain/Infrastructure Separation Check

- [ ] Am I adding framework imports to domain layer?
  - `from fastapi import ...`
  - `from sqlmodel import ...`
  - `import httpx`
  - `import redis`
- [ ] If YES → Move to infrastructure layer, use Protocol interfaces in domain

### 5. Testing Check

- [ ] Does this change need tests?
  - New domain logic → Need unit tests (`tests/unit/`)
  - New repository methods → Need integration tests (`tests/integration/`)
  - New API endpoints → Need API tests (`tests/api/`)
- [ ] Plan test coverage before coding:
  - Happy path
  - Edge cases (boundaries, empty inputs)
  - Error conditions
  - Validation failures

### 6. REST Compliance Check

- [ ] Am I adding verbs to URLs?
  - `/approve`, `/complete`, `/claim`, `/signoff`
- [ ] If YES → Refactor to RESTful resources:
  - Use PATCH for status changes
  - Use POST for creating resources
  - Use nouns for resources (not verbs)

### 7. Pattern Decision Tree

Use this decision tree when implementing:

```
1. Am I writing the same logic in 2+ places?
   YES → Extract to utility function
   NO  → Continue

2. Am I hardcoding a value that should be configurable?
   YES → Use configuration, database, or environment variable
   NO  → Continue

3. Am I importing frameworks in domain layer?
   YES → Move to infrastructure, use Protocol interfaces
   NO  → Continue

4. Am I adding verbs to URLs?
   YES → Refactor to RESTful resources
   NO  → Continue

5. Am I writing a public function/class without docstring?
   YES → Add Google-style docstring
   NO  → Implementation is correct
```

## Example Violations Caught

### Violation 1: Hardcoded member names

```python
# BAD: Hardcoded member names
ADULT_MEMBERS = {"faiyaz", "trisha"}

def can_signoff(member_name: str) -> bool:
    return member_name in ADULT_MEMBERS

# GOOD: Data-driven from database
async def can_signoff(member_id: str, session: AsyncSession) -> bool:
    member = await session.get(FamilyMember, member_id)
    return member.has_permission("signoff")
```

### Violation 2: Framework imports in domain

```python
# BAD: FastAPI import in domain layer
from fastapi import HTTPException

class ChoresService:
    async def get_chore(self, chore_id: str):
        chore = await self.repo.get(chore_id)
        if not chore:
            raise HTTPException(status_code=404, detail="Chore not found")

# GOOD: Domain exception, infrastructure converts to HTTP
class ChoreNotFoundError(Exception):
    pass

class ChoresService:
    async def get_chore(self, chore_id: str):
        chore = await self.repo.get(chore_id)
        if not chore:
            raise ChoreNotFoundError(f"Chore {chore_id} not found")

# In API layer:
@router.get("/chores/{chore_id}")
async def get_chore(chore_id: str):
    try:
        return await service.get_chore(chore_id)
    except ChoreNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### Violation 3: Duplicated logic

```python
# BAD: Same period calculation in 3 places
def generate_instance():
    if frequency == "weekly":
        period_start = today - timedelta(days=today.weekday())
        period_end = period_start + timedelta(days=6)

def check_expiration():
    if frequency == "weekly":
        period_start = today - timedelta(days=today.weekday())
        period_end = period_start + timedelta(days=6)

# GOOD: Single utility function
from app.domain.chores.utils.periods import calculate_period

def generate_instance():
    period_start, period_end = calculate_period(frequency, today)

def check_expiration():
    period_start, period_end = calculate_period(frequency, today)
```

### Violation 4: Verbs in URLs

```python
# BAD: Verb in URL
@router.post("/chores/{chore_id}/complete")
async def complete_chore(chore_id: str):
    ...

# GOOD: RESTful resource with PATCH
@router.patch("/chores/{chore_id}")
async def update_chore(chore_id: str, update: ChoreUpdate):
    if update.status == "completed":
        ...
```

### Violation 5: Missing docstrings

```python
# BAD: No docstring
def calculate_period(frequency, reference_date):
    if frequency == "weekly":
        ...

# GOOD: Google-style docstring
def calculate_period(
    frequency: str, reference_date: date
) -> tuple[date, date]:
    """Calculate period boundaries for a given frequency.

    Args:
        frequency: One of 'daily', 'weekly', 'monthly', 'yearly'.
        reference_date: Date to calculate period for.

    Returns:
        Tuple of (period_start, period_end) dates.

    Raises:
        ValueError: If frequency is not recognized.
    """
    if frequency == "weekly":
        ...
```

## Enforcement

If you skip this checklist and violations are found later, they are part of the current phase — do not defer to a separate "cleanup phase."

## Notes

- This checklist is **mandatory** before writing code
- Run `/self-review` after coding to catch anything missed
- Run `/code-review-gate` before quality gates
- All commands run inside Docker containers via Makefile targets
