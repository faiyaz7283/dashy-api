# Chores Redesign — Complete Design & Implementation Plan

> **Status:** Design complete — awaiting implementation approval
> **Created:** 2026-08-26
> **Replaces:** Previous chores architecture (approval flow, no associations, no conditional logic)

---

## Executive Summary

The chores feature is being redesigned to support five chore types, persistent associations between masters and members, conditional activation based on external data, and collaborative multi-member tracking. All permission/age-based restrictions are removed — any member can perform any action.

**Key changes:**
- New `chore_associations` table for persistent master→member links
- Instance generation triggered by association, completion, and safety net (hybrid approach)
- Conditional chores with JSON-based condition evaluation
- Collaborative masters allow multiple simultaneous associations
- Bulk pause/resume for masters
- Complete removal of approval flow and age-based logic

---

## 1.5 Date/Time Standard (Chores Module)

All date/time handling in the chores module follows industry-standard practices. This is a **module-level standard** — a project-wide date/time standardization is planned separately.

### Rules

| Rule | Implementation |
|------|---------------|
| **Timezone-aware UTC** | `datetime.now(timezone.utc)` — never `datetime.utcnow()` (deprecated Python 3.12+) |
| **ISO 8601 wire format** | Timestamps: `"2026-08-26T19:30:00Z"` (with `Z` suffix, no microseconds) |
| **Date-only fields** | `"2026-08-26"` (ISO date, no time component) — used for `end_date`, `period_start`, `period_end` |
| **Time-only fields** | `"18:00"` (24-hour, HH:MM) — used for `recurrence_rule.time` |
| **DB storage** | Timestamps use `sa.DateTime()` columns; date-only fields stored as `TEXT` (ISO format) |
| **Serialization** | `.isoformat(timespec="seconds")` + `"Z"` suffix for UTC timestamps |

### What This Affects

- `app/domain/chores/models.py` — dataclass defaults use `datetime.now(timezone.utc)`
- `app/domain/chores/services.py` — all timestamp generation uses timezone-aware UTC
- `app/infrastructure/persistence/chores_repository.py` — soft-delete timestamps
- `app/infrastructure/persistence/models.py` — DB model defaults
- `app/infrastructure/chores/mock_adapter.py` — mock data timestamps
- `app/api/routes/chores.py` — serialization strips microseconds, adds `Z` suffix

### Not Changed (Project-Wide Fix Later)

- Weather/calendar modules still use `datetime.utcnow()` or naive local time
- Non-chores DB columns (`family_members.date_of_birth`, etc.) remain as-is
- Frontend `new Date()` legacy usage in `WeatherPopup.tsx` and `family.ts`

---

## 1. Chore Types

| Type | How It Works | Special Fields |
|------|-------------|----------------|
| **Recurring** | Master → associate → instance → complete → next instance | `frequency`, `end_date`, `max_occurrences` |
| **One-off** | Master (`frequency=once`) → associate → single instance | `frequency=once` |
| **Recurring w/ Expiration** | Stops at `end_date` or `max_occurrences` (whichever first) | `end_date`, `max_occurrences` |
| **Conditional** | Backend evaluates conditions → instances appear when met | `conditions` (JSON), `status` (active/inactive) |
| **Collaborative** | Multiple members associate same master, each gets own instances | `is_collaborative=true` |

**Milestone** — Deferred to future feature.
**Chore chains** — Not included (no good use case).

---

## 2. Database Design

### 2.1 MasterChore — New/Changed Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `recurrence_rule` | `JSON` | `NULL` | Recurrence pattern config (validated as `RecurrenceRule` Pydantic model). Replaces old `frequency` column. Contains frequency, time, day_of_week, day_of_month, week_of_month, month. |
| `end_date` | `TEXT` | `NULL` | Stop generating after this date (ISO format) |
| `max_occurrences` | `INTEGER` | `NULL` | Stop after N total instances generated |
| `occurrence_count` | `INTEGER` | `0` | Total instances generated (incremented on each generation) |
| `conditions` | `JSON` | `NULL` | Conditional chore conditions (validated as `ConditionsConfig` Pydantic model) |
| `is_collaborative` | `INTEGER` | `0` | 1 if multiple members can have simultaneous instances |
| `status` | `TEXT` | `'active'` | `active`, `inactive`, `archived` |

**Removed fields:**
- `approved_by` — no approval flow
- `frequency` — replaced by `recurrence_rule` JSON (which includes frequency + configuration)

**Removed enum values:**
- `pending_approval` from `MasterChoreStatus` — only `active`, `inactive`, `archived` remain

### 2.2 New Table: `chore_associations`

```sql
CREATE TABLE chore_associations (
    id TEXT PRIMARY KEY,
    master_chore_id TEXT NOT NULL REFERENCES master_chores(id),
    member_id TEXT NULL,
    is_open_pool INTEGER DEFAULT 0,
    created_by TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    removed_at DATETIME NULL,
    
    UNIQUE(master_chore_id, member_id)  -- one active association per member per master
);
```

**Application-level rules (enforced in service):**
- Non-collaborative master: only one non-open-pool association allowed at a time
- Open pool: one open pool association per master
- Collaborative master: multiple non-open-pool associations allowed
- `removed_at` is set when disassociated (soft delete)
- Historical associations preserved for stats/tracking

### 2.3 ChoreInstance — New Field

| Field | Type | Notes |
|-------|------|-------|
| `association_id` | `TEXT FK → chore_associations.id` | Links instance to its association |

