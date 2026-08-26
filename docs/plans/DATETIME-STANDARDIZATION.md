# Project-Wide Date/Time Standardization

**Status:** Planned  
**Created:** 2026-08-26  
**Scope:** All modules (weather, calendar, family, chores already done)

---

## Overview

Standardize all date/time handling across the entire Dashy project to follow industry best practices. The chores module has already been updated as part of Phase 1. This plan covers the remaining modules.

---

## Current State

### ✅ Completed (Chores Module)
- All `datetime.utcnow()` → `datetime.now(UTC)`
- All `.isoformat()` → `.isoformat(timespec="seconds") + "Z"`
- Timezone-aware UTC throughout
- Consistent ISO 8601 wire format with `Z` suffix

### ❌ Remaining Issues

#### Backend
1. **Weather module** (`app/infrastructure/weather/`)
   - Uses `datetime.utcnow()` in adapters
   - Inconsistent timezone handling (OWM adapter uses local timezone from API)

2. **Calendar module** (`app/domain/calendar/`, `app/infrastructure/calendar/`)
   - `get_default_week_dates()` uses `datetime.now()` (naive local time)
   - Google Calendar adapter passes through timezone-aware strings without normalization
   - Mixed timezone bases (UTC vs local)

3. **Family module** (`app/infrastructure/persistence/models.py`)
   - `FamilyMemberDB.date_of_birth` is `date` type (correct)
   - `created_at`/`updated_at` use `datetime.utcnow()` (needs fix)

4. **Database columns**
   - Some temporal fields stored as `TEXT` (VARCHAR) instead of proper `DateTime` columns
   - Examples: `period_start`, `period_end`, `due_date`, `end_date` in chores
   - Should migrate to `sa.Date()` for date-only fields

#### Frontend
1. **Legacy `Date` usage** (2 locations)
   - `WeatherPopup.tsx:233` — uses `new Date(hour.time)`
   - `family.ts:20-21` — uses `new Date()` for age calculation
   - Should use Temporal API (`parseWeatherTime()`, `Temporal.Now.plainDateISO()`)

2. **Inconsistent parsing**
   - Some components parse ISO strings, others don't
   - Need consistent use of `parse.ts` utilities

---

## Implementation Plan

### Phase 1: Backend Standardization

#### 1.1 Weather Module
**Files:** `app/infrastructure/weather/owm_adapter.py`, `app/infrastructure/weather/mock_adapter.py`

**Changes:**
- Replace `datetime.utcnow()` → `datetime.now(UTC)`
- Normalize all timestamps to UTC before serialization
- Ensure OWM adapter converts local timezone to UTC
- Update wire format to use `Z` suffix

**Migration:** None needed (no schema changes)

#### 1.2 Calendar Module
**Files:** `app/domain/calendar/services.py`, `app/infrastructure/calendar/`

**Changes:**
- Fix `get_default_week_dates()` to use `datetime.now(UTC)` instead of `datetime.now()`
- Normalize Google Calendar event times to UTC
- Update serialization to use consistent ISO 8601 with `Z`

**Migration:** None needed

#### 1.3 Family Module
**Files:** `app/infrastructure/persistence/models.py`

**Changes:**
- Update `FamilyMemberDB.created_at`/`updated_at` defaults to `lambda: datetime.now(UTC)`

**Migration:** None needed (existing data unaffected)

#### 1.4 Database Schema Migration
**Goal:** Convert TEXT date columns to proper `Date`/`DateTime` types

**Affected tables:**
- `master_chores`: `end_date`, `due_date` → `sa.Date()`
- `chore_instances`: `period_start`, `period_end` → `sa.Date()`
- `chore_instances`: `started_at`, `completed_at` → `sa.DateTime(timezone=True)`

**Migration strategy:**
1. Create new columns with correct types
2. Copy data from old TEXT columns (parse ISO strings)
3. Drop old columns
4. Rename new columns to original names

**Risk:** Data loss if parsing fails. Must validate all existing data before migration.

---

### Phase 2: Frontend Standardization

#### 2.1 Fix Legacy `Date` Usage
**Files:**
- `dashy-kiosk/src/features/weather/components/WeatherPopup.tsx`
- `dashy-kiosk/src/shared/utils/family.ts`

**Changes:**
- Replace `new Date(hour.time)` with `parseWeatherTime(hour.time)` + `formatTime()`
- Replace `new Date(member.date_of_birth)` with `Temporal.PlainDate.from()`
- Replace `new Date()` with `Temporal.Now.plainDateISO()`

#### 2.2 Consistent Parsing
**Files:** All components using date/time data

**Changes:**
- Audit all date field usage
- Ensure all ISO strings go through `parse.ts` utilities
- Remove any direct `Date` constructor usage

---

### Phase 3: Configuration

#### 3.1 Add Timezone Config
**File:** `app/config.py`

**Changes:**
```python
class Settings(BaseSettings):
    # ... existing settings ...
    TIMEZONE: str = "UTC"  # Default to UTC, can override in .env
```

**Usage:**
- Use `zoneinfo.ZoneInfo(settings.TIMEZONE)` for local time conversions
- Display layer converts UTC to user's timezone
- All storage and computation in UTC

---

## Testing Strategy

### Backend Tests
1. **Unit tests** for timezone conversions
2. **Integration tests** for database migrations
3. **API tests** to verify wire format consistency

### Frontend Tests
1. **Unit tests** for date parsing/formatting
2. **Component tests** to verify display in user's timezone

---

## Migration Checklist

- [ ] Weather module: Replace `datetime.utcnow()`
- [ ] Weather module: Normalize to UTC
- [ ] Calendar module: Fix `get_default_week_dates()`
- [ ] Calendar module: Normalize Google Calendar times
- [ ] Family module: Update DB model defaults
- [ ] Database: Create migration for TEXT → Date/DateTime columns
- [ ] Database: Test migration with sample data
- [ ] Frontend: Fix `WeatherPopup.tsx`
- [ ] Frontend: Fix `family.ts`
- [ ] Frontend: Audit all date field usage
- [ ] Config: Add `TIMEZONE` setting
- [ ] Tests: Add timezone conversion tests
- [ ] Tests: Add migration tests
- [ ] Docs: Update API documentation with wire format spec

---

## Wire Format Specification

### Timestamps (DateTime)
- **Format:** ISO 8601 with `Z` suffix
- **Precision:** Seconds (no microseconds)
- **Example:** `"2026-08-26T19:30:00Z"`
- **Timezone:** Always UTC

### Dates (Date-only)
- **Format:** ISO 8601 date
- **Example:** `"2026-08-26"`
- **No time component**

### Times (Time-only)
- **Format:** 24-hour HH:MM
- **Example:** `"18:00"`
- **No seconds, no timezone**

---

## Success Criteria

- [ ] Zero `datetime.utcnow()` calls in backend
- [ ] Zero `new Date()` calls in frontend (except polyfill)
- [ ] All API responses use consistent ISO 8601 with `Z`
- [ ] All database temporal fields use proper column types
- [ ] Timezone configurable via `.env`
- [ ] All tests pass
- [ ] No data loss during migration

---

## Notes

- **Chores module already compliant** — use as reference implementation
- **Backward compatibility** — frontend must handle both old (microseconds, no `Z`) and new formats during transition
- **Migration timing** — coordinate with frontend deployment to avoid breaking changes
- **Monitoring** — log any parsing errors during transition period
