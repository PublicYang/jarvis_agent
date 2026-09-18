"""Unit and integration tests for SQLiteMemoryStore (Phase10)."""

import concurrent.futures
from datetime import UTC, datetime, timedelta
from pathlib import Path

from memory.models import MemoryRecord, MemoryScope
from memory.sqlite import SQLiteMemoryStore
from memory.store import MemoryStore
from runtime.models import Message, MessageRole, State


def test_sqlite_store_implements_protocol() -> None:
    store = SQLiteMemoryStore()
    assert isinstance(store, MemoryStore)
    store.close()


def test_sqlite_write_and_read() -> None:
    with SQLiteMemoryStore() as store:
        rec = MemoryRecord(key="user_city", content="Shanghai", scope=MemoryScope.USER)
        store.write(rec)

        found = store.read("user_city", MemoryScope.USER)
        assert found is not None
        assert found.id == rec.id
        assert found.content == "Shanghai"

        assert store.read("unknown", MemoryScope.USER) is None
        assert store.read("user_city", MemoryScope.SESSION) is None
        assert store.read("user_city", MemoryScope.GLOBAL) is None


def test_sqlite_get_by_id() -> None:
    with SQLiteMemoryStore() as store:
        rec = MemoryRecord(key="note", content="persistent note")
        store.write(rec)

        assert store.get(rec.id) == rec
        assert store.get("non-existent-id") is None


def test_sqlite_scope_isolation() -> None:
    with SQLiteMemoryStore() as store:
        store.write(
            MemoryRecord(key="theme", content="dark_session", scope=MemoryScope.SESSION)
        )
        store.write(
            MemoryRecord(key="theme", content="light_user", scope=MemoryScope.USER)
        )
        store.write(
            MemoryRecord(key="theme", content="system_global", scope=MemoryScope.GLOBAL)
        )

        assert store.count() == 3
        assert (
            store.read("theme", MemoryScope.SESSION).content  # type: ignore[union-attr]
            == "dark_session"
        )
        assert (
            store.read("theme", MemoryScope.USER).content  # type: ignore[union-attr]
            == "light_user"
        )
        assert (
            store.read("theme", MemoryScope.GLOBAL).content  # type: ignore[union-attr]
            == "system_global"
        )


def test_sqlite_overwrite_same_key_scope() -> None:
    with SQLiteMemoryStore() as store:
        rec1 = MemoryRecord(key="lang", content="python", scope=MemoryScope.USER)
        rec2 = MemoryRecord(key="lang", content="rust", scope=MemoryScope.USER)

        store.write(rec1)
        store.write(rec2)

        assert store.count() == 1
        assert (
            store.read("lang", MemoryScope.USER).content  # type: ignore[union-attr]
            == "rust"
        )
        assert store.get(rec1.id) is None
        assert store.get(rec2.id) is not None


def test_sqlite_delete() -> None:
    with SQLiteMemoryStore() as store:
        rec = MemoryRecord(key="temp", content="to be deleted")
        store.write(rec)

        assert store.read("temp", MemoryScope.SESSION) is not None
        store.delete(rec.id)

        assert store.read("temp", MemoryScope.SESSION) is None
        assert store.get(rec.id) is None
        assert store.count() == 0


def test_sqlite_expiration_filtering() -> None:
    with SQLiteMemoryStore() as store:
        past = datetime.now(UTC) - timedelta(minutes=5)
        future = datetime.now(UTC) + timedelta(hours=1)

        rec_exp = MemoryRecord(key="exp", content="expired text", expires_at=past)
        rec_valid = MemoryRecord(key="valid", content="valid text", expires_at=future)

        store.write(rec_exp)
        store.write(rec_valid)

        assert store.read("exp", MemoryScope.SESSION) is None
        assert store.get(rec_exp.id) is None
        assert store.read("valid", MemoryScope.SESSION) is not None

        # Search excludes expired
        results = store.search("text")
        assert len(results) == 1
        assert results[0].key == "valid"

        removed = store.cleanup_expired()
        assert removed == 1
        assert store.count() == 1


