"""Memory domain models (Phase8)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class MemoryScope(StrEnum):
    """Scope of a memory record to prevent context contamination."""

    SESSION = "session"
    USER = "user"
    GLOBAL = "global"


class MemoryRecord(BaseModel):
    """A unit of memory stored by the agent."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_new_id)
    key: str
    content: str
    scope: MemoryScope = MemoryScope.SESSION
    embedding_ref: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime | None = None

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check whether this record has expired."""
        if self.expires_at is None:
            return False
        check_time = now if now is not None else datetime.now(UTC)
        return self.expires_at <= check_time
