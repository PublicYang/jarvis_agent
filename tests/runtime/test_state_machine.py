"""Tests for RuntimePhase transitions (Phase7)."""

from __future__ import annotations

import pytest
from runtime.models import StateStatus
from runtime.state_machine import (
    InvalidTransitionError,
    RuntimePhase,
    to_state_status,
    transition,
)


def test_idle_to_planning() -> None:
    assert transition(RuntimePhase.IDLE, RuntimePhase.PLANNING) == RuntimePhase.PLANNING


def test_invalid_transition_raises() -> None:
    with pytest.raises(InvalidTransitionError):
        transition(RuntimePhase.COMPLETED, RuntimePhase.PLANNING)


def test_phase_to_state_status_mapping() -> None:
    assert to_state_status(RuntimePhase.IDLE) is None
    assert to_state_status(RuntimePhase.PLANNING) == StateStatus.RUNNING
    assert to_state_status(RuntimePhase.EXECUTING) == StateStatus.RUNNING
    assert to_state_status(RuntimePhase.WAITING_TOOL) == StateStatus.WAITING_TOOL
    assert to_state_status(RuntimePhase.WAITING_APPROVAL) == StateStatus.RUNNING
    assert to_state_status(RuntimePhase.COMPLETED) == StateStatus.COMPLETED
    assert to_state_status(RuntimePhase.FAILED) == StateStatus.FAILED
    assert to_state_status(RuntimePhase.CANCELLED) == StateStatus.CANCELLED
