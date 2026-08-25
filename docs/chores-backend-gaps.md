# Chores Backend — Implementation Gaps

> **Status:** Investigation complete — awaiting implementation planning
> **Created:** 2026-08-25
> **Context:** Frontend wiring complete (kiosk-v2 Phase 5). Board renders but stays empty because backend doesn't generate instances.

---

## Executive Summary

The backend has the **data model** and **CRUD endpoints** in place, but is missing the **business logic** that makes chores actually work:

1. **No instance generation** — Creating a master chore doesn't create any instances
2. **No recurring logic** — Daily/weekly/monthly chores never produce new instances
3. **No expiration/rollover** — Old instances never expire or carry over
4. **No overdue detection** — Instances never transition to `overdue` or `missed`

**Impact:** The frontend board renders correctly but shows zero chores because it displays `instances`, not `master_chores`.

---

## Gap Analysis

### Gap 1: No Instance Generation on Master Creation (P0)

**Spec Reference:** `docs/chores-spec.md` §7 — "System generates one `ChoreInstance` per period from the `MasterChore`"

**Current Behavior:**
```python
# routes/chores.py:155-190
@router.post("/masters", response_model=MasterChoreResponse, status_code=201)
async def create_master_chore(...):
    created = await chores_service.create_master_chore(...)
    # Returns master chore — NO instance created
    return _master_to_response(created, category_map)
```

**Expected Behavior:**
- `frequency: "once"` → Create one instance immediately (no period boundaries)
- `frequency: "daily"` → Create instance for today
- `frequency: "weekly"` → Create instance for current week (Mon-Sun)
- `frequency: "monthly"` → Create instance for current month (1st-last day)

**Fix Location:** `app/api/routes/chores.py` → `create_master_chore()` endpoint, or `app/domain/chores/services.py` → `create_master_chore()` method

---

### Gap 2: No Recurring Instance Generation (P0)

**Spec Reference:** `docs/chores-spec.md` §7 — "Generation logic runs on a schedule (e.g., nightly cron or on-demand)"

**Current Behavior:**
- No cron job exists
- No scheduled task exists
- No method like `generate_instances_for_period()` exists in `ChoresService`
- `ports.py` has `create_instance()` but nothing calls it automatically

**Expected Behavior:**
- When the board loads (`GET /api/v1/chores`), check if any active masters are missing instances for the current period
- Generate missing instances on-demand
- Alternative: Run a nightly cron job to generate instances for the next day/week/month

**Fix Location:** 
- `app/domain/chores/services.py` → Add `generate_instances_for_period(start_date, end_date)` method
- `app/api/routes/chores.py` → Call it in `get_all_chores()` before returning data
- OR: Add a Celery/cron task for scheduled generation

---

### Gap 3: No Expiration/Rollover Logic (P1)

**Spec Reference:** `docs/chores-spec.md` §8 — Expiration behaviors: `disappear`, `carry_over`, `stay_visible`, `convert_to_open`

**Current Behavior:**
- Zero implementation
- No logic to check period boundaries
- No rollover logic
- No status transitions

**Expected Behavior:**
When a period ends (e.g., day ends for daily chores):
- `disappear` → Delete the instance
- `carry_over` → Create a new instance for the next period with the same status
- `stay_visible` → Keep the instance, mark as `missed`
- `convert_to_open` → Clear `claimed_by`/`assigned_to`, move to open pool

**Fix Location:**
- `app/domain/chores/services.py` → Add `process_expired_instances()` method
- Call it in `get_all_chores()` or via cron

---

### Gap 4: No Overdue/Missed Status Transitions (P1)

**Spec Reference:** `docs/chores-spec.md` §2 — `overdue` = past due and not completed, `missed` = period ended without completion

**Current Behavior:**
- `InstanceStatus.OVERDUE` and `InstanceStatus.MISSED` exist in the enum
- **No code ever sets them**
- `update_instance_status()` only handles `in_progress`, `completed`, `completed_pending_signoff`

