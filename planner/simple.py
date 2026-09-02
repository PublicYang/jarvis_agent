"""Simple LLM-backed planner (Phase5)."""

from __future__ import annotations

from llm.adapter import LLMAdapter, LLMRequest
from runtime.models import MessageRole, State, StateStatus

from planner.base import DecisionType, PlannerOutput


class SimplePlanner:
    """Calls the LLM adapter and returns a reply decision."""

    def __init__(
        self,
        *,
        llm: LLMAdapter,
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> None:
        self._llm = llm
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def plan(self, state: State) -> PlannerOutput:
        user_messages = [
            message for message in state.messages if message.role == MessageRole.USER
        ]
        if not user_messages:
            return PlannerOutput(
                decision_type=DecisionType.CLARIFY,
                clarify_message="Please provide a user message to continue.",
            )

        request: LLMRequest = {
            "messages": list(state.messages),
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        response = self._llm.complete(request)

        return PlannerOutput(
            decision_type=DecisionType.REPLY,
            content=response["content"],
            reasoning=f"finish_reason={response['finish_reason']}",
        )


def planning_state(state: State) -> State:
    """Mark state as running during planning (Phase5 helper for state machine tests)."""
    return state.model_copy(update={"status": StateStatus.RUNNING})
