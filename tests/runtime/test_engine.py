"""Tests for RuntimeEngine retry / timeout / cancel / approval (Phase7)."""

from __future__ import annotations

import time

from planner.base import DecisionType, PlannerOutput
from runtime.engine import RuntimeEngine
from runtime.models import Message, MessageRole, State, StateStatus
from runtime.state_machine import RuntimePhase
from tools.base import ToolCall, ToolCallStatus
from tools.echo import EchoTool
from tools.executor import ToolExecutor
from tools.registry import InMemoryToolRegistry


class ScriptedPlanner:
    def __init__(self, outputs: list[PlannerOutput]) -> None:
        self._outputs = list(outputs)

    def plan(self, state: State) -> PlannerOutput:
        if not self._outputs:
            raise AssertionError("no remaining planner outputs")
        return self._outputs.pop(0)


class FlakyPlanner:
    def __init__(self, failures_before_success: int) -> None:
        self._remaining_failures = failures_before_success

    def plan(self, state: State) -> PlannerOutput:
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise RuntimeError("transient planner error")
        return PlannerOutput(decision_type=DecisionType.REPLY, content="recovered")


class SlowPlanner:
    def __init__(self, delay: float) -> None:
        self._delay = delay

    def plan(self, state: State) -> PlannerOutput:
        time.sleep(self._delay)
        return PlannerOutput(decision_type=DecisionType.REPLY, content="late")


class CancellingPlanner:
    def __init__(self, engine: RuntimeEngine) -> None:
        self._engine = engine

    def plan(self, state: State) -> PlannerOutput:
        self._engine.cancel(state.id)
        return PlannerOutput(decision_type=DecisionType.REPLY, content="ignored")


class SlowTool:
    def __init__(self, delay: float) -> None:
        self._delay = delay

    @property
    def definition(self):
        return {
            "name": "slow",
            "description": "Sleeps then returns",
            "parameters": {"type": "object", "properties": {}},
        }

    def execute(self, arguments: dict):
        time.sleep(self._delay)
        from tools.base import Observation

        return Observation(tool_call_id="", success=True, content="done")

    async def aexecute(self, arguments: dict):
        return self.execute(arguments)


def _engine(
    planner,
    *,
    tools=None,
    max_retries: int = 3,
    retry_backoff_seconds: float = 0.0,
    run_timeout: float | None = 300.0,
    tool_timeout: float | None = 30.0,
    llm_timeout: float | None = 60.0,
    require_approval_for: frozenset[str] | None = None,
    approval_callback=None,
) -> RuntimeEngine:
    registry = InMemoryToolRegistry()
    for tool in tools or [EchoTool()]:
        registry.register(tool)
    return RuntimeEngine(
        planner=planner,
        executor=ToolExecutor(registry),
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        run_timeout=run_timeout,
        tool_timeout=tool_timeout,
        llm_timeout=llm_timeout,
        require_approval_for=require_approval_for,
        approval_callback=approval_callback,
    )


def test_engine_reply_path() -> None:
    engine = _engine(
        ScriptedPlanner(
            [PlannerOutput(decision_type=DecisionType.REPLY, content="hello")]
        )
    )
    final = engine.run(Message(role=MessageRole.USER, content="hi"))
    assert final.status == StateStatus.COMPLETED
    assert final.messages[-1].content == "hello"
    assert engine.phase_of(final.id) == RuntimePhase.COMPLETED


def test_engine_tool_then_reply() -> None:
    engine = _engine(
        ScriptedPlanner(
            [
                PlannerOutput(
                    decision_type=DecisionType.TOOL_CALL,
                    tool_call=ToolCall(tool_name="echo", arguments={"text": "x"}),
                ),
                PlannerOutput(decision_type=DecisionType.REPLY, content="done"),
            ]
        )
    )
    final = engine.run(Message(role=MessageRole.USER, content="go"))
    assert final.status == StateStatus.COMPLETED
    assert final.tool_calls[0].status == ToolCallStatus.COMPLETED
    assert final.observations[0].content == "x"


