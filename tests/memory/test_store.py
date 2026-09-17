"""Unit tests for MemoryStore interface and InMemoryMemoryStore (Phase8)."""

import concurrent.futures
from datetime import UTC, datetime, timedelta

from memory.models import MemoryRecord, MemoryScope
from memory.store import InMemoryMemoryStore, MemoryStore
from runtime.models import State


def test_in_memory_store_implements_protocol() -> None:
    store = InMemoryMemoryStore()
    assert isinstance(store, MemoryStore)


def test_write_and_read() -> None:
    store = InMemoryMemoryStore()
    rec = MemoryRecord(key="user_city", content="Hangzhou", scope=MemoryScope.USER)
    store.write(rec)

    # Exact key and scope match
    found = store.read("user_city", MemoryScope.USER)
    assert found is not None
    assert found.id == rec.id
    assert found.content == "Hangzhou"

    # Reading with wrong key or wrong scope returns None
    assert store.read("non_existent", MemoryScope.USER) is None
    assert store.read("user_city", MemoryScope.SESSION) is None
    assert store.read("user_city", MemoryScope.GLOBAL) is None


def test_get_by_id() -> None:
    store = InMemoryMemoryStore()
    rec = MemoryRecord(key="summary", content="Conversation summary")
    store.write(rec)

    assert store.get(rec.id) == rec
    assert store.get("non-existent-id") is None


def test_scope_isolation_prevents_contamination() -> None:
    """Verify identical keys across different scopes do not collide or contaminate."""
    store = InMemoryMemoryStore()

    rec_session = MemoryRecord(
        key="topic", content="Python Agent", scope=MemoryScope.SESSION
    )
    rec_user = MemoryRecord(
        key="topic", content="Machine Learning", scope=MemoryScope.USER
    )
    rec_global = MemoryRecord(
        key="topic", content="General AI", scope=MemoryScope.GLOBAL
    )

    store.write(rec_session)
    store.write(rec_user)
    store.write(rec_global)

    assert store.count() == 3

    assert store.read("topic", MemoryScope.SESSION).content == "Python Agent"  # type: ignore[union-attr]
    assert store.read("topic", MemoryScope.USER).content == "Machine Learning"  # type: ignore[union-attr]
    assert store.read("topic", MemoryScope.GLOBAL).content == "General AI"  # type: ignore[union-attr]


def test_overwrite_on_same_key_and_scope() -> None:
    """Writing to the same (key, scope) updates the record to avoid stale memory."""
    store = InMemoryMemoryStore()

    rec1 = MemoryRecord(key="pref_theme", content="dark", scope=MemoryScope.USER)
    rec2 = MemoryRecord(key="pref_theme", content="light", scope=MemoryScope.USER)

    store.write(rec1)
    assert store.read("pref_theme", MemoryScope.USER).content == "dark"  # type: ignore[union-attr]

    store.write(rec2)
    assert store.count() == 1
    assert store.read("pref_theme", MemoryScope.USER).content == "light"  # type: ignore[union-attr]
    # Old ID should no longer be accessible
    assert store.get(rec1.id) is None
    assert store.get(rec2.id) is not None


def test_delete_record() -> None:
    store = InMemoryMemoryStore()
    rec = MemoryRecord(key="temp", content="temporary value")
    store.write(rec)

    assert store.read("temp", MemoryScope.SESSION) is not None
    store.delete(rec.id)

    assert store.read("temp", MemoryScope.SESSION) is None
    assert store.get(rec.id) is None
    assert store.count() == 0


def test_expiration_behavior() -> None:
    store = InMemoryMemoryStore()
    past = datetime.now(UTC) - timedelta(seconds=10)
    future = datetime.now(UTC) + timedelta(hours=1)

    rec_expired = MemoryRecord(key="exp", content="expired content", expires_at=past)
    rec_valid = MemoryRecord(key="val", content="valid content", expires_at=future)

    store.write(rec_expired)
    store.write(rec_valid)

    # Expired records should not be returned by read or get
    assert store.read("exp", MemoryScope.SESSION) is None
    assert store.get(rec_expired.id) is None

    # Valid records work normally
    assert store.read("val", MemoryScope.SESSION) is not None
    assert store.get(rec_valid.id) is not None

    # Search ignores expired records
    results = store.search("content")
    assert len(results) == 1
    assert results[0].key == "val"

    # Cleanup expired records
    removed = store.cleanup_expired()
    assert removed == 1
    assert store.count() == 1


def test_search_and_filtering() -> None:
    store = InMemoryMemoryStore()
    store.write(
        MemoryRecord(key="lang", content="Python programming", scope=MemoryScope.USER)
    )
    store.write(
        MemoryRecord(key="db", content="PostgreSQL database", scope=MemoryScope.USER)
    )
    store.write(
        MemoryRecord(
            key="python_framework", content="FastAPI web", scope=MemoryScope.GLOBAL
        )
    )

    # Content match case-insensitive
    results = store.search("python")
    assert len(results) == 2
    keys = {r.key for r in results}
    assert keys == {"lang", "python_framework"}

    # Search with scope filter
    user_results = store.search("python", scope=MemoryScope.USER)
    assert len(user_results) == 1
    assert user_results[0].key == "lang"

    # Limit check
    all_results = store.search("", limit=2)
    assert len(all_results) == 2


def test_state_memory_refs_integration() -> None:
    """Verify State.memory_refs links to MemoryStore records without duplication."""
    store = InMemoryMemoryStore()
    state = State()

    # Create memory records and associate IDs in state.memory_refs
    rec1 = MemoryRecord(key="goal", content="Build autonomous agent")
    rec2 = MemoryRecord(key="user_lang", content="Chinese", scope=MemoryScope.USER)
    store.write(rec1)
    store.write(rec2)

    state.memory_refs.append(rec1.id)
    state.memory_refs.append(rec2.id)

    # Dereference records from state.memory_refs
    retrieved = [store.get(ref_id) for ref_id in state.memory_refs]
    assert all(r is not None for r in retrieved)
    assert [r.content for r in retrieved if r] == [  # type: ignore[union-attr]
        "Build autonomous agent",
        "Chinese",
    ]


def test_concurrency_thread_safety() -> None:
    """Verify concurrent reads and writes do not cause race conditions."""
    store = InMemoryMemoryStore()

    def worker(idx: int) -> None:
        rec = MemoryRecord(
            key=f"key_{idx}",
            content=f"content_{idx}",
            scope=MemoryScope.SESSION,
        )
        store.write(rec)
        assert store.read(f"key_{idx}", MemoryScope.SESSION) is not None
        store.search("content")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(50)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    assert store.count() == 50
