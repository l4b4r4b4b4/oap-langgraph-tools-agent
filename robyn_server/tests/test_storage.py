"""Unit tests for the in-memory storage layer.

Tests cover:
- CRUD operations for all resource types
- Owner isolation and filtering
- Edge cases and error handling
"""

import pytest

from robyn_server.models import Assistant, Run, Thread
from robyn_server.storage import (
    AssistantStore,
    RunStore,
    Storage,
    ThreadStore,
    generate_id,
    get_storage,
    reset_storage,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def assistant_store() -> AssistantStore:
    """Create a fresh AssistantStore for testing."""
    return AssistantStore()


@pytest.fixture
def thread_store() -> ThreadStore:
    """Create a fresh ThreadStore for testing."""
    return ThreadStore()


@pytest.fixture
def run_store() -> RunStore:
    """Create a fresh RunStore for testing."""
    return RunStore()


@pytest.fixture
def storage() -> Storage:
    """Create a fresh Storage container for testing."""
    return Storage()


@pytest.fixture(autouse=True)
def reset_global_storage():
    """Reset global storage before and after each test."""
    reset_storage()
    yield
    reset_storage()


# ============================================================================
# Helper Functions Tests
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_generate_id_returns_hex_string(self):
        """generate_id returns a 32-character hex string."""
        resource_id = generate_id()
        assert len(resource_id) == 32
        assert all(c in "0123456789abcdef" for c in resource_id)

    def test_generate_id_returns_unique_values(self):
        """generate_id returns unique values."""
        ids = [generate_id() for _ in range(100)]
        assert len(set(ids)) == 100


# ============================================================================
# AssistantStore Tests
# ============================================================================


class TestAssistantStore:
    """Tests for AssistantStore."""

    def test_create_assistant(self, assistant_store: AssistantStore):
        """Create assistant with owner stamping."""
        data = {"graph_id": "test-graph", "name": "Test Assistant"}
        owner_id = "user-123"

        assistant = assistant_store.create(data, owner_id)

        assert isinstance(assistant, Assistant)
        assert assistant.graph_id == "test-graph"
        assert assistant.name == "Test Assistant"
        assert assistant.metadata["owner"] == owner_id
        assert assistant.assistant_id is not None
        assert assistant.created_at is not None
        assert assistant.updated_at is not None

    def test_create_assistant_requires_graph_id(self, assistant_store: AssistantStore):
        """Create assistant without graph_id raises ValueError."""
        data = {"name": "Test Assistant"}
        owner_id = "user-123"

        with pytest.raises(ValueError, match="graph_id is required"):
            assistant_store.create(data, owner_id)

    def test_create_assistant_with_existing_metadata(
        self, assistant_store: AssistantStore
    ):
        """Create assistant preserves existing metadata and adds owner."""
        data = {
            "graph_id": "test-graph",
            "metadata": {"custom_key": "custom_value"},
        }
        owner_id = "user-123"

        assistant = assistant_store.create(data, owner_id)

        assert assistant.metadata["owner"] == owner_id
        assert assistant.metadata["custom_key"] == "custom_value"

    def test_get_assistant_by_owner(self, assistant_store: AssistantStore):
        """Get assistant by owner succeeds."""
        data = {"graph_id": "test-graph"}
        owner_id = "user-123"
        created = assistant_store.create(data, owner_id)

        retrieved = assistant_store.get(created.assistant_id, owner_id)

        assert retrieved is not None
        assert retrieved.assistant_id == created.assistant_id

    def test_get_assistant_by_different_owner_returns_none(
        self, assistant_store: AssistantStore
    ):
        """Get assistant by different owner returns None."""
        data = {"graph_id": "test-graph"}
        owner_id = "user-123"
        other_owner = "user-456"
        created = assistant_store.create(data, owner_id)

        retrieved = assistant_store.get(created.assistant_id, other_owner)

        assert retrieved is None

    def test_get_nonexistent_assistant_returns_none(
        self, assistant_store: AssistantStore
    ):
        """Get nonexistent assistant returns None."""
        result = assistant_store.get("nonexistent-id", "user-123")
        assert result is None

    def test_list_assistants_by_owner(self, assistant_store: AssistantStore):
        """List assistants filters by owner."""
        owner_a = "user-a"
        owner_b = "user-b"

        assistant_store.create({"graph_id": "graph-1"}, owner_a)
        assistant_store.create({"graph_id": "graph-2"}, owner_a)
        assistant_store.create({"graph_id": "graph-3"}, owner_b)

        list_a = assistant_store.list(owner_a)
        list_b = assistant_store.list(owner_b)

        assert len(list_a) == 2
        assert len(list_b) == 1
        assert all(a.metadata["owner"] == owner_a for a in list_a)
        assert all(a.metadata["owner"] == owner_b for a in list_b)

    def test_list_assistants_empty_for_new_owner(self, assistant_store: AssistantStore):
        """List assistants returns empty for owner with no assistants."""
        assistant_store.create({"graph_id": "graph-1"}, "user-a")

        result = assistant_store.list("user-new")

        assert result == []

    def test_update_assistant(self, assistant_store: AssistantStore):
        """Update assistant preserves owner."""
        owner_id = "user-123"
        created = assistant_store.create({"graph_id": "graph-1"}, owner_id)

        updated = assistant_store.update(
            created.assistant_id,
            {"name": "Updated Name"},
            owner_id,
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.metadata["owner"] == owner_id
        assert updated.updated_at > created.updated_at

    def test_update_assistant_by_different_owner_returns_none(
        self, assistant_store: AssistantStore
    ):
        """Update assistant by different owner returns None."""
        owner_id = "user-123"
        other_owner = "user-456"
        created = assistant_store.create({"graph_id": "graph-1"}, owner_id)

        result = assistant_store.update(
            created.assistant_id,
            {"name": "Hacked Name"},
            other_owner,
        )

        assert result is None
        # Verify original unchanged
        original = assistant_store.get(created.assistant_id, owner_id)
        assert original is not None
        assert original.name != "Hacked Name"

    def test_update_cannot_change_owner(self, assistant_store: AssistantStore):
        """Update cannot change the owner via metadata."""
        owner_id = "user-123"
        created = assistant_store.create({"graph_id": "graph-1"}, owner_id)

        updated = assistant_store.update(
            created.assistant_id,
            {"metadata": {"owner": "attacker"}},
            owner_id,
        )

        assert updated is not None
        assert updated.metadata["owner"] == owner_id  # Owner preserved

    def test_update_merges_metadata(self, assistant_store: AssistantStore):
        """Update merges metadata instead of replacing."""
        owner_id = "user-123"
        created = assistant_store.create(
            {"graph_id": "graph-1", "metadata": {"key1": "value1"}},
            owner_id,
        )

        updated = assistant_store.update(
            created.assistant_id,
            {"metadata": {"key2": "value2"}},
            owner_id,
        )

        assert updated is not None
        assert updated.metadata["key1"] == "value1"
        assert updated.metadata["key2"] == "value2"
        assert updated.metadata["owner"] == owner_id

    def test_delete_assistant(self, assistant_store: AssistantStore):
        """Delete assistant by owner succeeds."""
        owner_id = "user-123"
        created = assistant_store.create({"graph_id": "graph-1"}, owner_id)

        result = assistant_store.delete(created.assistant_id, owner_id)

        assert result is True
        assert assistant_store.get(created.assistant_id, owner_id) is None

    def test_delete_assistant_by_different_owner_fails(
        self, assistant_store: AssistantStore
    ):
        """Delete assistant by different owner fails."""
        owner_id = "user-123"
        other_owner = "user-456"
        created = assistant_store.create({"graph_id": "graph-1"}, owner_id)

        result = assistant_store.delete(created.assistant_id, other_owner)

        assert result is False
        # Verify still exists
        assert assistant_store.get(created.assistant_id, owner_id) is not None

    def test_delete_nonexistent_assistant_returns_false(
        self, assistant_store: AssistantStore
    ):
        """Delete nonexistent assistant returns False."""
        result = assistant_store.delete("nonexistent-id", "user-123")
        assert result is False

    def test_count_assistants(self, assistant_store: AssistantStore):
        """Count assistants by owner."""
        owner_a = "user-a"
        owner_b = "user-b"

        assistant_store.create({"graph_id": "graph-1"}, owner_a)
        assistant_store.create({"graph_id": "graph-2"}, owner_a)
        assistant_store.create({"graph_id": "graph-3"}, owner_b)

        assert assistant_store.count(owner_a) == 2
        assert assistant_store.count(owner_b) == 1
        assert assistant_store.count("owner-c") == 0


# ============================================================================
# ThreadStore Tests
# ============================================================================


class TestThreadStore:
    """Tests for ThreadStore."""

    def test_create_thread(self, thread_store: ThreadStore):
        """Create thread with owner stamping."""
        data = {"metadata": {"purpose": "testing"}}
        owner_id = "user-123"

        thread = thread_store.create(data, owner_id)

        assert isinstance(thread, Thread)
        assert thread.metadata["owner"] == owner_id
        assert thread.metadata["purpose"] == "testing"
        assert thread.thread_id is not None
        assert thread.created_at is not None

    def test_create_thread_minimal(self, thread_store: ThreadStore):
        """Create thread with minimal data."""
        owner_id = "user-123"

        thread = thread_store.create({}, owner_id)

        assert thread.metadata["owner"] == owner_id
        assert thread.thread_id is not None

    def test_get_thread_by_owner(self, thread_store: ThreadStore):
        """Get thread by owner succeeds."""
        owner_id = "user-123"
        created = thread_store.create({}, owner_id)

        retrieved = thread_store.get(created.thread_id, owner_id)

        assert retrieved is not None
        assert retrieved.thread_id == created.thread_id

    def test_get_thread_by_different_owner_returns_none(
        self, thread_store: ThreadStore
    ):
        """Get thread by different owner returns None."""
        owner_id = "user-123"
        other_owner = "user-456"
        created = thread_store.create({}, owner_id)

        retrieved = thread_store.get(created.thread_id, other_owner)

        assert retrieved is None

    def test_list_threads_by_owner(self, thread_store: ThreadStore):
        """List threads filters by owner."""
        owner_a = "user-a"
        owner_b = "user-b"

        thread_store.create({}, owner_a)
        thread_store.create({}, owner_a)
        thread_store.create({}, owner_b)

        list_a = thread_store.list(owner_a)
        list_b = thread_store.list(owner_b)

        assert len(list_a) == 2
        assert len(list_b) == 1

    def test_update_thread(self, thread_store: ThreadStore):
        """Update thread metadata."""
        owner_id = "user-123"
        created = thread_store.create({}, owner_id)

        updated = thread_store.update(
            created.thread_id,
            {"metadata": {"status": "active"}},
            owner_id,
        )

        assert updated is not None
        assert updated.metadata["status"] == "active"
        assert updated.metadata["owner"] == owner_id

    def test_delete_thread(self, thread_store: ThreadStore):
        """Delete thread by owner succeeds."""
        owner_id = "user-123"
        created = thread_store.create({}, owner_id)

        result = thread_store.delete(created.thread_id, owner_id)

        assert result is True
        assert thread_store.get(created.thread_id, owner_id) is None


# ============================================================================
# RunStore Tests
# ============================================================================


class TestRunStore:
    """Tests for RunStore."""

    def test_create_run(self, run_store: RunStore):
        """Create run with owner stamping."""
        data = {
            "thread_id": "thread-123",
            "assistant_id": "assistant-456",
        }
        owner_id = "user-123"

        run = run_store.create(data, owner_id)

        assert isinstance(run, Run)
        assert run.thread_id == "thread-123"
        assert run.assistant_id == "assistant-456"
        assert run.status == "pending"  # Default status
        assert run.metadata["owner"] == owner_id
        assert run.run_id is not None

    def test_create_run_requires_thread_id(self, run_store: RunStore):
        """Create run without thread_id raises ValueError."""
        data = {"assistant_id": "assistant-456"}
        owner_id = "user-123"

        with pytest.raises(ValueError, match="thread_id is required"):
            run_store.create(data, owner_id)

    def test_create_run_requires_assistant_id(self, run_store: RunStore):
        """Create run without assistant_id raises ValueError."""
        data = {"thread_id": "thread-123"}
        owner_id = "user-123"

        with pytest.raises(ValueError, match="assistant_id is required"):
            run_store.create(data, owner_id)

    def test_create_run_with_custom_status(self, run_store: RunStore):
        """Create run with custom status."""
        data = {
            "thread_id": "thread-123",
            "assistant_id": "assistant-456",
            "status": "running",
        }
        owner_id = "user-123"

        run = run_store.create(data, owner_id)

        assert run.status == "running"

    def test_get_run_by_owner(self, run_store: RunStore):
        """Get run by owner succeeds."""
        owner_id = "user-123"
        created = run_store.create(
            {"thread_id": "t1", "assistant_id": "a1"},
            owner_id,
        )

        retrieved = run_store.get(created.run_id, owner_id)

        assert retrieved is not None
        assert retrieved.run_id == created.run_id

    def test_get_run_by_different_owner_returns_none(self, run_store: RunStore):
        """Get run by different owner returns None."""
        owner_id = "user-123"
        other_owner = "user-456"
        created = run_store.create(
            {"thread_id": "t1", "assistant_id": "a1"},
            owner_id,
        )

        retrieved = run_store.get(created.run_id, other_owner)

        assert retrieved is None

    def test_list_runs_by_owner(self, run_store: RunStore):
        """List runs filters by owner."""
        owner_a = "user-a"
        owner_b = "user-b"

        run_store.create({"thread_id": "t1", "assistant_id": "a1"}, owner_a)
        run_store.create({"thread_id": "t2", "assistant_id": "a1"}, owner_a)
        run_store.create({"thread_id": "t3", "assistant_id": "a1"}, owner_b)

        list_a = run_store.list(owner_a)
        list_b = run_store.list(owner_b)

        assert len(list_a) == 2
        assert len(list_b) == 1

    def test_list_by_thread(self, run_store: RunStore):
        """List runs by thread_id."""
        owner_id = "user-123"
        thread_1 = "thread-1"
        thread_2 = "thread-2"

        run_store.create({"thread_id": thread_1, "assistant_id": "a1"}, owner_id)
        run_store.create({"thread_id": thread_1, "assistant_id": "a1"}, owner_id)
        run_store.create({"thread_id": thread_2, "assistant_id": "a1"}, owner_id)

        runs_t1 = run_store.list_by_thread(thread_1, owner_id)
        runs_t2 = run_store.list_by_thread(thread_2, owner_id)

        assert len(runs_t1) == 2
        assert len(runs_t2) == 1

    def test_list_by_thread_respects_owner(self, run_store: RunStore):
        """List by thread respects owner isolation."""
        owner_a = "user-a"
        owner_b = "user-b"
        thread_id = "shared-thread"

        run_store.create({"thread_id": thread_id, "assistant_id": "a1"}, owner_a)
        run_store.create({"thread_id": thread_id, "assistant_id": "a1"}, owner_b)

        runs_a = run_store.list_by_thread(thread_id, owner_a)
        runs_b = run_store.list_by_thread(thread_id, owner_b)

        assert len(runs_a) == 1
        assert len(runs_b) == 1
        assert runs_a[0].metadata["owner"] == owner_a
        assert runs_b[0].metadata["owner"] == owner_b

    def test_update_status(self, run_store: RunStore):
        """Update run status."""
        owner_id = "user-123"
        created = run_store.create(
            {"thread_id": "t1", "assistant_id": "a1"},
            owner_id,
        )
        assert created.status == "pending"

        updated = run_store.update_status(created.run_id, "running", owner_id)

        assert updated is not None
        assert updated.status == "running"

    def test_update_status_by_different_owner_fails(self, run_store: RunStore):
        """Update status by different owner returns None."""
        owner_id = "user-123"
        other_owner = "user-456"
        created = run_store.create(
            {"thread_id": "t1", "assistant_id": "a1"},
            owner_id,
        )

        result = run_store.update_status(created.run_id, "cancelled", other_owner)

        assert result is None
        # Verify original unchanged
        original = run_store.get(created.run_id, owner_id)
        assert original is not None
        assert original.status == "pending"

    def test_delete_run(self, run_store: RunStore):
        """Delete run by owner succeeds."""
        owner_id = "user-123"
        created = run_store.create(
            {"thread_id": "t1", "assistant_id": "a1"},
            owner_id,
        )

        result = run_store.delete(created.run_id, owner_id)

        assert result is True
        assert run_store.get(created.run_id, owner_id) is None


# ============================================================================
# Storage Container Tests
# ============================================================================


class TestStorage:
    """Tests for Storage container."""

    def test_storage_has_all_stores(self, storage: Storage):
        """Storage has assistants, threads, and runs stores."""
        assert isinstance(storage.assistants, AssistantStore)
        assert isinstance(storage.threads, ThreadStore)
        assert isinstance(storage.runs, RunStore)

    def test_clear_all(self, storage: Storage):
        """clear_all removes all data from all stores."""
        owner_id = "user-123"

        storage.assistants.create({"graph_id": "g1"}, owner_id)
        storage.threads.create({}, owner_id)
        storage.runs.create({"thread_id": "t1", "assistant_id": "a1"}, owner_id)

        storage.clear_all()

        assert storage.assistants.count(owner_id) == 0
        assert storage.threads.count(owner_id) == 0
        assert storage.runs.count(owner_id) == 0


# ============================================================================
# Global Storage Tests
# ============================================================================


class TestGlobalStorage:
    """Tests for module-level storage access."""

    def test_get_storage_returns_same_instance(self):
        """get_storage returns the same instance."""
        storage_1 = get_storage()
        storage_2 = get_storage()

        assert storage_1 is storage_2

    def test_reset_storage_creates_new_instance(self):
        """reset_storage creates a new instance."""
        storage_1 = get_storage()
        reset_storage()
        storage_2 = get_storage()

        assert storage_1 is not storage_2

    def test_global_storage_is_functional(self):
        """Global storage works end-to-end."""
        storage = get_storage()
        owner_id = "user-123"

        assistant = storage.assistants.create({"graph_id": "g1"}, owner_id)
        thread = storage.threads.create({}, owner_id)
        run = storage.runs.create(
            {"thread_id": thread.thread_id, "assistant_id": assistant.assistant_id},
            owner_id,
        )

        assert storage.assistants.get(assistant.assistant_id, owner_id) is not None
        assert storage.threads.get(thread.thread_id, owner_id) is not None
        assert storage.runs.get(run.run_id, owner_id) is not None


# ============================================================================
# Cross-Owner Isolation Tests
# ============================================================================


class TestCrossOwnerIsolation:
    """Tests ensuring complete owner isolation."""

    def test_user_a_cannot_see_user_b_assistants(self, storage: Storage):
        """User A cannot see User B's assistants."""
        user_a = "user-a"
        user_b = "user-b"

        assistant_b = storage.assistants.create({"graph_id": "secret"}, user_b)

        # User A tries to access User B's assistant
        assert storage.assistants.get(assistant_b.assistant_id, user_a) is None
        assert assistant_b.assistant_id not in [
            a.assistant_id for a in storage.assistants.list(user_a)
        ]

    def test_user_a_cannot_see_user_b_threads(self, storage: Storage):
        """User A cannot see User B's threads."""
        user_a = "user-a"
        user_b = "user-b"

        thread_b = storage.threads.create({}, user_b)

        # User A tries to access User B's thread
        assert storage.threads.get(thread_b.thread_id, user_a) is None
        assert thread_b.thread_id not in [
            t.thread_id for t in storage.threads.list(user_a)
        ]

    def test_user_a_cannot_see_user_b_runs(self, storage: Storage):
        """User A cannot see User B's runs."""
        user_a = "user-a"
        user_b = "user-b"

        run_b = storage.runs.create(
            {"thread_id": "t1", "assistant_id": "a1"},
            user_b,
        )

        # User A tries to access User B's run
        assert storage.runs.get(run_b.run_id, user_a) is None
        assert run_b.run_id not in [r.run_id for r in storage.runs.list(user_a)]

    def test_user_a_cannot_update_user_b_resources(self, storage: Storage):
        """User A cannot update User B's resources."""
        user_a = "user-a"
        user_b = "user-b"

        assistant_b = storage.assistants.create({"graph_id": "g1"}, user_b)
        thread_b = storage.threads.create({}, user_b)
        run_b = storage.runs.create(
            {"thread_id": "t1", "assistant_id": "a1"},
            user_b,
        )

        # User A tries to update User B's resources
        assert (
            storage.assistants.update(
                assistant_b.assistant_id, {"name": "hacked"}, user_a
            )
            is None
        )
        assert (
            storage.threads.update(
                thread_b.thread_id, {"metadata": {"hacked": True}}, user_a
            )
            is None
        )
        assert storage.runs.update_status(run_b.run_id, "cancelled", user_a) is None

    def test_user_a_cannot_delete_user_b_resources(self, storage: Storage):
        """User A cannot delete User B's resources."""
        user_a = "user-a"
        user_b = "user-b"

        assistant_b = storage.assistants.create({"graph_id": "g1"}, user_b)
        thread_b = storage.threads.create({}, user_b)
        run_b = storage.runs.create(
            {"thread_id": "t1", "assistant_id": "a1"},
            user_b,
        )

        # User A tries to delete User B's resources
        assert storage.assistants.delete(assistant_b.assistant_id, user_a) is False
        assert storage.threads.delete(thread_b.thread_id, user_a) is False
        assert storage.runs.delete(run_b.run_id, user_a) is False

        # Verify resources still exist for User B
        assert storage.assistants.get(assistant_b.assistant_id, user_b) is not None
        assert storage.threads.get(thread_b.thread_id, user_b) is not None
        assert storage.runs.get(run_b.run_id, user_b) is not None
