# Task 04: Integration Testing — Persistence Verification

> **Status**: ⚪ Not Started
> **Parent Goal**: [12-Postgres-Persistence](../scratchpad.md)
> **Depends On**: [Task-02-LangGraph-Checkpointer](../Task-02-LangGraph-Checkpointer/scratchpad.md), [Task-03-Robyn-Storage-Postgres](../Task-03-Robyn-Storage-Postgres/scratchpad.md)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11

## Objective

Verify that the complete Postgres persistence integration works end-to-end. This includes:
1. LangGraph checkpointer — conversation memory persists across server restarts
2. LangGraph store — cross-thread memory available
3. Robyn runtime storage — assistants, threads, runs, crons, store items survive restarts
4. Backward compatibility — in-memory fallback works when `DATABASE_URL` is not set

## Test Strategy

### Layer 1: LangGraph Checkpointer Tests

#### 1a. Short-term memory (thread-level persistence)

- [ ] **Multi-turn conversation**: Send "My name is Alice" → restart server → send "What's my name?" on same thread → agent responds "Alice"
- [ ] **Thread isolation**: Thread A has user "Alice", Thread B has user "Bob" → each thread returns correct name
- [ ] **Thread history**: `GET /threads/{thread_id}/history` returns multiple state snapshots ordered by time
- [ ] **Empty thread**: New thread with no messages returns empty state

#### 1b. Checkpoint table verification

- [ ] After first agent run, verify checkpoint tables exist in Postgres:
  ```sql
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'public'
  AND table_name LIKE 'checkpoint%';
  ```
- [ ] After a multi-turn conversation, verify multiple checkpoint rows exist for the thread
- [ ] Verify checkpoint data contains serialized messages

### Layer 2: LangGraph Store Tests

#### 2a. Cross-thread memory

- [ ] Store an item via agent in Thread A → access it from Thread B with same user namespace
- [ ] Verify store tables exist after `.setup()` runs
- [ ] Namespace isolation — user A's memories not visible to user B

#### 2b. Store table verification

- [ ] After `.setup()`, verify store tables exist in Postgres
- [ ] After a put operation, verify data in the store table

### Layer 3: Robyn Runtime Storage Tests

#### 3a. Assistants persistence

- [ ] `POST /assistants` → restart server → `GET /assistants` returns the created assistant
- [ ] `PATCH /assistants/{id}` → restart → changes persist
- [ ] `DELETE /assistants/{id}` → restart → assistant is gone
- [ ] Owner isolation: User A's assistants not visible to User B

#### 3b. Threads persistence

- [ ] `POST /threads` → restart → `GET /threads/{id}` returns the thread
- [ ] Thread state snapshots persist across restarts
- [ ] Thread deletion cascades to state snapshots and runs

#### 3c. Runs persistence

- [ ] Run created via streaming persists with correct status
- [ ] `GET /threads/{thread_id}/runs` returns runs after restart
- [ ] Run status transitions tracked (pending → running → success/error)

#### 3d. Store items persistence

- [ ] `PUT /store/items` → restart → `GET /store/items` returns the item
- [ ] Namespace listing works with Postgres backend
- [ ] Search within namespace returns matching items

#### 3e. Crons persistence

- [ ] `POST /crons` → restart → `GET /crons` returns the cron
- [ ] Cron schedule and configuration preserved across restarts

#### 3f. Schema verification

- [ ] `langgraph_server` schema exists with all five tables
- [ ] Indexes exist on key columns (thread_id, created_at, etc.)
- [ ] All tables have correct column types and constraints

### Layer 4: Backward Compatibility Tests

#### 4a. In-memory fallback

- [ ] Unset `DATABASE_URL` → server starts without errors
- [ ] All CRUD operations work with in-memory storage
- [ ] No Postgres connection attempts when `DATABASE_URL` is not set
- [ ] Server logs indicate "using in-memory storage"

#### 4b. Graceful degradation

- [ ] Set `DATABASE_URL` to unreachable host → server starts with warning, falls back to in-memory
- [ ] Or: server fails fast with a clear error message (decide which behavior is preferred)

## Automated Test Plan

### Unit Tests (pytest)

Tests that run without a real Postgres instance (mocked or in-memory):

```python
# test_database.py — DB module tests
class TestDatabaseModule:
    async def test_initialize_without_database_url(self):
        """initialize_database() returns False when DATABASE_URL not set."""

    async def test_is_postgres_enabled_false_by_default(self):
        """is_postgres_enabled() returns False before initialization."""

    async def test_get_checkpointer_none_without_init(self):
        """get_checkpointer() returns None before initialization."""

    async def test_get_store_none_without_init(self):
        """get_store() returns None before initialization."""
```

### Integration Tests (pytest, requires Postgres)

Tests that require a running Postgres instance. Mark with `@pytest.mark.postgres`:

