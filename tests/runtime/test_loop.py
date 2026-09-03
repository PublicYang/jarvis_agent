"""Closed-loop integration tests: Planning → Tool → Planning → Reply (Phase6)."""

from __future__ import annotations

from planner.base import DecisionType, PlannerOutput
from runtime.loop import AgentLoop
from runtime.models import Message, MessageRole, State, StateStatus
from tools.base import ToolCall, ToolCallStatus
from tools.echo import EchoTool
from tools.executor import ToolExecutor
from tools.registry import InMemoryToolRegistry


class ScriptedPlanner:
    """Test planner that returns a fixed sequence of decisions."""

    def __init__(self, outputs: list[PlannerOutput]) -> None:
        self._outputs = list(outputs)

    def plan(self, state: State) -> PlannerOutput:
        if not self._outputs:
            raise AssertionError("ScriptedPlanner has no remaining decisions")
        return self._outputs.pop(0)


def _loop() -> AgentLoop:
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    return AgentLoop(
        planner=ScriptedPlanner(
            [
                PlannerOutput(
                    decision_type=DecisionType.TOOL_CALL,
                    tool_call=ToolCall(tool_name="echo", arguments={"text": "jarvis"}),
                ),
                PlannerOutput(
                    decision_type=DecisionType.REPLY,
                    content="echoed jarvis",
                ),
            ]
        ),
        executor=ToolExecutor(registry),
    )


def test_closed_loop_planning_tool_planning_reply() -> None:
    loop = _loop()
    initial = State(messages=[Message(role=MessageRole.USER, content="echo jarvis")])
    snapshot = initial.model_dump()

    final = loop.run(initial)

    assert initial.model_dump() == snapshot
    assert final.status == StateStatus.COMPLETED
    assert [message.role for message in final.messages] == [
        MessageRole.USER,
        MessageRole.TOOL,
        MessageRole.ASSISTANT,
    ]
    assert final.messages[1].content == "jarvis"
    assert final.messages[2].content == "echoed jarvis"


def test_closed_loop_tool_call_is_traceable() -> None:
    final = _loop().run(
        State(messages=[Message(role=MessageRole.USER, content="echo jarvis")])
    )

    assert len(final.tool_calls) == 1
    assert len(final.observations) == 1
    tool_call = final.tool_calls[0]
    observation = final.observations[0]
    assert tool_call.tool_name == "echo"
    assert tool_call.status == ToolCallStatus.COMPLETED
    assert observation.tool_call_id == tool_call.id
    assert observation.success is True
    assert observation.content == "jarvis"
    assert final.messages[1].metadata["tool_call_id"] == tool_call.id
    assert len(final.planner_outputs) == 2


def test_loop_second_plan_sees_observation() -> None:
    seen_observations: list[int] = []

    class InspectingPlanner(ScriptedPlanner):
        def plan(self, state: State) -> PlannerOutput:
            seen_observations.append(len(state.observations))
            return super().plan(state)

    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    loop = AgentLoop(
        planner=InspectingPlanner(
            [
                PlannerOutput(
                    decision_type=DecisionType.TOOL_CALL,
                    tool_call=ToolCall(tool_name="echo", arguments={"text": "x"}),
                ),
                PlannerOutput(
                    decision_type=DecisionType.REPLY,
                    content="done",
                ),
            ]
        ),
        executor=ToolExecutor(registry),
    )

    loop.run(State(messages=[Message(role=MessageRole.USER, content="go")]))

    assert seen_observations == [0, 1]


def test_loop_reply_without_tool() -> None:
    registry = InMemoryToolRegistry()
    loop = AgentLoop(
        planner=ScriptedPlanner(
            [PlannerOutput(decision_type=DecisionType.REPLY, content="hi")]
        ),
        executor=ToolExecutor(registry),
    )
    final = loop.run(State(messages=[Message(role=MessageRole.USER, content="hello")]))
    assert final.status == StateStatus.COMPLETED
    assert final.tool_calls == []
    assert final.messages[-1].content == "hi"


def test_loop_fails_when_max_steps_exceeded() -> None:
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    loop = AgentLoop(
        planner=ScriptedPlanner(
            [
                PlannerOutput(
                    decision_type=DecisionType.TOOL_CALL,
                    tool_call=ToolCall(tool_name="echo", arguments={"text": "a"}),
                ),
                PlannerOutput(
                    decision_type=DecisionType.TOOL_CALL,
                    tool_call=ToolCall(tool_name="echo", arguments={"text": "b"}),
                ),
            ]
        ),
        executor=ToolExecutor(registry),
        max_steps=2,
    )

    final = loop.run(State(messages=[Message(role=MessageRole.USER, content="go")]))

    assert final.status == StateStatus.FAILED
    assert final.error is not None
    assert "max_steps" in final.error
    assert len(final.tool_calls) == 2
