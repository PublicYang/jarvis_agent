"""Memory store interfaces and in-memory implementation (Phase8)."""

from __future__ import annotations

import threading
from typing import Protocol, runtime_checkable

from memory.models import MemoryRecord, MemoryScope


@runtime_checkable
class MemoryStore(Protocol):
    """Protocol defining the memory storage interface."""

    def write(self, record: MemoryRecord) -> None: ...

    def read(self, key: str, scope: MemoryScope) -> MemoryRecord | None: ...

    def search(
        self,
        query: str,
        limit: int = 10,
        scope: MemoryScope | None = None,
    ) -> list[MemoryRecord]: ...

    def delete(self, record_id: str) -> None: ...

    def get(self, record_id: str) -> MemoryRecord | None: ...


class InMemoryMemoryStore:
    """Thread-safe in-memory implementation of MemoryStore."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, MemoryRecord] = {}
        self._key_scope_index: dict[tuple[str, MemoryScope], str] = {}

    def write(self, record: MemoryRecord) -> None:
        """Write or update a memory record.

        If a record already exists with the same (key, scope), it will be replaced
        to prevent stale memory contamination.
        """
        with self._lock:
            key_scope = (record.key, record.scope)
            existing_id = self._key_scope_index.get(key_scope)
            if existing_id and existing_id != record.id:
                self._records.pop(existing_id, None)

            old_record = self._records.get(record.id)
            if old_record:
                old_key_scope = (old_record.key, old_record.scope)
                if old_key_scope != key_scope:
                    self._key_scope_index.pop(old_key_scope, None)

            self._records[record.id] = record
            self._key_scope_index[key_scope] = record.id

    def read(self, key: str, scope: MemoryScope) -> MemoryRecord | None:
        """Read a record by key and scope, returning None if not found or expired."""
        with self._lock:
            record_id = self._key_scope_index.get((key, scope))
            if not record_id:
                return None
            record = self._records.get(record_id)
            if record is None or record.is_expired():
                return None
            return record

    def get(self, record_id: str) -> MemoryRecord | None:
        """Get a record by ID, returning None if not found or expired."""
        with self._lock:
            record = self._records.get(record_id)
            if record is None or record.is_expired():
                return None
            return record

    def search(
        self,
        query: str,
        limit: int = 10,
        scope: MemoryScope | None = None,
    ) -> list[MemoryRecord]:
        """Search non-expired records matching query in key or content."""
        with self._lock:
            q = query.lower().strip()
            matches: list[MemoryRecord] = []
            for record in self._records.values():
                if record.is_expired():
                    continue
                if scope is not None and record.scope != scope:
                    continue
                k_lower = record.key.lower()
                c_lower = record.content.lower()
                if not q:
                    matches.append(record)
                elif (
                    q in k_lower
                    or q in c_lower
                    or (len(k_lower) > 1 and k_lower in q)
                    or (len(c_lower) > 1 and c_lower in q)
                ):
                    matches.append(record)

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
        """Delete a record by its ID."""
        with self._lock:
            record = self._records.pop(record_id, None)
            if record is not None:
                key_scope = (record.key, record.scope)
                if self._key_scope_index.get(key_scope) == record_id:
                    self._key_scope_index.pop(key_scope, None)

    def cleanup_expired(self) -> int:
        """Remove all expired records and return the count of removed records."""
        with self._lock:
            expired_ids = [
                rec_id for rec_id, rec in self._records.items() if rec.is_expired()
            ]
            for rec_id in expired_ids:
                self.delete(rec_id)
            return len(expired_ids)

    def count(self) -> int:
        """Return the count of active (non-expired) records."""
        with self._lock:
            return sum(1 for rec in self._records.values() if not rec.is_expired())
