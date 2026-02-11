# Task 03: Robyn Storage → Postgres

> **Status**: ⚪ Not Started
> **Parent Goal**: [12-Postgres-Persistence](../scratchpad.md)
> **Depends On**: [Task-01-Dependencies-DB-Module](../Task-01-Dependencies-DB-Module/scratchpad.md)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11

## Objective

Replace the in-memory storage layer in `robyn_server/storage.py` with Postgres-backed implementations. All five stores (AssistantStore, ThreadStore, RunStore, StoreStorage, CronStore) must be reimplemented to use the Postgres instance via `psycopg` async queries. The existing `Storage` interface and `get_storage()` accessor must remain unchanged so that **zero route handler changes** are needed.

## Background

### Current In-Memory Architecture

`robyn_server/storage.py` contains:

| Class | Purpose | Data Structure |
|-------|---------|---------------|
| `BaseStore(Generic[T])` | Generic CRUD with owner isolation | `dict[str, dict[str, Any]]` |
| `AssistantStore(BaseStore)` | Assistants — agent configs, graph IDs | Inherits from BaseStore |
| `ThreadStore(BaseStore)` | Threads — conversation containers + state snapshots | BaseStore + `_state_history: dict` |
| `RunStore(BaseStore)` | Runs — execution tracking per thread | Inherits from BaseStore |
| `StoreStorage` | Key-value store — namespaced items | `dict[tuple, StoreItem]` |
| `CronStore(BaseStore)` | Cron jobs — scheduled task definitions | Inherits from BaseStore |
| `Storage` | Container — holds all five stores | Instantiates all stores |

All operations enforce **owner isolation** via `metadata.owner` filtering. Data lives in Python dicts and is lost on restart.

### Target: Postgres in `langgraph_server` Schema

Each store maps to a table in the `langgraph_server` Postgres schema:

| Store | Table | Key Columns |
|-------|-------|-------------|
| `AssistantStore` | `langgraph_server.assistants` | `id`, `graph_id`, `config`, `metadata`, `created_at`, `updated_at` |
| `ThreadStore` | `langgraph_server.threads` + `langgraph_server.thread_states` | `id`, `metadata`, `values`, `created_at`, `updated_at` |
| `RunStore` | `langgraph_server.runs` | `id`, `thread_id`, `assistant_id`, `status`, `metadata`, `created_at`, `updated_at` |
| `StoreStorage` | `langgraph_server.store_items` | `namespace`, `key`, `value`, `created_at`, `updated_at` |
| `CronStore` | `langgraph_server.crons` | `id`, `assistant_id`, `schedule`, `metadata`, `created_at`, `updated_at` |

## Implementation Plan

### Step 1: Create DDL Migration for `langgraph_server` Schema

Idempotent DDL that can run on every startup:

```sql
CREATE SCHEMA IF NOT EXISTS langgraph_server;

CREATE TABLE IF NOT EXISTS langgraph_server.assistants (
    id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS langgraph_server.threads (
    id TEXT PRIMARY KEY,
    metadata JSONB NOT NULL DEFAULT '{}',
    values JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS langgraph_server.thread_states (
    id SERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES langgraph_server.threads(id) ON DELETE CASCADE,
    values JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    next TEXT[] NOT NULL DEFAULT '{}',
    tasks JSONB NOT NULL DEFAULT '[]',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint JSONB,
    interrupts JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_thread_states_thread_id
    ON langgraph_server.thread_states(thread_id, created_at DESC);

CREATE TABLE IF NOT EXISTS langgraph_server.runs (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    assistant_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    metadata JSONB NOT NULL DEFAULT '{}',
    config JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_runs_thread_id
    ON langgraph_server.runs(thread_id, created_at DESC);

CREATE TABLE IF NOT EXISTS langgraph_server.store_items (
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (namespace, key)
);

CREATE TABLE IF NOT EXISTS langgraph_server.crons (
    id TEXT PRIMARY KEY,
    assistant_id TEXT NOT NULL,
    schedule TEXT NOT NULL,
    input JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Step 2: Create `robyn_server/postgres_storage.py`

New module that implements Postgres-backed versions of each store class. Each class mirrors the interface of its in-memory counterpart but uses `psycopg` async queries via the connection pool from `database.py`.

#### Design Principles

1. **Same method signatures** — every public method in `BaseStore`, `AssistantStore`, `ThreadStore`, etc. has a matching async Postgres implementation
2. **Owner isolation via SQL WHERE** — replace Python dict filtering with `WHERE metadata->>'owner' = $1`
3. **JSONB for flexible data** — `config`, `metadata`, `values` stored as JSONB columns
4. **Pydantic model conversion** — `_to_model()` methods convert DB rows to the same Pydantic models
5. **Connection pool from `database.py`** — each store receives the pool in its constructor

#### Example: `PostgresAssistantStore`

```python
class PostgresAssistantStore:
    """Postgres-backed assistant store with owner isolation."""

    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def create(self, data: dict[str, Any], owner_id: str) -> Assistant:
        assistant_id = generate_id()
        now = utc_now()
        metadata = {**data.get("metadata", {}), "owner": owner_id}
        config = data.get("config", {})
        graph_id = data.get("graph_id", "agent")

        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO langgraph_server.assistants
                    (id, graph_id, config, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (assistant_id, graph_id, Json(config), Json(metadata), now, now),
            )

        return self._to_model(assistant_id, graph_id, config, metadata, now, now)

    async def get(self, assistant_id: str, owner_id: str) -> Assistant | None:
        async with self._pool.connection() as conn:
            row = await conn.execute(
                """
                SELECT id, graph_id, config, metadata, created_at, updated_at
                FROM langgraph_server.assistants
                WHERE id = %s AND metadata->>'owner' = %s
                """,
                (assistant_id, owner_id),
            ).fetchone()

        if not row:
            return None
        return self._to_model(*row)

    # ... list, update, delete, count, clear follow the same pattern
