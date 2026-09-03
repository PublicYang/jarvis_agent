"""Tests for planner models and SimplePlanner (Phase5)."""

from __future__ import annotations

import pytest
from llm.adapter import LLMRequest, LLMResponse
from planner.base import DecisionType, PlannerOutput
from planner.simple import SimplePlanner, planning_state
from pydantic import ValidationError
from runtime.models import Message, MessageRole, State, StateStatus
from tools.base import ToolCall


class StubLLM:
    def __init__(self, response: LLMResponse) -> None:
        self._response = response
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return self._response

    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        return self.complete(request)


def test_planner_output_reply_validation() -> None:
    output = PlannerOutput(decision_type=DecisionType.REPLY, content="done")
    assert output.decision_type == DecisionType.REPLY
    assert output.content == "done"


def test_planner_output_reply_requires_content() -> None:
    with pytest.raises(ValidationError):
        PlannerOutput(decision_type=DecisionType.REPLY)


def test_planner_output_tool_call_validation() -> None:
    output = PlannerOutput(
        decision_type=DecisionType.TOOL_CALL,
        tool_call=ToolCall(tool_name="search", arguments={"q": "jarvis"}),
    )
    assert output.tool_call is not None
    assert output.tool_call.tool_name == "search"


def test_planner_output_clarify_validation() -> None:
    output = PlannerOutput(
        decision_type=DecisionType.CLARIFY,
        clarify_message="What do you mean?",
    )
    assert output.clarify_message == "What do you mean?"


def test_planning_state_sets_running() -> None:
    state = State(status=StateStatus.CREATED)
    planned = planning_state(state)
    assert planned.status == StateStatus.RUNNING
    assert state.status == StateStatus.CREATED


def test_simple_planner_clarify_without_user_message() -> None:
    llm = StubLLM(
        {"content": "unused", "finish_reason": "stop", "usage": {"total_tokens": 0}}
    )
    planner = SimplePlanner(llm=llm, model="gpt-4o-mini")
    state = State(
        messages=[Message(role=MessageRole.SYSTEM, content="You are helpful.")]
    )

    output = planner.plan(state)

    assert output.decision_type == DecisionType.CLARIFY
    assert output.clarify_message
    assert llm.requests == []


def test_simple_planner_reply_with_mock_llm() -> None:
    llm = StubLLM(
        {
            "content": "Hello from LLM",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }
    )
    planner = SimplePlanner(llm=llm, model="gpt-4o-mini", temperature=0.1)
    state = State(
        messages=[Message(role=MessageRole.USER, content="hi")],
        status=StateStatus.RUNNING,
    )
    before = state.model_dump()

    output = planner.plan(state)

    assert output.decision_type == DecisionType.REPLY
    assert output.content == "Hello from LLM"
    assert state.model_dump() == before
    assert len(llm.requests) == 1
    assert llm.requests[0]["model"] == "gpt-4o-mini"
    assert llm.requests[0]["temperature"] == 0.1
    assert llm.requests[0]["messages"] == state.messages