Keep `master_chore_id` for query convenience (denormalized, but practical for "show me all instances of this chore").

### 2.4 Removed Tables/Fields

- `approved_by` column from `master_chores`
- `pending_approval` from status enum
- `signoff_by`, `signed_off_at` from `chore_instances` — signoff flow removed entirely

---

## 3. Domain Model Changes

### 3.1 Enums

**MasterChoreStatus:**
```python
class MasterChoreStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
```

**InstanceStatus** — unchanged:
```python
class InstanceStatus(StrEnum):
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    MISSED = "missed"
    ARCHIVED = "archived"
```

**Removed:**
- `COMPLETED_PENDING_SIGNOFF` — signoff flow removed

### 3.2 Dataclasses

**MasterChore** — new fields:
```python
@dataclass
class MasterChore:
    # ... existing fields ...
    end_date: str | None = None
    max_occurrences: int | None = None
    occurrence_count: int = 0
    conditions: list[dict] | None = None  # JSON structure
    is_collaborative: bool = False
    # Remove: approved_by
```

**New: ChoreAssociation:**
```python
@dataclass
class ChoreAssociation:
    id: str
    master_chore_id: str
    member_id: str | None = None
    is_open_pool: bool = False
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    removed_at: datetime | None = None
```

**ChoreInstance** — new field:
```python
@dataclass
class ChoreInstance:
    # ... existing fields ...
    association_id: str | None = None  # FK to association
    # Remove: signoff_by, signed_off_at
```

---

## 4. JSON Schema Validation — Single Source of Truth

All JSON fields (`recurrence_rule`, `conditions`) are validated using Pydantic models. These models are the **single source of truth** for JSON structure — no ad-hoc validation scattered across the codebase.

### 4.1 Recurrence Rule Schema

```python
# app/domain/chores/schemas.py

from pydantic import BaseModel, model_validator
from typing import Literal

class RecurrenceRule(BaseModel):
    """
    Recurrence pattern configuration for chore instances.
    
    Validates field combinations based on frequency:
    - once: no additional fields required
    - daily: no additional fields required
    - weekly: requires day_of_week
    - monthly: requires day_of_month OR (day_of_week + week_of_month)
    - yearly: requires month + (day_of_month OR (day_of_week + week_of_month))
    
    Examples:
        Daily at 8am: {"frequency": "daily", "time": "08:00"}
        Weekly on Monday at 9am: {"frequency": "weekly", "day_of_week": 1, "time": "09:00"}
        Monthly on 3rd at 10am: {"frequency": "monthly", "day_of_month": 3, "time": "10:00"}
        Monthly first Monday at 8am: {"frequency": "monthly", "day_of_week": 1, "week_of_month": 1, "time": "08:00"}
        Yearly on Jan 15th at 9am: {"frequency": "yearly", "month": 1, "day_of_month": 15, "time": "09:00"}
        Yearly 4th Thursday Nov at 12pm: {"frequency": "yearly", "month": 11, "day_of_week": 3, "week_of_month": 4, "time": "12:00"}
    """
    
    frequency: Literal["once", "daily", "weekly", "monthly", "yearly"]
    time: str  # HH:MM format (24-hour), required for all frequencies
    
    # Weekly
    day_of_week: int | None = None  # 0=Monday, 6=Sunday
    
    # Monthly
    day_of_month: int | None = None  # 1-31
    week_of_month: int | None = None  # 1-5 (for "first Monday", "third Friday")
    
    # Yearly
    month: int | None = None  # 1-12
    
    @model_validator(mode='after')
    def validate_recurrence_combinations(self):
        """Validate field combinations based on frequency."""
        if self.frequency == "once":
            # No additional fields needed
            pass
        elif self.frequency == "daily":
            # No additional fields needed
            pass
        elif self.frequency == "weekly":
            if self.day_of_week is None:
                raise ValueError("weekly frequency requires day_of_week")
        elif self.frequency == "monthly":
            if self.day_of_month is None and (self.day_of_week is None or self.week_of_month is None):
                raise ValueError("monthly frequency requires either day_of_month OR (day_of_week + week_of_month)")
        elif self.frequency == "yearly":
            if self.month is None:
                raise ValueError("yearly frequency requires month")
            if self.day_of_month is None and (self.day_of_week is None or self.week_of_month is None):
                raise ValueError("yearly frequency requires either (month + day_of_month) OR (month + day_of_week + week_of_month)")
        
        return self
```

**Validation rules:**
- `time` is required for all frequencies (HH:MM 24-hour format)
- `day_of_week`: 0=Monday, 6=Sunday (ISO weekday)
- `day_of_month`: 1-31 (adjusted for shorter months in period calculation)
- `week_of_month`: 1-5 (1=first occurrence, 5=fifth occurrence)
- `month`: 1-12

**First instance logic:**
- If today is Wednesday and chore recurs weekly on Monday → first instance is for **next Monday**
- If today is Monday before configured time → first instance is for **today**
- If today is Monday after configured time → first instance is for **next Monday**

### 4.2 Conditions Schema