**Expected Behavior:**
- When current time > `due_time` (or `period_end`) and status is still `active`/`in_progress` → transition to `overdue`
- When period ends and instance is `overdue` → transition to `missed` (unless `expiration_behavior` says otherwise)

**Fix Location:**
- `app/domain/chores/services.py` → Add `check_overdue_instances()` method
- Call it in `get_all_chores()` or via cron

---

### Gap 5: Frontend/Backend Status Enum Mismatch (P2)

**Frontend Types (`dashy-kiosk-v2/src/types/chores.ts`):**
```typescript
type InstanceStatus = 
  | 'open'           //  Backend doesn't have this
  | 'claimed'        // ❌ Backend doesn't have this
  | 'assigned'       // ❌ Backend doesn't have this
  | 'in_progress'    // ✅ Matches
  | 'completed_pending_signoff' // ✅ Matches
  | 'completed'      // ✅ Matches
  | 'overdue'        // ✅ Matches
  | 'expiring_soon'  // ❌ Backend doesn't have this
```

**Backend Enum (`app/domain/chores/models.py`):**
```python
class InstanceStatus(StrEnum):
    ACTIVE = "active"                    # ❌ Frontend doesn't have this
    IN_PROGRESS = "in_progress"          // ✅ Matches
    COMPLETED_PENDING_SIGNOFF = "completed_pending_signoff" // ✅ Matches
    COMPLETED = "completed"              // ✅ Matches
    OVERDUE = "overdue"                  // ✅ Matches
    MISSED = "missed"                    // ❌ Frontend doesn't have this
    ARCHIVED = "archived"                // ❌ Frontend doesn't have this
```

**Analysis:**
The frontend uses **derived UI states** (`open`, `claimed`, `assigned`) based on `claimed_by`/`assigned_to` fields. This is actually correct UI-wise — the board needs to know if a chore is in the open pool vs. claimed vs. assigned. But the type names are misleading because they suggest these are stored DB states.

**Recommended Fix:**
- Keep backend enum as-is (`active`, `missed`, `archived`)
- Rename frontend type to clarify these are UI states: `InstanceUIState` or `InstanceBoardState`
- Document that `open`/`claimed`/`assigned` are derived from `claimed_by`/`assigned_to` fields
- Add `missed` and `archived` to frontend enum for completeness

---

### Gap 6: `claimable_by` Field Missing (P3)

**Spec Reference:** `docs/chores-spec.md` §4 — "Open pool chores can optionally have a `claimable_by` field restricting who can claim them"

**Current Behavior:**
- Not in domain model
- Not in DB schema
- Not in API

**Impact:** Can't restrict who can claim a chore (e.g., "only kids can claim this")

**Priority:** Deferred per spec §10 — "What's NOT in v1"

---

## Database State (as of 2026-08-25)

```
=== CATEGORIES (5) ===
  cat-bathroom: Bathroom
  cat-general: General
  cat-kitchen: Kitchen
  cat-laundry: Laundry
  cat-outdoor: Outdoor

=== TAGS (0) ===

=== MASTER CHORES (0) ===

=== INSTANCES (0) ===
```

**Note:** Migration `b3e7f2a19c45_create_chores_tables.py` ran successfully and seeded 5 categories. No "Bedroom" category exists in the DB — if the frontend shows "Bedroom", it's a frontend caching bug.

---

## Implementation Plan (Recommended Order)

### Phase 1: Core Instance Generation (P0)

1. **Add instance generation to `create_master_chore()`**
   - File: `app/domain/chores/services.py`
   - Method: `create_master_chore()` → after creating master, call `generate_instances_for_master(chore)`
   - Logic:
     - `once` → Create one instance, `period_start=None`, `period_end=None`
     - `daily` → Create instance for today, `period_start=today`, `period_end=today`
     - `weekly` → Create instance for current week (Mon-Sun)
     - `monthly` → Create instance for current month (1st-last day)

2. **Add on-demand generation to `get_all_chores()`**
   - File: `app/api/routes/chores.py`
   - Method: `get_all_chores()` → before returning data, call `generate_instances_for_period(today, today)` for daily, `generate_instances_for_period(monday, sunday)` for weekly, etc.
   - Ensures board always shows current instances