def test_engine_retries_planner_failures() -> None:
    engine = _engine(FlakyPlanner(failures_before_success=2), max_retries=3)
    final = engine.run(Message(role=MessageRole.USER, content="hi"))
    assert final.status == StateStatus.COMPLETED
    assert final.messages[-1].content == "recovered"


def test_engine_fails_after_max_planner_retries() -> None:
    engine = _engine(FlakyPlanner(failures_before_success=5), max_retries=2)
    final = engine.run(Message(role=MessageRole.USER, content="hi"))
    assert final.status == StateStatus.FAILED
    assert final.error is not None
    assert "planner failed" in final.error


def test_engine_llm_timeout() -> None:
    engine = _engine(SlowPlanner(delay=0.2), llm_timeout=0.05, max_retries=0)
    final = engine.run(Message(role=MessageRole.USER, content="hi"))
    assert final.status == StateStatus.FAILED
    assert final.error is not None
    assert "timeout" in final.error


def test_engine_run_timeout() -> None:
    engine = _engine(SlowPlanner(delay=0.2), run_timeout=0.05, llm_timeout=None)
    final = engine.run(Message(role=MessageRole.USER, content="hi"))
    assert final.status == StateStatus.FAILED
    assert final.error is not None
    assert "run timeout" in final.error


def test_engine_cancel_during_planning() -> None:
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    engine = RuntimeEngine(
        planner=ScriptedPlanner(
            [PlannerOutput(decision_type=DecisionType.REPLY, content="unused")]
        ),
        executor=ToolExecutor(registry),
        retry_backoff_seconds=0.0,
    )
    engine._planner = CancellingPlanner(engine)

    final = engine.run(Message(role=MessageRole.USER, content="hi"))
    assert final.status == StateStatus.CANCELLED
    assert engine.phase_of(final.id) == RuntimePhase.CANCELLED


def test_engine_approval_rejected_returns_to_planning() -> None:
    engine = _engine(
        ScriptedPlanner(
            [
                PlannerOutput(
                    decision_type=DecisionType.TOOL_CALL,
                    tool_call=ToolCall(tool_name="echo", arguments={"text": "secret"}),
                ),
                PlannerOutput(
                    decision_type=DecisionType.REPLY,
                    content="after rejection",
                ),
            ]
        ),
        require_approval_for=frozenset({"echo"}),
        approval_callback=lambda tool_call: False,
    )
    final = engine.run(Message(role=MessageRole.USER, content="go"))
    assert final.status == StateStatus.COMPLETED
    assert final.tool_calls == []
    assert final.messages[-1].content == "after rejection"
    assert any("rejected" in message.content for message in final.messages)


def test_engine_approval_approved_executes_tool() -> None:
    engine = _engine(
        ScriptedPlanner(
            [
                PlannerOutput(
                    decision_type=DecisionType.TOOL_CALL,
                    tool_call=ToolCall(tool_name="echo", arguments={"text": "ok"}),
                ),
                PlannerOutput(decision_type=DecisionType.REPLY, content="done"),
            ]
        ),
        require_approval_for=frozenset({"echo"}),
        approval_callback=lambda tool_call: True,
    )
    final = engine.run(Message(role=MessageRole.USER, content="go"))
    assert final.status == StateStatus.COMPLETED
    assert len(final.tool_calls) == 1
    assert final.observations[0].content == "ok"


def test_engine_tool_timeout_fails() -> None:
    engine = _engine(
        ScriptedPlanner(
            [
                PlannerOutput(
                    decision_type=DecisionType.TOOL_CALL,
                    tool_call=ToolCall(tool_name="slow", arguments={}),
                )
            ]
        ),
        tools=[SlowTool(delay=0.2)],
        tool_timeout=0.05,
        max_retries=0,
        retry_backoff_seconds=0.0,
    )
    final = engine.run(Message(role=MessageRole.USER, content="go"))
    assert final.status == StateStatus.FAILED
    assert final.error is not None
    assert "tool timeout" in final.error
