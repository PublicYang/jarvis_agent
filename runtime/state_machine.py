"""Runtime phase state machine (Phase7)."""

from __future__ import annotations

from enum import StrEnum

from runtime.models import StateStatus


class RuntimePhase(StrEnum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_TOOL = "waiting_tool"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS: dict[RuntimePhase, frozenset[RuntimePhase]] = {
    RuntimePhase.IDLE: frozenset(
        {RuntimePhase.PLANNING, RuntimePhase.CANCELLED, RuntimePhase.FAILED}
    ),
    RuntimePhase.PLANNING: frozenset(
        {
            RuntimePhase.EXECUTING,
            RuntimePhase.WAITING_APPROVAL,
            RuntimePhase.PLANNING,
            RuntimePhase.COMPLETED,
            RuntimePhase.FAILED,
            RuntimePhase.CANCELLED,
        }
    ),
    RuntimePhase.EXECUTING: frozenset(
        {
            RuntimePhase.WAITING_TOOL,
            RuntimePhase.PLANNING,
            RuntimePhase.COMPLETED,
            RuntimePhase.FAILED,
            RuntimePhase.CANCELLED,
        }
    ),
    RuntimePhase.WAITING_TOOL: frozenset(
        {
            RuntimePhase.PLANNING,
            RuntimePhase.EXECUTING,
            RuntimePhase.FAILED,
            RuntimePhase.CANCELLED,
        }
    ),
    RuntimePhase.WAITING_APPROVAL: frozenset(
        {
            RuntimePhase.EXECUTING,
            RuntimePhase.PLANNING,
            RuntimePhase.CANCELLED,
            RuntimePhase.FAILED,
        }
    ),
    RuntimePhase.COMPLETED: frozenset(),
    RuntimePhase.FAILED: frozenset(),
    RuntimePhase.CANCELLED: frozenset(),
}


class InvalidTransitionError(ValueError):
    """Raised when a RuntimePhase transition is not allowed."""


def transition(current: RuntimePhase, target: RuntimePhase) -> RuntimePhase:
    allowed = ALLOWED_TRANSITIONS[current]
    if target not in allowed:
        raise InvalidTransitionError(f"cannot transition {current} → {target}")
    return target


def to_state_status(phase: RuntimePhase) -> StateStatus | None:
    """Map Runtime phase to State.status (Idle has no State mapping)."""
    mapping: dict[RuntimePhase, StateStatus | None] = {
        RuntimePhase.IDLE: None,
        RuntimePhase.PLANNING: StateStatus.RUNNING,
        RuntimePhase.EXECUTING: StateStatus.RUNNING,
        RuntimePhase.WAITING_TOOL: StateStatus.WAITING_TOOL,
        RuntimePhase.WAITING_APPROVAL: StateStatus.RUNNING,
        RuntimePhase.COMPLETED: StateStatus.COMPLETED,
        RuntimePhase.FAILED: StateStatus.FAILED,
        RuntimePhase.CANCELLED: StateStatus.CANCELLED,
    }
    return mapping[phase]