```python
class Condition(BaseModel):
    """
    Single condition for conditional chores.
    
    Weather conditions:
        {"type": "weather", "metric": "snowfall", "operator": "gt", "value": 0}
        {"type": "weather", "metric": "temperature", "operator": "lt", "value": 32}
    
    Calendar conditions:
        {"type": "calendar", "event_count": 5, "operator": "gte", "value": 5}
        {"type": "calendar", "event_type": "meeting", "operator": "eq", "value": "meeting"}
    """
    
    type: Literal["weather", "calendar"]
    operator: Literal["gt", "lt", "eq", "gte", "lte", "contains"]
    value: float | str
    
    # Weather-specific
    metric: Literal["temperature", "snowfall", "rainfall", "wind_speed"] | None = None
    
    # Calendar-specific
    event_count: int | None = None
    event_type: str | None = None
    
    @model_validator(mode='after')
    def validate_condition_fields(self):
        """Validate condition-specific fields."""
        if self.type == "weather" and self.metric is None:
            raise ValueError("weather condition requires metric")
        if self.type == "calendar" and self.event_count is None and self.event_type is None:
            raise ValueError("calendar condition requires event_count or event_type")
        return self


class ConditionsConfig(BaseModel):
    """
    Configuration for conditional chore evaluation.
    
    Example:
        {
            "logic": "and",
            "conditions": [
                {"type": "weather", "metric": "snowfall", "operator": "gt", "value": 0},
                {"type": "weather", "metric": "temperature", "operator": "lt", "value": 32}
            ]
        }
    """
    
    logic: Literal["and", "or"] = "and"
    conditions: list[Condition]
```

### 4.3 Database Storage

**MasterChore model:**
```python
class MasterChore(SQLModel):
    # ... existing fields ...
    recurrence_rule: dict | None = None  # JSON, validated as RecurrenceRule
    conditions: dict | None = None  # JSON, validated as ConditionsConfig
```

**Validation on read/write:**
```python
# In repository or service layer
def get_recurrence_rule(self) -> RecurrenceRule | None:
    """Parse and validate recurrence_rule JSON."""
    if self.recurrence_rule is None:
        return None
    return RecurrenceRule(**self.recurrence_rule)

def set_recurrence_rule(self, rule: RecurrenceRule) -> None:
    """Serialize validated RecurrenceRule to JSON."""
    self.recurrence_rule = rule.model_dump(exclude_none=True)
```

**Single source of truth:**
- Pydantic models define the schema
- Validation happens at model instantiation
- API models use these schemas for request/response
- Documentation is in the Pydantic docstrings
- No ad-hoc validation elsewhere

---

## 5. Backend Design

### 5.1 Service Layer — New Methods

**`ChoresService`** — new methods:

```python
# Association management
async def associate_master(
    self, master_id: str, member_id: str | None, created_by: str
) -> ChoreAssociation:
    """
    Associate master with member or open pool.
    Validates collaborative rules.
    Generates first instance immediately.
    """

async def disassociate_master(
    self, master_id: str, member_id: str | None
) -> None:
    """
    Soft-delete association (set removed_at).
    Archive active instances for that association.
    Master is free for new association.
    """

# Instance generation
async def generate_instance_for_association(
    self, association_id: str
) -> ChoreInstance | None:
    """
    Generate next instance for an association.
    Called by: associate, complete, safety net, conditional evaluation.
    Checks: end_date, max_occurrences, frequency.
    Increments occurrence_count atomically.
    Returns None if limits reached.
    """

async def ensure_current_instances(self) -> list[ChoreInstance]:
    """
    Safety net called on board load.
    For each active association: does current period have an instance?
    For conditional masters: evaluate conditions, generate if met.
    Returns list of newly created instances.
    """

# Condition evaluation
async def evaluate_conditions(self, master_id: str) -> bool:
    """
    Evaluate conditional chore conditions against live data.
    Fetches weather/calendar data via injected providers.
    Evaluates condition tree (AND/OR logic).
    """

# Expiration processing
async def process_expired_instances(self) -> list[ChoreInstance]:
    """
    Find instances past period_end with non-completed status.
    Apply expiration_behavior from parent master.
    Trigger next instance generation if applicable.
    """

# Bulk operations
async def bulk_update_master_status(
    self, master_ids: list[str], status: MasterChoreStatus
) -> None:
    """
    Pause/resume multiple masters at once.
    Sets status, updated_at for all.
    """

# Internal validation
def _validate_association(
    self, master: MasterChore, member_id: str | None, existing_associations: list
) -> None:
    """
    Enforce collaborative rules:
    - Non-collaborative: only one non-open-pool association
    - Collaborative: multiple allowed
    - Open pool: one per master
    """
```

### 5.2 Period Calculation — Single Utility

