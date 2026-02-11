# Task 01: Dependencies & DB Module

> **Status**: ⚪ Not Started
> **Parent Goal**: [12-Postgres-Persistence](../scratchpad.md)
> **Depends On**: Goal 11 (packages already added in Goal 11 Task-01)
> **Created**: 2026-02-11
> **Updated**: 2026-02-11

## Objective

Create the database connection infrastructure for Postgres persistence. This includes the `DATABASE_URL` environment variable configuration, a shared async connection pool module, and startup/shutdown lifecycle management. This module is the foundation that both the LangGraph checkpointer/store (Task-02) and the Robyn runtime storage (Task-03) will build on.

## Implementation Plan

### Step 1: Add `DatabaseConfig` to `robyn_server/config.py`

```python
@dataclass
class DatabaseConfig:
    """Database configuration for Postgres persistence."""

    url: str = ""
    pool_min_size: int = 2
    pool_max_size: int = 10
    pool_timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            url=os.getenv("DATABASE_URL", ""),
            pool_min_size=int(os.getenv("DATABASE_POOL_MIN_SIZE", "2")),
            pool_max_size=int(os.getenv("DATABASE_POOL_MAX_SIZE", "10")),
            pool_timeout=float(os.getenv("DATABASE_POOL_TIMEOUT", "30.0")),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.url)
```

Also add `database: DatabaseConfig` to the `Config` dataclass and wire it into `Config.from_env()`.

### Step 2: Create `robyn_server/database.py`

New module responsible for:

1. **Connection pool lifecycle** — create, manage, and close an `AsyncConnectionPool` from `psycopg_pool`
2. **LangGraph checkpointer/store initialization** — create `AsyncPostgresSaver` and `AsyncPostgresStore` instances
3. **Setup logic** — call `.setup()` on first run to auto-create LangGraph tables
4. **Singleton access** — global accessor functions (`get_checkpointer()`, `get_store()`, `get_pool()`)
5. **Graceful shutdown** — close pool on server shutdown

```python
# robyn_server/database.py — rough structure

import logging
from typing import Optional

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

from robyn_server.config import get_config

logger = logging.getLogger(__name__)

_pool: Optional[AsyncConnectionPool] = None
_checkpointer: Optional[AsyncPostgresSaver] = None
_store: Optional[AsyncPostgresStore] = None
_initialized: bool = False


async def initialize_database() -> bool:
    """Initialize database connections. Returns True if Postgres is configured and ready."""
    global _pool, _checkpointer, _store, _initialized

    config = get_config()
    if not config.database.is_configured:
        logger.info("DATABASE_URL not set — using in-memory storage")
        return False

    db_url = config.database.url
    # Append sslmode=disable for local Supabase if not already present
    if "sslmode" not in db_url and "127.0.0.1" in db_url:
        db_url += "?sslmode=disable"

    # Create connection pool
    _pool = AsyncConnectionPool(
        conninfo=db_url,
        min_size=config.database.pool_min_size,
        max_size=config.database.pool_max_size,
        timeout=config.database.pool_timeout,
    )
    await _pool.open()

    # Create LangGraph checkpointer and store
    _checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
    _store = AsyncPostgresStore.from_conn_string(db_url)

    # Run setup (idempotent — creates tables if they don't exist)
    await _checkpointer.setup()
    await _store.setup()

    _initialized = True
    logger.info("Postgres persistence initialized successfully")
    return True


async def shutdown_database() -> None:
    """Close database connections gracefully."""
    global _pool, _checkpointer, _store, _initialized
    # Close resources...
    _initialized = False


def get_pool() -> Optional[AsyncConnectionPool]:
    return _pool

def get_checkpointer() -> Optional[AsyncPostgresSaver]:
    return _checkpointer

def get_store() -> Optional[AsyncPostgresStore]:
    return _store

def is_postgres_enabled() -> bool:
    return _initialized
```

### Step 3: Wire into Robyn server lifecycle

In `robyn_server/app.py` or `__main__.py`, call `initialize_database()` at startup and `shutdown_database()` at shutdown.

### Step 4: Environment variable documentation

Add `DATABASE_URL` to `.env.example` (or document in README):

```env
# Postgres persistence (optional — falls back to in-memory if not set)
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
DATABASE_POOL_MIN_SIZE=2
DATABASE_POOL_MAX_SIZE=10
DATABASE_POOL_TIMEOUT=30.0
```

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `robyn_server/database.py` | **CREATE** | Connection pool, checkpointer/store init, lifecycle management |
| `robyn_server/config.py` | MODIFY | Add `DatabaseConfig` dataclass |
| `robyn_server/app.py` or `__main__.py` | MODIFY | Wire startup/shutdown lifecycle |

## Dependencies (Python packages)

All should already be installed by Goal 11 Task-01:

- `langgraph-checkpoint-postgres>=3.0.4` — provides `AsyncPostgresSaver`, `AsyncPostgresStore`
- `psycopg[binary,pool]>=3.2.0` — provides `AsyncConnectionPool`, async Postgres driver
- `psycopg-pool>=3.2.0` — connection pooling (transitive from above)

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `AsyncConnectionPool` and `AsyncPostgresSaver` conflict on connection management | Medium | Medium | They may use separate internal pools; verify if `from_conn_string` creates its own pool |
| Supabase local Postgres requires `sslmode=disable` | Low | High | Auto-append for localhost connections |
| Pool initialization fails if Postgres is not running | Medium | Medium | Catch connection errors, log warning, fall back to in-memory |

## Acceptance Criteria

- [ ] `robyn_server/database.py` module created with pool management
- [ ] `DatabaseConfig` added to `robyn_server/config.py`
- [ ] `initialize_database()` successfully connects to local Supabase Postgres
- [ ] `get_checkpointer()` returns a valid `AsyncPostgresSaver` when configured
- [ ] `get_store()` returns a valid `AsyncPostgresStore` when configured
- [ ] `is_postgres_enabled()` returns `True` when configured, `False` otherwise
- [ ] Startup/shutdown lifecycle wired into Robyn server
- [ ] Falls back gracefully to in-memory when `DATABASE_URL` is not set
- [ ] `ruff check` and `ruff format` pass
- [ ] Existing tests still pass (no regressions)

## Notes

- The `AsyncPostgresSaver.from_conn_string()` and `AsyncPostgresStore.from_conn_string()` each create their own internal connection pool. Investigate whether we can pass our shared pool instead to reduce connection count. The `from_conn_string` is the simplest path; optimization can come later.
- The `.setup()` calls are idempotent — they use `CREATE TABLE IF NOT EXISTS` internally. Safe to call on every startup.
- For production (AKS deployment), `DATABASE_URL` will point to the production Supabase Postgres instance with proper credentials. The connection string format is the same.