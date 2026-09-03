"""Runtime domain models (Phase3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from tools.base import Observation, ToolCall


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    """A single conversation message. Immutable after creation."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_new_id)
    role: MessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)


class StateStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: str = Field(default_factory=_new_id)
    description: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    subtasks: list[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class State(BaseModel):
    id: str = Field(default_factory=_new_id)
    status: StateStatus = StateStatus.CREATED
    messages: list[Message] = Field(default_factory=list)
    task: Task | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    planner_outputs: list[Any] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
