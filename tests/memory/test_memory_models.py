"""Unit tests for Memory domain models (Phase8)."""

from datetime import UTC, datetime, timedelta

import pytest
from memory.models import MemoryRecord, MemoryScope
from pydantic import ValidationError


def test_memory_record_defaults() -> None:
    rec = MemoryRecord(key="user_name", content="Alice")
    assert rec.id
    assert rec.key == "user_name"
    assert rec.content == "Alice"
    assert rec.scope == MemoryScope.SESSION
    assert rec.embedding_ref is None
    assert rec.expires_at is None
    assert isinstance(rec.created_at, datetime)
    assert not rec.is_expired()


def test_memory_record_is_immutable() -> None:
    rec = MemoryRecord(key="user_name", content="Alice")
    with pytest.raises(ValidationError):
        rec.content = "Bob"  # type: ignore[misc]


def test_memory_record_serialization_roundtrip() -> None:
    rec = MemoryRecord(
        key="pref",
        content="concise",
        scope=MemoryScope.USER,
        embedding_ref="emb_123",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    raw = rec.model_dump_json()
    reloaded = MemoryRecord.model_validate_json(raw)
    assert reloaded == rec


def test_memory_record_expiration() -> None:
    now = datetime.now(UTC)
    past = now - timedelta(minutes=5)
    future = now + timedelta(minutes=5)

    rec_permanent = MemoryRecord(key="k1", content="c1")
    rec_expired = MemoryRecord(key="k2", content="c2", expires_at=past)
    rec_valid = MemoryRecord(key="k3", content="c3", expires_at=future)

    assert not rec_permanent.is_expired()
    assert rec_expired.is_expired()
    assert not rec_valid.is_expired()

    # Test with custom reference time
    assert rec_valid.is_expired(now=future + timedelta(seconds=1))


def test_memory_scopes_values() -> None:
    assert MemoryScope.SESSION.value == "session"
    assert MemoryScope.USER.value == "user"
    assert MemoryScope.GLOBAL.value == "global"