```python
# test_postgres_integration.py
import pytest

@pytest.mark.postgres
class TestPostgresIntegration:
    async def test_initialize_with_database_url(self, supabase_postgres_url):
        """initialize_database() connects to real Postgres."""

    async def test_checkpointer_setup_creates_tables(self, supabase_postgres_url):
        """checkpointer.setup() creates checkpoint tables."""

    async def test_store_setup_creates_tables(self, supabase_postgres_url):
        """store.setup() creates store tables."""

@pytest.mark.postgres
class TestPostgresAssistantStore:
    async def test_create_and_get(self, postgres_storage):
        """Create assistant, get it back."""

    async def test_owner_isolation(self, postgres_storage):
        """User A can't see User B's assistants."""

    async def test_list_with_filters(self, postgres_storage):
        """List assistants with metadata filters."""

    async def test_update(self, postgres_storage):
        """Update assistant config and metadata."""

    async def test_delete(self, postgres_storage):
        """Delete assistant, verify it's gone."""

@pytest.mark.postgres
class TestPostgresThreadStore:
    async def test_create_and_get(self, postgres_storage):
        """Create thread, get it back."""

    async def test_state_snapshots(self, postgres_storage):
        """Add state snapshots, retrieve history."""

    async def test_delete_cascades(self, postgres_storage):
        """Delete thread cascades to states and runs."""

# ... similar test classes for RunStore, StoreStorage, CronStore
```

### Pytest Configuration

```python
# conftest.py additions
import os
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "postgres: requires Postgres instance")

@pytest.fixture
def supabase_postgres_url():
    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres?sslmode=disable")
    return url

@pytest.fixture
async def postgres_storage(supabase_postgres_url):
    """Create a PostgresStorage instance for testing, clean up after."""
    # Initialize pool, create storage, run migrations
    # yield storage
    # Truncate all langgraph_server.* tables
```

### Running Tests

```bash
# Unit tests only (no Postgres needed)
uv run pytest -m "not postgres"

# All tests (requires running Supabase stack)
DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres?sslmode=disable" \
  uv run pytest

# Just Postgres integration tests
DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres?sslmode=disable" \
  uv run pytest -m postgres -v
```

## Manual Verification Procedure

### Restart Persistence Test

1. Start Supabase stack (`supabase start`)
2. Set `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres?sslmode=disable`
3. Start Robyn server: `uv run python -m robyn_server`
4. Create an assistant via `POST /assistants`
5. Create a thread via `POST /threads`
6. Send a streaming message via `POST /threads/{thread_id}/runs/stream`
7. Verify SSE events arrive correctly
8. **Stop the Robyn server** (Ctrl+C)
9. **Restart the Robyn server**
10. `GET /assistants` → verify assistant still exists
11. `GET /threads/{thread_id}` → verify thread still exists
12. Send another message on the same thread → verify agent remembers context from step 6

### Database Inspection

After running the manual test, connect to Postgres and inspect:

```bash
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

```sql
-- Check langgraph_server schema
\dn langgraph_server

-- List runtime tables
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'langgraph_server';

-- Check assistants
SELECT id, graph_id, metadata->>'owner' as owner, created_at
FROM langgraph_server.assistants;

-- Check threads
SELECT id, metadata->>'owner' as owner, created_at
FROM langgraph_server.threads;

-- Check runs
SELECT id, thread_id, status, created_at
FROM langgraph_server.runs;

-- Check LangGraph checkpoint tables
SELECT table_name FROM information_schema.tables
WHERE table_name LIKE 'checkpoint%' OR table_name LIKE 'store%';

-- Check checkpoint data for a thread
SELECT * FROM checkpoints WHERE thread_id = '<thread_id>' LIMIT 5;
```

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `robyn_server/tests/test_database.py` | **CREATE** | Unit tests for database module |
| `robyn_server/tests/test_postgres_storage.py` | **CREATE** | Integration tests for Postgres-backed stores |
| `robyn_server/tests/test_postgres_integration.py` | **CREATE** | End-to-end persistence tests |
| `robyn_server/tests/conftest.py` | MODIFY | Add Postgres fixtures, markers |

## Acceptance Criteria

- [ ] All unit tests pass without Postgres (`pytest -m "not postgres"`)
- [ ] All integration tests pass with Postgres (`pytest -m postgres`)
- [ ] Manual restart persistence test succeeds (data survives restart)
- [ ] Conversation memory verified across restarts (LangGraph checkpointer)
- [ ] In-memory fallback verified (no `DATABASE_URL` → works as before)
- [ ] Coverage remains ≥73% per project rules
- [ ] `ruff check` and `ruff format` pass
- [ ] `langgraph_server` schema and tables verified in Postgres
- [ ] LangGraph checkpoint/store tables verified in Postgres
- [ ] Goal 12 scratchpad updated to 🟢 Complete

## Performance Baseline (Optional)

If time permits, capture basic performance metrics to establish a baseline:

- [ ] Time to create 100 assistants (Postgres vs in-memory)
- [ ] Time to create 100 threads (Postgres vs in-memory)
- [ ] Streaming latency with checkpointer enabled vs disabled
- [ ] Connection pool utilization under concurrent requests

This is not a hard requirement but useful data for future optimization.

## Notes

- The Supabase local Postgres instance must be running for integration tests. Ensure `supabase start` has been run before testing.
- Integration tests should clean up after themselves (TRUNCATE tables in teardown fixtures) to ensure test isolation.
- The pytest markers allow running just unit tests in CI (where Postgres may not be available) and full integration tests locally or in staging.
- Consider adding a `--postgres` CLI flag or checking for `DATABASE_URL` env var to auto-skip Postgres tests when the DB is not available.
- The LangGraph checkpoint table names may vary by version of `langgraph-checkpoint-postgres`. Don't hardcode specific table names in assertions — query `information_schema.tables` dynamically.