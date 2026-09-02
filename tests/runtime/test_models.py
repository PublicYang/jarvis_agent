"""Tests for runtime domain models (Phase3)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from runtime.models import (
    Message,
    MessageRole,
    State,
    StateStatus,
    Task,
    TaskStatus,
)


def test_message_creation_with_defaults() -> None:
    message = Message(role=MessageRole.USER, content="hello")

    assert message.role == MessageRole.USER
    assert message.content == "hello"
    assert message.metadata == {}
    assert message.id
    assert message.created_at.tzinfo is not None


def test_message_is_immutable() -> None:
    message = Message(role=MessageRole.USER, content="hello")

    with pytest.raises(ValidationError):
        message.content = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("role", list(MessageRole))
def test_message_roles(role: MessageRole) -> None:
    message = Message(role=role, content="test")
    assert message.role == role


def test_message_serialization_roundtrip() -> None:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    message = Message(
        id="msg-1",
        role=MessageRole.ASSISTANT,
        content="reply",
        metadata={"source": "test"},
        created_at=created_at,
    )

    restored = Message.model_validate(message.model_dump())
    assert restored == message


def test_state_defaults() -> None:
    state = State()

    assert state.status == StateStatus.CREATED
    assert state.messages == []
    assert state.task is None
    assert state.tool_calls == []
    assert state.observations == []
    assert state.planner_outputs == []
    assert state.memory_refs == []
    assert state.error is None
    assert state.id
    assert state.created_at.tzinfo is not None
    assert state.updated_at.tzinfo is not None


def test_state_with_messages_and_task() -> None:
    message = Message(role=MessageRole.USER, content="do something")
    task = Task(description="demo", goal="complete demo")
    state = State(messages=[message], task=task, status=StateStatus.RUNNING)

    assert len(state.messages) == 1
    assert state.messages[0].content == "do something"
    assert state.task is not None
    assert state.task.goal == "complete demo"
    assert state.status == StateStatus.RUNNING


@pytest.mark.parametrize("status", list(StateStatus))
def test_state_status_values(status: StateStatus) -> None:
    state = State(status=status)
    assert state.status == status


def test_task_defaults_and_subtasks() -> None:
    subtask = Task(description="sub", goal="sub goal")
    task = Task(description="main", goal="main goal", subtasks=[subtask])

    assert task.status == TaskStatus.PENDING
    assert len(task.subtasks) == 1
    assert task.subtasks[0].goal == "sub goal"


@pytest.mark.parametrize("status", list(TaskStatus))
def test_task_status_values(status: TaskStatus) -> None:
    task = Task(description="t", goal="g", status=status)
    assert task.status == status


def test_state_failed_with_error() -> None:
    state = State(status=StateStatus.FAILED, error="something went wrong")
    assert state.error == "something went wrong"