3. **Add `generate_instances_for_master()` method**
   - File: `app/domain/chores/services.py`
   - Signature: `async def generate_instances_for_master(self, master: MasterChore, period_start: date, period_end: date) -> ChoreInstance`
   - Logic: Check if instance exists for this period → if not, create it

### Phase 2: Expiration & Rollover (P1)

4. **Add `process_expired_instances()` method**
   - File: `app/domain/chores/services.py`
   - Logic: Query instances where `period_end < today` and status != `completed`
   - Apply `expiration_behavior` from parent master chore
   - Call in `get_all_chores()` or via cron

5. **Add `check_overdue_instances()` method**
   - File: `app/domain/chores/services.py`
   - Logic: Query instances where `due_time < now` or `period_end < now` and status is `active`/`in_progress`
   - Transition to `overdue`
   - Call in `get_all_chores()` or via cron

### Phase 3: Frontend Alignment (P2)

6. **Fix frontend status enum**
   - File: `dashy-kiosk-v2/src/types/chores.ts`
   - Rename `InstanceStatus` to `InstanceUIState` (or add comment clarifying derived states)
   - Add `missed` and `archived` to enum
   - Update components to handle new states

7. **Fix category caching bug**
   - Investigate why "Bedroom" appears in frontend when DB only has 5 categories
   - Likely a stale cache or hardcoded fallback

---

## Files to Modify

| File | Changes |
|------|---------|
| `app/domain/chores/services.py` | Add `generate_instances_for_master()`, `generate_instances_for_period()`, `process_expired_instances()`, `check_overdue_instances()` |
| `app/api/routes/chores.py` | Call instance generation in `create_master_chore()` and `get_all_chores()` |
| `app/domain/chores/ports.py` | Add new methods to `ChoresRepository` protocol if needed |
| `app/infrastructure/persistence/chores_repository.py` | Implement new repository methods |
| `dashy-kiosk-v2/src/types/chores.ts` | Fix status enum, add `missed`/`archived` |
| `dashy-kiosk-v2/src/shared/utils/chores.ts` | Update `isOpenPoolInstance()` to handle new statuses |

---

## Testing Strategy

### Unit Tests
- `tests/unit/domain/chores/test_services.py`
  - Test instance generation for each frequency
  - Test expiration behaviors
  - Test overdue transitions

### Integration Tests
- `tests/integration/chores/test_repository.py`
  - Test instance CRUD
  - Test period-based queries

### API Tests
- `tests/api/test_chores.py`
  - Test `POST /masters` creates instance
  - Test `GET /chores` returns instances
  - Test expiration logic

---

## Open Questions

1. **Cron vs. On-Demand:** Should instance generation run on a schedule (cron) or on-demand (when board loads)?
   - **Recommendation:** On-demand for v1, cron for v2
   - On-demand is simpler and ensures data is always fresh
   - Cron is more efficient but requires infrastructure (Celery, cron job, etc.)

2. **Period Boundaries for Weekly:** Spec says "configurable start day (default: Monday)" — should this be a setting or hardcoded?
   - **Recommendation:** Hardcode Monday for v1, make configurable in v2

3. **Multiple Instances per Period:** Can a master chore have multiple instances in the same period (e.g., if someone manually triggers generation)?
   - **Recommendation:** No — enforce uniqueness via DB constraint `(master_chore_id, period_start, period_end)`

4. **Backfilling:** If a master chore is created mid-week with `frequency: "daily"`, should we backfill instances for earlier days in the week?
   - **Recommendation:** No — only generate from today forward

---

## References

- Spec: `docs/chores-spec.md`
- Architecture: `docs/plans/CHORES-ARCHITECTURE.md`
- Frontend types: `dashy-kiosk-v2/src/types/chores.ts`
- Backend models: `app/domain/chores/models.py`
- Backend services: `app/domain/chores/services.py`
- Backend routes: `app/api/routes/chores.py`
- Migration: `alembic/versions/b3e7f2a19c45_create_chores_tables.py`