```python
# app/domain/chores/utils/periods.py

from datetime import date, timedelta
from calendar import monthrange
from app.domain.chores.schemas import RecurrenceRule

def calculate_period(
    rule: RecurrenceRule, reference_date: date
) -> tuple[date | None, date | None]:
    """
    Calculate period_start and period_end based on recurrence rule.
    
    Uses configured day_of_week, day_of_month, week_of_month, month
    to determine exact period boundaries.
    
    Single source of truth for period logic.
    
    Args:
        rule: Validated RecurrenceRule with frequency and configuration
        reference_date: Date to calculate period for (usually today)
    
    Returns:
        (period_start, period_end) tuple. None for frequency=once.
    
    Examples:
        Weekly on Monday: reference_date=Wed Aug 26 → (Mon Aug 24, Sun Aug 30)
        Monthly on 15th: reference_date=Aug 20 → (Aug 15, Aug 31)
        Monthly first Monday: reference_date=Aug 20 → (Mon Aug 4, Mon Aug 4)
        Yearly on Jan 15: reference_date=Aug 20, 2026 → (Jan 15, 2026, Jan 15, 2026)
    """
    if rule.frequency == "once":
        return (None, None)
    
    if rule.frequency == "daily":
        return (reference_date, reference_date)
    
    if rule.frequency == "weekly":
        # Find the configured day of week for this week
        target_weekday = rule.day_of_week  # 0=Monday, 6=Sunday
        current_weekday = reference_date.weekday()
        
        # Calculate days to target
        days_diff = target_weekday - current_weekday
        
        # If target is in the past this week, use next week
        if days_diff < 0:
            days_diff += 7
        
        target_date = reference_date + timedelta(days=days_diff)
        return (target_date, target_date)
    
    if rule.frequency == "monthly":
        year = reference_date.year
        month = reference_date.month
        
        if rule.day_of_month is not None:
            # Fixed day of month (e.g., 15th of every month)
            # Adjust for shorter months
            max_day = monthrange(year, month)[1]
            day = min(rule.day_of_month, max_day)
            target_date = date(year, month, day)
            return (target_date, target_date)
        
        elif rule.day_of_week is not None and rule.week_of_month is not None:
            # Nth weekday of month (e.g., first Monday, third Friday)
            target_date = _get_nth_weekday(year, month, rule.day_of_week, rule.week_of_month)
            return (target_date, target_date)
    
    if rule.frequency == "yearly":
        month = rule.month
        year = reference_date.year
        
        if rule.day_of_month is not None:
            # Fixed date (e.g., Jan 15 every year)
            max_day = monthrange(year, month)[1]
            day = min(rule.day_of_month, max_day)
            target_date = date(year, month, day)
            return (target_date, target_date)
        
        elif rule.day_of_week is not None and rule.week_of_month is not None:
            # Nth weekday of month (e.g., 4th Thursday of November)
            target_date = _get_nth_weekday(year, month, rule.day_of_week, rule.week_of_month)
            return (target_date, target_date)
    
    return (None, None)


def _get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """
    Get the Nth occurrence of a weekday in a month.
    
    Args:
        year: Year
        month: Month (1-12)
        weekday: Day of week (0=Monday, 6=Sunday)
        n: Occurrence (1=first, 2=second, etc.)
    
    Returns:
        Date of the Nth weekday
    
    Example:
        _get_nth_weekday(2026, 11, 3, 4) → 4th Thursday of November 2026
    """
    first_day = date(year, month, 1)
    first_weekday = first_day.weekday()
    
    # Days to first occurrence of target weekday
    days_to_target = (weekday - first_weekday) % 7
    first_occurrence = first_day + timedelta(days=days_to_target)
    
    # Add (n-1) weeks to get Nth occurrence
    target_date = first_occurrence + timedelta(weeks=n - 1)
    
    # Verify it's still in the same month
    if target_date.month != month:
        # Nth occurrence doesn't exist in this month (e.g., 5th Monday in a month with only 4)
        # Return last occurrence
        target_date = first_occurrence + timedelta(weeks=n - 2)
    
    return target_date


def get_next_occurrence(rule: RecurrenceRule, from_date: date, from_time: str) -> date:
    """
    Calculate the next occurrence date from a given date/time.
    
    Used for first instance generation and next instance after completion.
    
    Args:
        rule: Validated RecurrenceRule
        from_date: Starting date
        from_time: Current time (HH:MM format)
    
    Returns:
        Next occurrence date
    
    Logic:
        - If today is the target day and current time < configured time → today
        - If today is the target day and current time >= configured time → next period
        - If today is not the target day → next target day
    """
    period_start, _ = calculate_period(rule, from_date)
    
    if period_start is None:
        return from_date  # frequency=once
    
    # Compare times
    if period_start == from_date and from_time < rule.time:
        return period_start  # Today, before configured time
    
    # Need next occurrence
    if rule.frequency == "daily":
        return from_date + timedelta(days=1)
    
    if rule.frequency == "weekly":
        return period_start + timedelta(weeks=1)
    
    if rule.frequency == "monthly":
        # Next month
        next_month = from_date.month + 1 if from_date.month < 12 else 1
        next_year = from_date.year if from_date.month < 12 else from_date.year + 1
        return calculate_period(rule, date(next_year, next_month, 1))[0]
    
    if rule.frequency == "yearly":
        # Next year
        return calculate_period(rule, date(from_date.year + 1, 1, 1))[0]
    
    return from_date
```

### 5.3 Condition Evaluator — Domain Service

```python
# app/domain/chores/services/condition_evaluator.py

class ConditionEvaluator:
    """Evaluates conditional chore conditions against live data."""
    
    def __init__(
        self, 
        weather_provider: WeatherProvider,
        calendar_provider: CalendarProvider
    ):
        self.weather = weather_provider
        self.calendar = calendar_provider
    
    async def evaluate(self, conditions: list[dict], logic: str = "all") -> bool:
        """
        Evaluate conditions with AND/OR logic.
        
        Args:
            conditions: List of condition dicts:
                [{"source": "weather", "field": "snowfall_cm", "operator": "gt", "value": 0}]
            logic: "all" (AND) or "any" (OR)
        
        Returns:
            True if conditions met, False otherwise.
        """
        results = [await self._evaluate_single(c) for c in conditions]
        return all(results) if logic == "all" else any(results)
    
    async def _evaluate_single(self, condition: dict) -> bool:
        """Evaluate a single condition against live data."""
        source = condition["source"]
        field = condition["field"]
        operator = condition["operator"]
        threshold = condition["value"]
        
        if source == "weather":
            data = await self.weather.get_current()
            actual = getattr(data, field, None)
        elif source == "calendar":
            events = await self.calendar.get_upcoming(days=1)
            actual = [e.title for e in events]
        else:
            return False
        
        return self._compare(actual, operator, threshold)
    
    def _compare(self, actual, operator: str, threshold) -> bool:
        """Compare actual value against threshold using operator."""
        match operator:
            case "gt": return actual > threshold
            case "gte": return actual >= threshold
            case "lt": return actual < threshold
            case "lte": return actual <= threshold
            case "eq": return actual == threshold
            case "contains": return threshold in actual
            case _: return False
```

