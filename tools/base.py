"""Tool interface and domain models (Phase6)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class ToolCallStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolCall(BaseModel):
    """A single tool invocation. Status changes via model_copy."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_new_id)
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: ToolCallStatus = ToolCallStatus.PENDING
    created_at: datetime = Field(default_factory=_utcnow)


class Observation(BaseModel):
    """Immutable result of a ToolCall."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_new_id)
    tool_call_id: str
    success: bool
    content: str | dict[str, Any]
    error: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class ToolDefinition(TypedDict):
    name: str
    description: str
    parameters: dict[str, Any]


class Tool(Protocol):
    """Executable tool registered in ToolRegistry."""

    @property
    def definition(self) -> ToolDefinition:
        """Return tool metadata for Planner/LLM."""
        ...

    def execute(self, arguments: dict[str, Any]) -> Observation:
        """Execute the tool and return an Observation."""
        ...

    async def aexecute(self, arguments: dict[str, Any]) -> Observation:
        """Execute the tool asynchronously."""
        ...
