"""Minimal Runtime loop: Planning → Tool → Planning → Reply (Phase6)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from planner.base import DecisionType, Planner, PlannerOutput
from tools.base import Observation, ToolCallStatus
from tools.executor import ToolExecutor

from runtime.models import Message, MessageRole, State, StateStatus


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _observation_text(observation: Observation) -> str:
    if isinstance(observation.content, str):
        return observation.content
    return json.dumps(observation.content)


class AgentLoop:
    """Orchestrate Planner and ToolExecutor until reply, clarify, or max steps."""

    def __init__(
        self,
        *,
        planner: Planner,
        executor: ToolExecutor,
        max_steps: int = 8,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._max_steps = max_steps

    def run(self, state: State) -> State:
        current = state.model_copy(
            update={"status": StateStatus.RUNNING, "updated_at": _utcnow()}
        )
        for _ in range(self._max_steps):
            output = self._planner.plan(current)
            current = _with_planner_output(current, output)
            if output.decision_type in {DecisionType.REPLY, DecisionType.CLARIFY}:
                return _complete(current, output)
            current = self._run_tool(current, output)
        return current.model_copy(
            update={
                "status": StateStatus.FAILED,
                "error": f"exceeded max_steps={self._max_steps}",
                "updated_at": _utcnow(),
            }
        )

    def _run_tool(self, state: State, output: PlannerOutput) -> State:
        if output.tool_call is None:
            return state.model_copy(
                update={
                    "status": StateStatus.FAILED,
                    "error": "tool_call decision missing tool_call",
                    "updated_at": _utcnow(),
                }
            )
        pending = output.tool_call.model_copy(update={"status": ToolCallStatus.PENDING})
        waiting = state.model_copy(
            update={
                "status": StateStatus.WAITING_TOOL,
                "tool_calls": [*state.tool_calls, pending],
                "updated_at": _utcnow(),
            }
        )
        finished, observation = self._executor.execute(pending)
        tool_message = Message(
            role=MessageRole.TOOL,
            content=_observation_text(observation),
            metadata={
                "tool_call_id": observation.tool_call_id,
                "tool_name": finished.tool_name,
                "success": observation.success,
            },
        )
        return waiting.model_copy(
            update={
                "status": StateStatus.RUNNING,
                "tool_calls": [*waiting.tool_calls[:-1], finished],
                "observations": [*waiting.observations, observation],
                "messages": [*waiting.messages, tool_message],
                "updated_at": _utcnow(),
            }
        )


def _with_planner_output(state: State, output: PlannerOutput) -> State:
    return state.model_copy(
        update={
            "planner_outputs": [*state.planner_outputs, output],
            "updated_at": _utcnow(),
        }
    )


def _complete(state: State, output: PlannerOutput) -> State:
    text = (
        output.content
        if output.decision_type == DecisionType.REPLY
        else output.clarify_message
    )
    message = Message(role=MessageRole.ASSISTANT, content=text or "")
    return state.model_copy(
        update={
            "status": StateStatus.COMPLETED,
            "messages": [*state.messages, message],
            "updated_at": _utcnow(),
        }
    )