**DI wiring:** Inject `WeatherProvider` and `CalendarProvider` into `ConditionEvaluator`, then inject `ConditionEvaluator` into `ChoresService`.

### 5.4 Instance Lifecycle — State Machine

```
         associate()
             │
             ▼
         ┌────────┐
         │ active  │◄──── generate_next_instance() on completion
         └────┬────┘      of previous instance
              │
         claim() / assign()
              │
              ▼
        ┌─────────────┐
        │ in_progress  │
        └─────┬───────┘
              │
         complete()
              │
              ▼
         ┌───────────┐
         │ completed  │
         └───────────┘

  Period ends without completion:
    active/in_progress → apply expiration_behavior
      disappear  → delete instance
      carry_over → new instance next period, same status
      stay_visible → mark as missed
      convert_to_open → clear assignment, move to pool
```

**All transitions in one place** — `update_instance_status()` method. No scattered state changes.

### 5.5 Instance Generation Flow

```python
async def generate_instance_for_association(
    self, association_id: str
) -> ChoreInstance | None:
    """
    Generate next instance for an association.
    
    Flow:
    1. Load association + master
    2. Check limits: end_date, max_occurrences
    3. Calculate period for next occurrence
    4. Check if instance already exists for this period
    5. Create instance
    6. Increment master.occurrence_count
    7. Save both atomically
    """
    association = await self.repo.get_association_by_id(association_id)
    master = await self.repo.get_master_chore_by_id(association.master_chore_id)
    
    # Check limits
    if master.end_date and today > parse_date(master.end_date):
        return None
    if master.max_occurrences and master.occurrence_count >= master.max_occurrences:
        return None
    
    # Calculate period
    reference_date = self._get_next_reference_date(master, association)
    period_start, period_end = calculate_period(master.frequency, reference_date)
    
    # Check for existing instance
    existing = await self.repo.get_instance_for_period(
        association_id, period_start, period_end
    )
    if existing:
        return existing
    
    # Create instance
    instance = ChoreInstance(
        id=generate_id(),
        master_chore_id=master.id,
        association_id=association.id,
        period_start=period_start.isoformat() if period_start else None,
        period_end=period_end.isoformat() if period_end else None,
        status=InstanceStatus.ACTIVE,
        claimed_by=association.member_id if not association.is_open_pool else None,
        assigned_to=association.member_id if not association.is_open_pool else None,
    )
    instance = await self.repo.create_instance(instance)
    
    # Increment counter
    master.occurrence_count += 1
    await self.repo.update_master_chore(master.id, {"occurrence_count": master.occurrence_count})
    
    return instance
```

---

## 6. Cache Design

| Data | Cache? | TTL | Rationale |
|------|--------|-----|-----------|
| Categories | Yes | 1 hour | Rarely change |
| Tags | Yes | 1 hour | Rarely change |
| Master chores | Yes | 5 min | Change occasionally (status, config) |
| Associations | Yes | 5 min | Change occasionally (associate/disassociate) |
| Instances | **No** | — | Change frequently (status, generation). Stale data = broken board. |
| Condition evaluation | Short-term | 15 min | Weather data already cached upstream |

**Key principle:** Cache reads, never writes. Instance generation always writes through to DB.

---

## 7. DRY & Single Source of Truth

| Concern | Single Location | Used By |
|---------|----------------|---------|
| Recurrence rule schema | `schemas.py` → `RecurrenceRule` (Pydantic) | API models, DB read/write, period calculation |
| Conditions schema | `schemas.py` → `ConditionsConfig` (Pydantic) | API models, DB read/write, condition evaluator |
| Period calculation | `utils/periods.py` → `calculate_period()` | Generation, expiration, safety net |
| Instance generation | `ChoresService.generate_instance_for_association()` | Associate, complete, safety net |
| Condition evaluation | `ConditionEvaluator.evaluate()` | Safety net, on-demand check |
| Status transitions | `ChoresService.update_instance_status()` | All status change paths |
| Collaborative enforcement | `ChoresService._validate_association()` | Associate endpoint |
| Expiration behavior | `ChoresService.process_expired_instances()` | Safety net |

No duplicate logic. Every trigger calls the same method.

---

## 8. Removals — Permission/Approval Cleanup

| Remove | Location |
|--------|----------|
| `pending_approval` enum value | `MasterChoreStatus` |
| `approved_by` field | Domain model, DB model, API model, migration |
| `approve_master_chore()` method | `ChoresService` |
| `POST /masters/{id}/approve` route | API routes |
| `ApproveMasterChoreRequest` model | API models |
| `is_adult` parameter | `update_instance_status()` |
| Hardcoded `adult_members` set | API routes |
| Adult vs kid completion logic | Service — any member completes = same path |
| `COMPLETED_PENDING_SIGNOFF` enum value | `InstanceStatus` |
| `signoff_by`, `signed_off_at` fields | Domain model, DB model, API model |
| `signoff_instance()` method | `ChoresService` |
| `POST /instances/{id}/signoff` route | API routes |
| `SignoffInstanceRequest` model | API models |