def test_sqlite_search_and_ranking() -> None:
    with SQLiteMemoryStore() as store:
        store.write(
            MemoryRecord(
                key="python_lang",
                content="Programming in Python",
                scope=MemoryScope.USER,
            )
        )
        store.write(
            MemoryRecord(
                key="db_sqlite",
                content="Database management",
                scope=MemoryScope.USER,
            )
        )
        store.write(
            MemoryRecord(
                key="global_python",
                content="Python runtime environment",
                scope=MemoryScope.GLOBAL,
            )
        )

        # Keyword match
        results = store.search("python")
        assert len(results) == 2
        keys = {r.key for r in results}
        assert keys == {"python_lang", "global_python"}

        # Scope filtered search
        user_results = store.search("python", scope=MemoryScope.USER)
        assert len(user_results) == 1
        assert user_results[0].key == "python_lang"

        # Limit
        all_results = store.search("", limit=2)
        assert len(all_results) == 2


def test_sqlite_restart_persistence(tmp_path: Path) -> None:
    """Core Gate: verify persistence and recovery across process restarts."""
    db_file = tmp_path / "persisted_agent.db"

    rec1 = MemoryRecord(key="user_name", content="Charlie", scope=MemoryScope.USER)
    rec2 = MemoryRecord(
        key="session_goal", content="Learn Agent Dev", scope=MemoryScope.SESSION
    )

    # 1. First run writes records and closes
    store1 = SQLiteMemoryStore(db_file)
    store1.write(rec1)
    store1.write(rec2)
    store1.close()

    # 2. Simulate process restart by opening a new instance on same file
    store2 = SQLiteMemoryStore(db_file)
    assert store2.count() == 2

    restored_user = store2.read("user_name", MemoryScope.USER)
    assert restored_user is not None
    assert restored_user.id == rec1.id
    assert restored_user.content == "Charlie"

    restored_goal = store2.read("session_goal", MemoryScope.SESSION)
    assert restored_goal is not None
    assert restored_goal.id == rec2.id
    assert restored_goal.content == "Learn Agent Dev"

    store2.close()


def test_sqlite_session_state_recovery(tmp_path: Path) -> None:
    """Verify session State can be saved and restored across restarts."""
    db_file = tmp_path / "session_state.db"

    messages = [
        Message(role=MessageRole.USER, content="Hello"),
        Message(role=MessageRole.ASSISTANT, content="Hi, how can I help?"),
    ]
    state = State(
        messages=messages,
        memory_refs=["mem_id_1", "mem_id_2"],
    )

    # 1. Save state in store1 and close
    store1 = SQLiteMemoryStore(db_file)
    store1.save_state(state)
    store1.close()

    # 2. Restore state in store2
    store2 = SQLiteMemoryStore(db_file)
    restored = store2.load_state(state.id)
    assert restored is not None
    assert restored.id == state.id
    assert len(restored.messages) == 2
    assert [m.content for m in restored.messages] == [
        "Hello",
        "Hi, how can I help?",
    ]
    assert restored.memory_refs == ["mem_id_1", "mem_id_2"]

    # Non-existent state returns None
    assert store2.load_state("unknown_state_id") is None
    store2.close()


def test_sqlite_concurrency() -> None:
    """Verify concurrent reads and writes over SQLite connection with locking."""
    with SQLiteMemoryStore() as store:

        def worker(idx: int) -> None:
            rec = MemoryRecord(
                key=f"worker_key_{idx}",
                content=f"worker_content_{idx}",
                scope=MemoryScope.SESSION,
            )
            store.write(rec)
            read_rec = store.read(f"worker_key_{idx}", MemoryScope.SESSION)
            assert read_rec is not None
            store.search("worker")

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, i) for i in range(40)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        assert store.count() == 40