```

### Step 3: Create `PostgresStorage` Container

```python
class PostgresStorage:
    """Postgres-backed container for all resource stores."""

    def __init__(self, pool: AsyncConnectionPool):
        self.assistants = PostgresAssistantStore(pool)
        self.threads = PostgresThreadStore(pool)
        self.runs = PostgresRunStore(pool)
        self.store = PostgresStoreStorage(pool)
        self.crons = PostgresCronStore(pool)

    async def run_migrations(self) -> None:
        """Run DDL migrations (idempotent)."""
        # Execute the CREATE SCHEMA / CREATE TABLE DDL

    def clear_all(self) -> None:
        """Clear all stores (for testing only)."""
        # TRUNCATE langgraph_server.* tables
```

### Step 4: Modify `get_storage()` in `storage.py`

```python
def get_storage() -> Storage | PostgresStorage:
    """Get the global storage instance.

    Returns PostgresStorage if DATABASE_URL is configured,
    otherwise returns in-memory Storage.
    """
    global _storage
    if _storage is None:
        if is_postgres_enabled():
            pool = get_pool()
            _storage = PostgresStorage(pool)
        else:
            _storage = Storage()
    return _storage
```

### Step 5: Handle Async Mismatch

**Critical issue**: The current in-memory stores use synchronous methods (plain `def`), but Postgres operations are inherently async (`async def`). The Robyn route handlers are already `async`, so they can `await` store methods.

**Options**:

A. **Make all store methods async** — change in-memory stores to `async def` too (trivially, since they don't do I/O). Update all route handler call sites to `await storage.assistants.create(...)`.
   - ✅ **Recommended** — clean, consistent, forward-compatible
   - Impact: All route handlers need `await` added to storage calls

B. **Use `asyncio.run()` wrapper in Postgres stores** — keep sync interface, run async queries synchronously.
   - ❌ Bad — blocks the event loop, defeats the purpose of async

C. **Use a Protocol/ABC with both sync and async variants** — complex, over-engineered.
   - ❌ Unnecessary complexity

**Decision**: Option A — make all store methods async. This requires updating route handlers to `await` storage calls, but since they're already `async` functions, this is a mechanical change (add `await` keyword).

### Step 6: Update Route Handlers

Every route handler that calls storage methods needs `await` added:

```python
# Before (sync in-memory)
assistant = storage.assistants.get(assistant_id, user.id)