---

## 9. API Changes

### 9.1 RESTful Design Principles

All endpoints follow REST conventions:
- **Resources are nouns** (masters, instances, associations)
- **HTTP methods indicate action** (GET=read, POST=create, PATCH=update, DELETE=remove)
- **No verbs in URLs** (no `/approve`, `/complete`, `/claim`)
- **Proper status codes** (201 Created, 204 No Content, 404 Not Found)
- **PATCH for partial updates** (status changes, bulk operations)

### 9.2 New Endpoints

```
POST   /api/v1/chores/associations
         → Create association between master and member/open pool
         → Body: {master_id, member_id?, is_open_pool?, created_by}
         → Returns: 201 Created with Association + first instance
         → REST: POST creates a new resource

DELETE   /api/v1/chores/associations/{association_id}
         → Remove association (soft delete)
         → Archives active instances
         → Returns: 204 No Content
         → REST: DELETE removes a resource

PATCH    /api/v1/chores/masters
         → Bulk update masters (pause/resume)
         → Body: {ids: [...], status: "active"|"inactive"}
         → Returns: 200 OK with updated masters
         → REST: PATCH for partial updates to multiple resources
```

### 9.3 Modified Endpoints

```
POST   /api/v1/chores/masters
         → Remove: approved_by, pending_approval logic
         → Add: end_date, max_occurrences, conditions, is_collaborative, recurrence_rule
         → All masters go straight to ACTIVE status
         → Returns: 201 Created

GET    /api/v1/chores/masters
         → Add: associations in response
         → Safety net: call ensure_current_instances() before returning
         → Returns: 200 OK with masters + associations

GET    /api/v1/chores/masters/{id}
         → Add: associations in response
         → Returns: 200 OK with master + associations

PATCH  /api/v1/chores/masters/{id}
         → Update master fields
         → Returns: 200 OK with updated master

DELETE /api/v1/chores/masters/{id}
         → Soft delete master
         → Returns: 204 No Content

GET    /api/v1/chores/instances
         → List instances with optional filters
         → Query params: status, master_id, association_id, period_start, period_end
         → Safety net: call ensure_current_instances() before returning
         → Returns: 200 OK with instances

GET    /api/v1/chores/instances/{id}
         → Get single instance
         → Returns: 200 OK with instance

PATCH  /api/v1/chores/instances/{id}
         → Update instance status (claim, complete, etc.)
         → Body: {status: "claimed"|"completed"|"in_progress"}
         → Remove: is_adult parameter, signoff logic
         → On status=completed: trigger generate_next_instance()
         → Returns: 200 OK with updated instance
         → REST: PATCH for status updates (not POST /instances/{id}/complete)
```

### 9.4 Removed Endpoints

```
POST   /api/v1/chores/masters/{id}/approve
         → No approval flow
         → REST violation: verb in URL

POST   /api/v1/chores/instances/{id}/signoff
         → No signoff flow
         → REST violation: verb in URL

POST   /api/v1/chores/instances/{id}/claim
         → Replaced with: PATCH /instances/{id} with {status: "claimed"}
         → REST violation: verb in URL

POST   /api/v1/chores/instances/{id}/complete
         → Replaced with: PATCH /instances/{id} with {status: "completed"}
         → REST violation: verb in URL

GET    /api/v1/chores/board
         → Replaced with: GET /instances with query params
         → REST violation: "board" is not a resource
```

### 9.5 API Model Changes

**MasterChoreResponse** — add:
- `recurrence_rule: dict | None` — validated as `RecurrenceRule` Pydantic model
- `end_date: str | None`
- `max_occurrences: int | None`
- `occurrence_count: int`
- `conditions: dict | None` — validated as `ConditionsConfig` Pydantic model
- `is_collaborative: bool`

**Remove:**
- `approved_by: str | None`
- `frequency: str` — replaced by `recurrence_rule` (which includes frequency)

**New: AssociationResponse:**
```python
class AssociationResponse(BaseModel):
    id: str
    master_chore_id: str
    member_id: str | None
    is_open_pool: bool
    created_by: str
    created_at: str
    updated_at: str
    removed_at: str | None
```

**ChoresResponse** — add:
- `associations: list[AssociationResponse]`

**InstanceStatus enum** — remove:
- `completed_pending_signoff`

**Remove models:**
- `ApproveMasterChoreRequest`
- `SignoffInstanceRequest`

---

## 10. Testing Structure

### 10.1 Unit Tests (no I/O)

| Test File | Coverage |
|-----------|----------|
| `test_period_calculation.py` | All frequencies, edge cases (month boundaries, DST) |
| `test_condition_evaluator.py` | Weather conditions, calendar conditions, AND/OR logic |
| `test_instance_generation.py` | end_date limits, max_occurrences limits, period calculation |
| `test_association_rules.py` | Collaborative vs non-collaborative enforcement |
| `test_expiration_behavior.py` | All four behaviors |
| `test_status_transitions.py` | Full state machine coverage |

### 10.2 Integration Tests (real DB)

| Test File | Coverage |
|-----------|----------|
| `test_associations_repository.py` | CRUD, unique constraints, cascading deletes |
| `test_instance_queries.py` | Period-based queries, association-based queries |

