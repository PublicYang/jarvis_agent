"""Tests for Tool registry, executor, and EchoTool (Phase6)."""

from __future__ import annotations

import pytest
from tools.base import ToolCall, ToolCallStatus
from tools.echo import EchoTool
from tools.executor import ToolExecutor
from tools.registry import InMemoryToolRegistry


def test_echo_tool_definition() -> None:
    tool = EchoTool()
    assert tool.definition["name"] == "echo"


def test_echo_tool_execute() -> None:
    observation = EchoTool().execute({"text": "hello"})
    assert observation.success is True
    assert observation.content == "hello"


def test_registry_register_and_list() -> None:
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())

    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "echo"
    assert registry.get("echo").definition["name"] == "echo"


def test_registry_rejects_duplicate_name() -> None:
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(EchoTool())


def test_registry_unknown_tool_returns_failed_observation() -> None:
    registry = InMemoryToolRegistry()
    tool_call = ToolCall(tool_name="missing", arguments={})

    observation = registry.execute(tool_call)

    assert observation.success is False
    assert observation.tool_call_id == tool_call.id
    assert observation.error is not None
    assert "missing" in observation.error


def test_registry_stamps_tool_call_id() -> None:
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    tool_call = ToolCall(tool_name="echo", arguments={"text": "hi"})

    observation = registry.execute(tool_call)

    assert observation.tool_call_id == tool_call.id
    assert observation.content == "hi"


def test_executor_completes_successful_call() -> None:
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    executor = ToolExecutor(registry)
    tool_call = ToolCall(tool_name="echo", arguments={"text": "ping"})

    finished, observation = executor.execute(tool_call)

    assert tool_call.status == ToolCallStatus.PENDING
    assert finished.status == ToolCallStatus.COMPLETED
    assert finished.id == tool_call.id
    assert observation.success is True
    assert observation.tool_call_id == tool_call.id


def test_executor_marks_unknown_tool_failed() -> None:
    executor = ToolExecutor(InMemoryToolRegistry())
    tool_call = ToolCall(tool_name="nope", arguments={})

    finished, observation = executor.execute(tool_call)

    assert finished.status == ToolCallStatus.FAILED
    assert observation.success is False
