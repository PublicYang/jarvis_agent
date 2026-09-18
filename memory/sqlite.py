"""SQLite persistent memory store implementation (Phase10)."""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from runtime.models import State

from memory.models import MemoryRecord, MemoryScope


class SQLiteMemoryStore:
    """Thread-safe SQLite persistent store for MemoryRecords and State snapshots."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = db_path
        if isinstance(db_path, Path):
            db_path = str(db_path)
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_records (
                    id TEXT PRIMARY KEY,
                    key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    embedding_ref TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_key_scope
                ON memory_records(key, scope)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS states (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        created_at = datetime.fromisoformat(row["created_at"])
        expires_at = (
            datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
        )
        return MemoryRecord(
            id=row["id"],
            key=row["key"],
            content=row["content"],
            scope=MemoryScope(row["scope"]),
            embedding_ref=row["embedding_ref"],
            created_at=created_at,
            expires_at=expires_at,
        )

    def write(self, record: MemoryRecord) -> None:
        """Write or update a memory record."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "DELETE FROM memory_records WHERE id = ? OR (key = ? AND scope = ?)",
                (record.id, record.key, record.scope.value),
            )
            cursor.execute(
                """
                INSERT INTO memory_records (
                    id, key, content, scope, embedding_ref, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.key,
                    record.content,
                    record.scope.value,
                    record.embedding_ref,
                    record.created_at.isoformat(),
                    record.expires_at.isoformat() if record.expires_at else None,
                ),
            )
            self._conn.commit()

    def read(self, key: str, scope: MemoryScope) -> MemoryRecord | None:
        """Read a record by key and scope, returning None if expired or not found."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT id, key, content, scope, embedding_ref, created_at, expires_at
                FROM memory_records
                WHERE key = ? AND scope = ?
                """,
                (key, scope.value),
            )
            row = cursor.fetchone()
            if not row:
                return None
            rec = self._row_to_record(row)
            if rec.is_expired():
                return None
            return rec

    def get(self, record_id: str) -> MemoryRecord | None:
        """Get a record by ID, returning None if expired or not found."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT id, key, content, scope, embedding_ref, created_at, expires_at
                FROM memory_records
                WHERE id = ?
                """,
                (record_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            rec = self._row_to_record(row)
            if rec.is_expired():
                return None
            return rec

    def search(
        self,
        query: str,
        limit: int = 10,
        scope: MemoryScope | None = None,
    ) -> list[MemoryRecord]:
        """Search non-expired records matching query in key or content."""
        with self._lock:
            sql = (
                "SELECT id, key, content, scope, embedding_ref, "
                "created_at, expires_at FROM memory_records"
            )
            params: list[Any] = []
            if scope is not None:
                sql += " WHERE scope = ?"
                params.append(scope.value)

            cursor = self._conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            q = query.lower().strip()
            matches: list[MemoryRecord] = []
            for row in rows:
                rec = self._row_to_record(row)
                if rec.is_expired():
                    continue
                k_lower = rec.key.lower()
                c_lower = rec.content.lower()
                if not q:
                    matches.append(rec)
                elif (
                    q in k_lower
                    or q in c_lower
                    or (len(k_lower) > 1 and k_lower in q)
                    or (len(c_lower) > 1 and c_lower in q)
                ):
                    matches.append(rec)

            def sort_key(rec: MemoryRecord) -> tuple[int, float]:
                k = rec.key.lower()
                c = rec.content.lower()
                if q and k == q:
                    rank = 0
                elif q and q in k:
                    rank = 1
                elif q and len(k) > 1 and k in q:
                    rank = 2
                elif q and q in c:
                    rank = 3
                elif q and len(c) > 1 and c in q:
                    rank = 4
                else:
                    rank = 5
                return (rank, -rec.created_at.timestamp())

            matches.sort(key=sort_key)
            return matches[:limit]

    def delete(self, record_id: str) -> None:
        """Delete a record by ID."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "DELETE FROM memory_records WHERE id = ?",
                (record_id,),
            )
            self._conn.commit()

    def cleanup_expired(self) -> int:
        """Delete expired records and return the number of removed records."""
        with self._lock:
            now_iso = datetime.now(UTC).isoformat()
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT count(*) FROM memory_records WHERE "
                "expires_at IS NOT NULL AND expires_at <= ?",
                (now_iso,),
            )
            count = cursor.fetchone()[0]
            if count > 0:
                cursor.execute(
                    "DELETE FROM memory_records WHERE "
                    "expires_at IS NOT NULL AND expires_at <= ?",
                    (now_iso,),
                )
                self._conn.commit()
            return count

    def count(self) -> int:
        """Return the count of active (non-expired) records."""
        with self._lock:
            now_iso = datetime.now(UTC).isoformat()
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT count(*) FROM memory_records WHERE "
                "expires_at IS NULL OR expires_at > ?",
                (now_iso,),
            )
            return cursor.fetchone()[0]

    def save_state(self, state: State) -> None:
        """Persist a State snapshot for session recovery."""
        with self._lock:
            now_iso = datetime.now(UTC).isoformat()
            cursor = self._conn.cursor()
            cursor.execute(
                """
                INSERT INTO states (id, data, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (state.id, state.model_dump_json(), now_iso),
            )
            self._conn.commit()

    def load_state(self, state_id: str) -> State | None:
        """Load and restore a State snapshot by ID."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT data FROM states WHERE id = ?",
                (state_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return State.model_validate_json(row["data"])

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            self._conn.close()

    def __enter__(self) -> SQLiteMemoryStore:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