### 10.3 API Tests (TestClient)

| Test File | Coverage |
|-----------|----------|
| `test_associate_endpoint.py` | Associate, disassociate, collaborative rules |
| `test_instance_generation_flow.py` | Create → associate → complete → next instance |
| `test_conditional_chore.py` | Conditions met/not met, instance creation |
| `test_bulk_operations.py` | Bulk pause/resume |

---

## 11. Implementation Phases

| Phase | What | Depends On | Status |
|-------|------|-----------|--------|
| **1** | Model changes — add fields to MasterChore, create `chore_associations` table, add `association_id` to ChoreInstance, remove approval fields, new migration | Nothing | ✅ Complete |
| **1.5** | Date/time standardization — proper `date`/`datetime` types for all chores fields, `datetime.now(UTC)` throughout | Phase 1 | ✅ Complete |
| **2** | Association logic — collaborative enforcement, archive-on-disassociate cascade, validation rules, enhanced error handling | Phase 1.5 | ✅ Complete |
| **3** | Instance generation — generate on associate, generate on complete, safety net on board load | Phase 2 | ✅ Complete |
| **4** | Expiration/rollover — period boundaries, expiration_behavior processing, overdue detection | Phase 3 | Pending |
| **5** | Conditional chores — conditions JSON, evaluator, integration with safety net | Phase 3 | Pending |
| **6** | Bulk operations — bulk pause/resume masters | Phase 1 | Pending |
| **7** | Permission cleanup — remove all approval/age/adult code | Phase 1 | ✅ Complete (done in Phase 1) |
| **8** | API model updates — new response fields, request fields, remove approval models | Phase 1 | ✅ Complete (done in Phase 1) |
| **9** | Tests — unit, integration, API for all new logic | Phases 2-7 | Pending |

**Parallelization:** Phases 6, 7, 8 can run in parallel after Phase 1. Phase 9 runs throughout but is finalized last.

**Phase 1 commit:** `6d22096` (dashy-api) — model changes, migration, schemas, services rewrite, test updates.

**Phase 1.5 commit:** `271bda6` (dashy-api) — TEXT→Date/DateTime type enforcement, `datetime.UTC` alias, documentation-only migration.

**Phase 2 commit:** `6c93863` (dashy-api) — `AssociationConflictError`, `_validate_association()`, collaborative enforcement rules, archive-on-disassociate cascade, enhanced error handling (404/409), 11 new unit tests + 6 new API tests.

**Phase 3 commit:** `4adcf8c` (dashy-api) — Period calculation utilities, instance generation engine, safety net on board load, 21 period tests + 8 generation tests + 2 safety net tests + 1 completion trigger test.

---

## 12. Migration Strategy

### 12.1 New Migration

```python
# alembic/versions/xxxx_chore_redesign.py

def upgrade():
    # 1. Add new fields to master_chores
    op.add_column('master_chores', sa.Column('end_date', sa.Text(), nullable=True))
    op.add_column('master_chores', sa.Column('max_occurrences', sa.Integer(), nullable=True))
    op.add_column('master_chores', sa.Column('occurrence_count', sa.Integer(), server_default='0'))
    op.add_column('master_chores', sa.Column('conditions', sa.JSON(), nullable=True))
    op.add_column('master_chores', sa.Column('is_collaborative', sa.Integer(), server_default='0'))
    
    # 2. Remove approval fields
    op.drop_column('master_chores', 'approved_by')
    
    # 3. Create associations table
    op.create_table(
        'chore_associations',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('master_chore_id', sa.Text(), sa.ForeignKey('master_chores.id')),
        sa.Column('member_id', sa.Text(), nullable=True),
        sa.Column('is_open_pool', sa.Integer(), server_default='0'),
        sa.Column('created_by', sa.Text(), server_default=''),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('removed_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('master_chore_id', 'member_id'),
    )
    
    # 4. Add association_id to instances
    op.add_column('chore_instances', sa.Column('association_id', sa.Text(), nullable=True))
    op.create_foreign_key(
        'fk_instance_association',
        'chore_instances', 'chore_associations',
        ['association_id'], ['id']
    )
    
    # 5. Remove signoff fields
    op.drop_column('chore_instances', 'signoff_by')
    op.drop_column('chore_instances', 'signed_off_at')
```

### 12.2 Data Migration

Existing instances have no `association_id`. Options:
- **Option A:** Set to NULL, leave as historical data. New instances require association.
- **Option B:** Create default associations for existing instances (one per master).

Recommendation: **Option A** — simpler, existing data is just historical.

---

## 13. Frontend Integration Notes

### 13.1 What Frontend Needs to Know

- **Associations** — new entity in API response. Frontend displays associations, not just instances.
- **Instance generation** — happens automatically on backend. Frontend just displays.
- **Conditional chores** — backend handles condition evaluation. Frontend just displays instances when they appear.
- **Collaborative** — frontend shows multiple instances per master if `is_collaborative=true`.

### 13.2 API Response Shape

```json
{
  "categories": [...],
  "tags": [...],
  "master_chores": [
    {
      "id": "master-001",
      "name": "Clean Dishes",
      "frequency": "daily",
      "is_collaborative": false,
      "end_date": null,
      "max_occurrences": null,
      "occurrence_count": 5,
      "conditions": null,
      "status": "active"
    }
  ],
  "associations": [
    {
      "id": "assoc-001",
      "master_chore_id": "master-001",
      "member_id": "artyom",
      "is_open_pool": false
    }
  ],
  "instances": [
    {
      "id": "inst-001",
      "master_chore_id": "master-001",
      "association_id": "assoc-001",
      "period_start": "2026-08-26",
      "period_end": "2026-08-26",
      "status": "active",
      "claimed_by": "artyom"
    }
  ]
}
```

