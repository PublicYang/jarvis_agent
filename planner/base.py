"""Planner interface and output models (Phase5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, model_validator
from runtime.models import State
from tools.base import ToolCall


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class DecisionType(StrEnum):
    REPLY = "reply"
    TOOL_CALL = "tool_call"
    CLARIFY = "clarify"


class PlannerOutput(BaseModel):
    id: str = Field(default_factory=_new_id)
    decision_type: DecisionType
    content: str | None = None
    tool_call: ToolCall | None = None
    clarify_message: str | None = None
    reasoning: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def validate_decision_fields(self) -> PlannerOutput:
        if self.decision_type == DecisionType.REPLY and not self.content:
            raise ValueError("reply decision requires content")
        if self.decision_type == DecisionType.TOOL_CALL and self.tool_call is None:
            raise ValueError("tool_call decision requires tool_call")
        if self.decision_type == DecisionType.CLARIFY and not self.clarify_message:
            raise ValueError("clarify decision requires clarify_message")
        return self


class Planner(Protocol):
    """Generate the next decision from read-only State."""

    def plan(self, state: State) -> PlannerOutput:
        """Must not mutate state."""
        ...
