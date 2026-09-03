"""Full Runtime engine with retry, timeout, cancel, and approval (Phase7)."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from datetime import UTC, datetime

from planner.base import DecisionType, Planner, PlannerOutput
from pydantic import ValidationError
from tools.base import Observation, ToolCall, ToolCallStatus
from tools.executor import ToolExecutor

from runtime.models import Message, MessageRole, State, StateStatus
from runtime.state_machine import (
    InvalidTransitionError,
    RuntimePhase,
    to_state_status,
    transition,
)

ApprovalCallback = Callable[[ToolCall], bool]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _observation_text(observation: Observation) -> str:
    if isinstance(observation.content, str):
        return observation.content
    return json.dumps(observation.content)


class RuntimeEngine:
    """Production Runtime orchestrator (composition used by CLI)."""

    def __init__(
        self,
        *,
        planner: Planner,
        executor: ToolExecutor,
        max_steps: int = 8,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.01,
        run_timeout: float | None = 300.0,
        tool_timeout: float | None = 30.0,
        llm_timeout: float | None = 60.0,
        require_approval_for: frozenset[str] | None = None,
        approval_callback: ApprovalCallback | None = None,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._max_steps = max_steps
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._run_timeout = run_timeout
        self._tool_timeout = tool_timeout
        self._llm_timeout = llm_timeout
        self._require_approval_for = require_approval_for or frozenset()
        self._approval_callback = approval_callback
        self._phases: dict[str, RuntimePhase] = {}
        self._cancelled: set[str] = set()
        self._active: dict[str, State] = {}

    def run(self, user_message: Message) -> State:
        state = State(
            messages=[user_message],
            status=StateStatus.CREATED,
        )
        self._active[state.id] = state
        self._phases[state.id] = RuntimePhase.IDLE
        started = time.monotonic()
        try:
            state = self._enter(state, RuntimePhase.PLANNING)
            return self._run_loop(state, started=started)
        finally:
            self._active.pop(state.id, None)
            self._cancelled.discard(state.id)

    def cancel(self, state_id: str) -> None:
        """Request cancellation; the run loop exits at the next safe checkpoint."""
        self._cancelled.add(state_id)

    def phase_of(self, state_id: str) -> RuntimePhase | None:
        return self._phases.get(state_id)

    def _run_loop(self, state: State, *, started: float) -> State:
        retries = 0
        for _ in range(self._max_steps):
            if self._is_cancelled(state.id):
                return self._enter(state, RuntimePhase.CANCELLED)
            if self._run_timed_out(started):
                return self._fail(state, "run timeout exceeded")

            try:
                output = self._plan_with_timeout(state)
            except ValidationError as exc:
                retries += 1
                if retries > self._max_retries:
                    return self._fail(state, f"planner validation failed: {exc}")
                self._backoff(retries)
                state = self._enter(state, RuntimePhase.PLANNING)
                continue
            except TimeoutError:
                return self._fail(state, "llm/planner timeout exceeded")
            except Exception as exc:  # noqa: BLE001 - surface planner failures
                retries += 1
                if retries > self._max_retries:
                    return self._fail(state, f"planner failed: {exc}")
                self._backoff(retries)
                state = self._enter(state, RuntimePhase.PLANNING)
                continue

            state = _with_planner_output(state, output)
            retries = 0

            if self._is_cancelled(state.id):
                return self._enter(state, RuntimePhase.CANCELLED)
            if self._run_timed_out(started):
                return self._fail(state, "run timeout exceeded")

            if output.decision_type in {DecisionType.REPLY, DecisionType.CLARIFY}:
                state = self._enter(state, RuntimePhase.EXECUTING)
                return self._complete(state, output)

            if output.decision_type == DecisionType.TOOL_CALL:
                state, cont, retries = self._handle_tool_call(
                    state, output, retries=retries, started=started
                )
                if not cont:
                    return state
                continue

            return self._fail(state, f"unsupported decision: {output.decision_type}")

        return self._fail(state, f"exceeded max_steps={self._max_steps}")

    def _handle_tool_call(
        self,
        state: State,
        output: PlannerOutput,
        *,
        retries: int,
        started: float,
    ) -> tuple[State, bool, int]:
        if output.tool_call is None:
            return (
                self._fail(state, "tool_call decision missing tool_call"),
                False,
                retries,
            )

        pending = output.tool_call.model_copy(update={"status": ToolCallStatus.PENDING})
        if pending.tool_name in self._require_approval_for:
            state = self._enter(state, RuntimePhase.WAITING_APPROVAL)
            if self._is_cancelled(state.id):
                return self._enter(state, RuntimePhase.CANCELLED), False, retries
            approved = self._request_approval(pending)
            if not approved:
                note = Message(
                    role=MessageRole.ASSISTANT,
                    content=f"Tool '{pending.tool_name}' was rejected.",
                )
                state = state.model_copy(
                    update={
                        "messages": [*state.messages, note],
                        "updated_at": _utcnow(),
                    }
                )
                state = self._enter(state, RuntimePhase.PLANNING)
                return state, True, retries

        state = self._enter(state, RuntimePhase.EXECUTING)
        state = state.model_copy(
            update={
                "tool_calls": [*state.tool_calls, pending],
                "updated_at": _utcnow(),
            }
        )
        state = self._enter(state, RuntimePhase.WAITING_TOOL)

        if self._is_cancelled(state.id):
            return self._enter(state, RuntimePhase.CANCELLED), False, retries
        if self._run_timed_out(started):
            return self._fail(state, "run timeout exceeded"), False, retries

        try:
            finished, observation = self._execute_tool_with_timeout(pending)
        except TimeoutError:
            retries += 1
            if retries > self._max_retries:
                return self._fail(state, "tool timeout exceeded"), False, retries
            self._backoff(retries)
            # Retry Executing after tool timeout.
            state = self._enter(state, RuntimePhase.EXECUTING)
            state = self._enter(state, RuntimePhase.WAITING_TOOL)
            try:
                finished, observation = self._execute_tool_with_timeout(pending)
            except TimeoutError:
                return self._fail(state, "tool timeout exceeded"), False, retries

        tool_message = Message(
            role=MessageRole.TOOL,
            content=_observation_text(observation),
            metadata={
                "tool_call_id": observation.tool_call_id,
                "tool_name": finished.tool_name,
                "success": observation.success,
            },
        )
        state = state.model_copy(
            update={
                "tool_calls": [*state.tool_calls[:-1], finished],
                "observations": [*state.observations, observation],
                "messages": [*state.messages, tool_message],
                "updated_at": _utcnow(),
            }
        )

        if not observation.success:
            retries += 1
            if retries > self._max_retries:
                return (
                    self._fail(
                        state, f"tool failed after retries: {observation.error}"
                    ),
                    False,
                    retries,
                )
            self._backoff(retries)
            state = self._enter(state, RuntimePhase.PLANNING)
            return state, True, retries

        state = self._enter(state, RuntimePhase.PLANNING)
        return state, True, 0

    def _plan_with_timeout(self, state: State) -> PlannerOutput:
        return self._call_with_timeout(
            lambda: self._planner.plan(state),
            timeout=self._llm_timeout,
            label="planner",
        )

    def _execute_tool_with_timeout(
        self, tool_call: ToolCall
    ) -> tuple[ToolCall, Observation]:
        return self._call_with_timeout(
            lambda: self._executor.execute(tool_call),
            timeout=self._tool_timeout,
            label="tool",
        )

    def _call_with_timeout(
        self, fn: Callable[[], object], *, timeout: float | None, label: str
    ):
        if timeout is None:
            return fn()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(fn)
            try:
                return future.result(timeout=timeout)
            except FuturesTimeout as exc:
                raise TimeoutError(f"{label} timeout exceeded") from exc

    def _request_approval(self, tool_call: ToolCall) -> bool:
        if self._approval_callback is None:
            return False
        return bool(self._approval_callback(tool_call))

    def _backoff(self, retries: int) -> None:
        time.sleep(self._retry_backoff_seconds * (2 ** max(retries - 1, 0)))

    def _run_timed_out(self, started: float) -> bool:
        if self._run_timeout is None:
            return False
        return (time.monotonic() - started) >= self._run_timeout

    def _is_cancelled(self, state_id: str) -> bool:
        return state_id in self._cancelled

    def _enter(self, state: State, phase: RuntimePhase) -> State:
        current = self._phases.get(state.id, RuntimePhase.IDLE)
        try:
            new_phase = transition(current, phase)
        except InvalidTransitionError:
            # Cancel can interrupt most phases; force terminal cancel/fail if needed.
            if phase == RuntimePhase.CANCELLED and current not in {
                RuntimePhase.COMPLETED,
                RuntimePhase.FAILED,
                RuntimePhase.CANCELLED,
            }:
                new_phase = RuntimePhase.CANCELLED
            else:
                raise
        self._phases[state.id] = new_phase
        status = to_state_status(new_phase)
        update: dict[str, object] = {"updated_at": _utcnow()}
        if status is not None:
            update["status"] = status
        updated = state.model_copy(update=update)
        if state.id in self._active:
            self._active[state.id] = updated
        return updated

    def _complete(self, state: State, output: PlannerOutput) -> State:
        text = (
            output.content
            if output.decision_type == DecisionType.REPLY
            else output.clarify_message
        )
        message = Message(role=MessageRole.ASSISTANT, content=text or "")
        state = state.model_copy(
            update={
                "messages": [*state.messages, message],
                "updated_at": _utcnow(),
            }
        )
        return self._enter(state, RuntimePhase.COMPLETED)

    def _fail(self, state: State, error: str) -> State:
        state = state.model_copy(update={"error": error, "updated_at": _utcnow()})
        return self._enter(state, RuntimePhase.FAILED)


def _with_planner_output(state: State, output: PlannerOutput) -> State:
    return state.model_copy(
        update={
            "planner_outputs": [*state.planner_outputs, output],
            "updated_at": _utcnow(),
        }
    )