---

## 14. Deferred Items

| Item | Reason | Revisit When |
|------|--------|--------------|
| Milestone chores | Too complex for current iteration | After core chores stable |
| Chore chains | No clear use case | User identifies need |
| Permission/role system | Out of scope for current chores work | Separate feature |
| Conditional condition UI | Frontend work, not backend | After backend complete |
| Bulk association | Bulk assign master to multiple members | After individual association works |
| SSE (Server-Sent Events) | Requires dedicated design; reference Dashtam SSE setup | After polling-based v1 is stable |
| Condition tracker background service | Tied to SSE implementation — polling sufficient for v1 | When SSE is implemented |

---

## 15. Resolved Questions

1. **Occurrence count sync** — ✅ All generation goes through one method (`generate_instance_for_association()`), so counter stays in sync. Diagnostic endpoint to compare counter vs actual instance count — **approved**, will add.

2. **Association removal** — ✅ When disassociated, active instances get `archived` status. Historical data preserved. Master free for new association. `occurrence_count` NOT reset — tracks total lifetime instances for stats/analysis.

3. **Conditional evaluation frequency** — ✅ Backend logic with caching (15 min). Frontend polls for now. SSE deferred to future iteration (reference Dashtam SSE setup).

4. **Recurrence period calculation** — ✅ Calendar-based recurrence with explicit configuration. No defaults derived from creation time. `recurrence_rule` JSON field stores frequency + day/time configuration. Pydantic models validate structure.

5. **Time-of-day tracking** — ✅ Required for all frequencies. `time` field (HH:MM 24-hour format) in `recurrence_rule`.

6. **SSE vs polling** — ✅ Polling for v1. SSE deferred — requires dedicated design, will reference Dashtam's existing SSE setup.

---

## 16. Success Criteria

### Functional Requirements
- [ ] Masters can be created with all new fields (`recurrence_rule`, `end_date`, `max_occurrences`, `conditions`, `is_collaborative`)
- [ ] `recurrence_rule` JSON validated by Pydantic `RecurrenceRule` model
- [ ] `conditions` JSON validated by Pydantic `ConditionsConfig` model
- [ ] Associations can be created/deleted with proper validation
- [ ] Instances auto-generate on association, completion, and board load
- [ ] Period calculation uses configured `recurrence_rule` (day_of_week, day_of_month, time, etc.)
- [ ] Conditional chores evaluate conditions and generate instances when met
- [ ] Expiration behaviors work correctly
- [ ] Bulk pause/resume works
- [ ] All approval/age/signoff code removed
- [ ] All endpoints follow REST conventions (no verbs in URLs, proper HTTP methods)
- [ ] Frontend can display associations and instances correctly

### Quality Gates (all must pass)
- [ ] `make lint` passes — no ruff violations, Google-style docstrings enforced
- [ ] `make typecheck` passes — no type errors (if applicable)
- [ ] `make test` passes — all unit, integration, and API tests pass
- [ ] `make build` passes — production build succeeds

### Code Quality & Review
- [ ] No hardcoded values — all configurable data comes from `.env`, database, or API responses
- [ ] No hardcoded member names, ages, or permissions
- [ ] DRY principle followed — no duplicate logic (period calculation, instance generation, condition evaluation)
- [ ] Single source of truth — Pydantic models for JSON schemas, utility functions for period calculation
- [ ] Google-style docstrings on all public modules, classes, functions, and methods
- [ ] Proper naming conventions (snake_case for Python, descriptive names, no abbreviations)
- [ ] No magic numbers or strings — use named constants
- [ ] Small, focused functions — one job per function
- [ ] Proper error handling with RFC 9457 error format
- [ ] Domain layer separated from infrastructure adapters
- [ ] Protocol-based architecture for providers (WeatherProvider, CalendarProvider)
- [ ] Centralized DI container (FastAPI Depends() + @lru_cache)

### Test Coverage
- [ ] Unit tests for all pure functions (period calculation, condition evaluation, validation)
- [ ] Unit tests for all service methods (instance generation, association rules, expiration behavior)
- [ ] Integration tests for repository methods (CRUD, constraints, cascading deletes)
- [ ] API tests for all endpoints (success cases, error cases, validation)
- [ ] Edge case coverage (month boundaries, leap years, conditional logic AND/OR, collaborative enforcement)
- [ ] Test isolation maintained (tests use separate `test.db`, never modify dev database)

### Documentation
- [ ] All public APIs documented with Google-style docstrings
- [ ] Pydantic models have clear docstrings with examples
- [ ] Complex logic (period calculation, condition evaluation) has inline comments explaining "why"
- [ ] API endpoints documented with proper OpenAPI descriptions
- [ ] Migration strategy documented (data migration approach for existing instances)

---

## 17. References

- Spec: `docs/chores-spec.md`
- Previous architecture: `docs/plans/CHORES-ARCHITECTURE.md`
- Backend gaps analysis: `docs/chores-backend-gaps.md`
- Frontend types: `dashy-kiosk/src/types/chores.ts`
- Backend models: `app/domain/chores/models.py`
- Backend services: `app/domain/chores/services.py`
