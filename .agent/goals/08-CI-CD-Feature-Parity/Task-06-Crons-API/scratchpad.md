# Task 06 — Crons API Implementation

> Implement scheduled cron jobs for recurring agent runs with APScheduler.

---

## Status: 🟢 Complete

---

## Objective

Implement the Crons API to enable scheduled recurring runs on LangGraph threads. This matches the LangGraph FastAPI Plus tier feature.

---

## API Endpoints to Implement

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/runs/crons` | POST | Create a cron job |
| `/runs/crons/search` | POST | Search cron jobs |
| `/runs/crons/count` | POST | Count cron jobs |
| `/runs/crons/{cron_id}` | DELETE | Delete a cron job |

---

## Schema Summary (from OpenAPI spec)

### Cron (Response Model)
```python
{
    "cron_id": str (uuid),        # Required
    "assistant_id": str | None,   # Optional
    "thread_id": str (uuid),      # Required
    "end_time": datetime,         # Required
    "schedule": str,              # Required (cron expression)
    "created_at": datetime,       # Required
    "updated_at": datetime,       # Required
    "user_id": str | None,        # Optional
    "payload": dict,              # Required (run config)
    "next_run_date": datetime | None,  # Optional
    "metadata": dict              # Optional
}
```

### CronCreate (Request Model)
```python
{
    "schedule": str,              # Required (cron expression)
    "assistant_id": str,          # Required (uuid or graph name)
    "end_time": datetime | None,  # Optional
    "input": list | dict | None,  # Optional
    "metadata": dict | None,      # Optional
    "config": dict | None,        # Optional (tags, recursion_limit, configurable)
    "context": dict | None,       # Optional
    "webhook": str | None,        # Optional (URI)
    "interrupt_before": str | list | None,  # Optional
    "interrupt_after": str | list | None,   # Optional
    "on_run_completed": "delete" | "keep"   # Default: "delete"
}
```

### CronSearch (Request Model)
```python
{
    "assistant_id": str | None,   # Filter by assistant
    "thread_id": str | None,      # Filter by thread
    "limit": int,                 # Default: 10, max: 1000
    "offset": int,                # Default: 0
    "sort_by": str,               # Default: "created_at"
    "sort_order": "asc" | "desc", # Default: "desc"
    "select": list[str] | None    # Field projection
}
```

### CronCountRequest (Request Model)
```python
{
    "assistant_id": str | None,   # Filter by assistant
    "thread_id": str | None       # Filter by thread
}
```

---

## Implementation Plan

### 1. Add APScheduler Dependency
```bash
uv add apscheduler
```

### 2. Create Module Structure
```
robyn_server/crons/
├── __init__.py       # Exports
├── schemas.py        # Pydantic models
├── handlers.py       # Business logic
└── scheduler.py      # APScheduler wrapper
```

### 3. Add CronStore to Storage
Extend `robyn_server/storage.py` with CronStore class.

### 4. Create Route Handlers
Add `robyn_server/routes/crons.py` following A2A pattern.

### 5. Register Routes
Update `robyn_server/app.py` to register cron routes.

### 6. Update OpenAPI Spec
Add crons endpoints to `robyn_server/openapi_spec.py`.

### 7. Write Tests
Create `robyn_server/tests/test_crons.py` with:
- Unit tests for schemas
- Unit tests for handlers
- Integration tests for routes
- Scheduler tests

---

## Files Created

- [x] `robyn_server/crons/__init__.py`
- [x] `robyn_server/crons/schemas.py`
- [x] `robyn_server/crons/handlers.py`
- [x] `robyn_server/crons/scheduler.py`
- [x] `robyn_server/routes/crons.py`
- [x] `robyn_server/tests/test_crons.py`

## Files Modified

- [x] `robyn_server/storage.py` - Added CronStore
- [x] `robyn_server/app.py` - Registered routes, updated capabilities
- [x] `robyn_server/openapi_spec.py` - Added endpoints and schemas
- [x] `robyn_server/routes/__init__.py` - Export register function
- [x] `pyproject.toml` / `uv.lock` - Added apscheduler, croniter dependencies

---

## Technical Notes

### Cron Expression Parsing
Use `croniter` library (included with APScheduler) to:
- Validate cron expressions
- Calculate `next_run_date`

### on_run_completed Behavior
- `"delete"`: Delete thread after each run (stateless cron)
- `"keep"`: Create new thread for each execution, don't clean up

### Scheduler Design
- Background async scheduler using APScheduler
- Store cron definitions in memory (CronStore)
- On server startup, reload and reschedule active crons
- Graceful shutdown: stop scheduler, persist state

### Thread Management
For stateless crons (on_run_completed: "delete"):
1. Create temporary thread
2. Execute run
3. Delete thread on completion

For stateful crons (on_run_completed: "keep"):
1. Create new thread per execution
2. Keep all threads

---

## Success Criteria

- [x] All 4 cron endpoints implemented and working
- [x] Cron jobs scheduled via APScheduler
- [x] next_run_date calculated correctly
- [x] on_run_completed: "delete" vs "keep" supported
- [x] Search/filter/sort works correctly
- [x] OpenAPI spec updated with all schemas and endpoints
- [x] Tests passing (58 tests)
- [x] Ruff lint clean
- [x] All 426 robyn_server tests passing

---

## Progress Log

### Session Start
- Created task directory and scratchpad
- Analyzed OpenAPI spec for Crons API
- Reviewed A2A module pattern for reference

### Implementation Complete
- Added dependencies: `apscheduler`, `croniter`
- Created `robyn_server/crons/` module:
  - `schemas.py`: Cron, CronCreate, CronSearch, CronCountRequest, helpers
  - `handlers.py`: CronHandler with create/search/count/delete
  - `scheduler.py`: APScheduler wrapper (AsyncIOScheduler)
  - `__init__.py`: Module exports
- Created `robyn_server/routes/crons.py`: 4 HTTP endpoints
- Added `CronStore` to `robyn_server/storage.py`
- Updated `robyn_server/app.py`: registered routes, capabilities.crons=true
- Updated `robyn_server/openapi_spec.py`: Added Crons tag, schemas, paths
- Created 58 comprehensive tests in `test_crons.py`
- All 426 robyn_server tests passing

---

## References

- `.agent/tmp/langgraph-serve_openape_spec.json` L2150-2571 (Crons endpoints)
- `.agent/tmp/langgraph-serve_openape_spec.json` L3537-3810 (Cron schemas)
- `robyn_server/a2a/` - Reference module structure
- `robyn_server/storage.py` - BaseStore pattern
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)