# After (async Postgres-compatible)
assistant = await storage.assistants.get(assistant_id, user.id)
```

Files to update:
- `robyn_server/routes/assistants.py`
- `robyn_server/routes/threads.py`
- `robyn_server/routes/runs.py`
- `robyn_server/routes/store.py`
- `robyn_server/routes/crons.py`
- `robyn_server/routes/streams.py`

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `robyn_server/postgres_storage.py` | **CREATE** | All five Postgres-backed store classes + `PostgresStorage` container |
| `robyn_server/storage.py` | MODIFY | Make in-memory methods `async`; update `get_storage()` to return Postgres or in-memory |
| `robyn_server/routes/assistants.py` | MODIFY | Add `await` to all storage method calls |
| `robyn_server/routes/threads.py` | MODIFY | Add `await` to all storage method calls |
| `robyn_server/routes/runs.py` | MODIFY | Add `await` to all storage method calls |
| `robyn_server/routes/store.py` | MODIFY | Add `await` to all storage method calls |
| `robyn_server/routes/crons.py` | MODIFY | Add `await` to all storage method calls |
| `robyn_server/routes/streams.py` | MODIFY | Add `await` to storage calls in streaming paths |
| `robyn_server/tests/*.py` | MODIFY | Update tests to use `await` for storage calls; add Postgres storage tests |

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Async mismatch — making in-memory stores async breaks existing sync call sites | High | High | Mechanical `await` addition; all callers are already `async def` |
| SQL injection via string interpolation | Critical | Low | Use parameterized queries (`%s` placeholders) exclusively; never f-strings for SQL |
| JSONB serialization edge cases (datetimes, UUIDs, bytes) | Medium | Medium | Use `psycopg.types.json.Json` adapter; test with real data |
| Owner isolation gaps in SQL queries | High | Low | Every query includes `WHERE metadata->>'owner' = %s`; code review all queries |
| Test suite needs major updates for async stores | Medium | High | Incremental — make in-memory async first, verify tests pass, then add Postgres tests |
| Large result sets without pagination | Medium | Medium | Existing `list()` methods already support `limit`/`offset`; carry forward to SQL |

## Acceptance Criteria

- [ ] `langgraph_server` schema created with all five tables + indexes
- [ ] `PostgresAssistantStore` — CRUD operations work with Postgres
- [ ] `PostgresThreadStore` — CRUD + state snapshots + history work with Postgres
- [ ] `PostgresRunStore` — CRUD + thread-scoped queries work with Postgres
- [ ] `PostgresStoreStorage` — put/get/delete/search/list_namespaces work with Postgres
- [ ] `PostgresCronStore` — CRUD operations work with Postgres
- [ ] `PostgresStorage` container wires all stores with shared pool
- [ ] `get_storage()` returns `PostgresStorage` when `DATABASE_URL` is set
- [ ] `get_storage()` returns in-memory `Storage` when `DATABASE_URL` is not set
- [ ] All route handlers updated with `await` for storage calls
- [ ] Owner isolation enforced in all SQL queries
- [ ] All existing tests updated and passing
- [ ] New Postgres-specific tests for each store
- [ ] DDL migrations are idempotent (safe to run on every startup)
- [ ] `ruff check` and `ruff format` pass
- [ ] No SQL injection vectors (all queries parameterized)

## Complexity Assessment

This is the **highest complexity task** in Goal 12. It touches nearly every route handler and requires reimplementing all five store classes. The async migration (making in-memory stores async + adding `await` everywhere) is the riskiest part — it's a pervasive change.

**Estimated scope**:
- ~5 new Postgres store classes (~200-300 lines each)
- ~1 new DDL migration file (~60 lines)
- ~6 route files needing `await` additions (~50-100 edits total)
- ~8 test files needing async updates
- Total: ~1500-2000 lines of changes across ~15 files

**Recommended approach**: Split into sub-steps:
1. First: Make in-memory stores async + update all call sites → verify tests pass
2. Then: Add Postgres store implementations → test with real DB
3. Finally: Wire `get_storage()` switching logic

## Notes

- The `BaseStore` generic class pattern in the in-memory implementation is clever but may not map cleanly to Postgres stores. Consider whether `PostgresBaseStore` should exist or if each Postgres store should be standalone. Standalone is simpler and avoids over-abstraction.
- The `ThreadStore` is the most complex — it has state snapshots and history, which are separate from the thread metadata itself. The `thread_states` table handles this with a foreign key to `threads`.
- The `StoreStorage` (key-value) uses tuple namespaces like `("user_123", "memories")` which need to be serialized to a single text key for the `namespace` column. Use `"/"` join: `"user_123/memories"`.
- Consider adding `EXPLAIN ANALYZE` for key queries during testing to ensure indexes are being used.
- The `psycopg` `Json` adapter handles Python dict → JSONB conversion. For reading, `psycopg` auto-converts JSONB → Python dict.