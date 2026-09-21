"""Workflow execution engine with interrupt, resume, and replay (Phase12)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from workflow.edge import WorkflowGraph


class WorkflowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowExecutionError(Exception):
    """Raised when an error occurs during workflow engine operations."""


@dataclass(frozen=True)
class WorkflowStepRecord:
    """Historical trace record of a single node execution step."""

    step_index: int
    node_id: str
    input_context: dict[str, Any]
    output_context: dict[str, Any]
    timestamp: str


@dataclass
class WorkflowSnapshot:
    """Stateful execution snapshot for a workflow run."""

    run_id: str
    graph: WorkflowGraph
    status: WorkflowStatus
    current_node: str | None
    context: dict[str, Any]
    pending_transition_from: str | None = None
    history: list[WorkflowStepRecord] = field(default_factory=list)
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class WorkflowEngine:
    """Stateful workflow execution engine supporting interrupt and resume."""

    def __init__(self) -> None:
        self._runs: dict[str, WorkflowSnapshot] = {}
        self._interrupt_signals: set[str] = set()

    def run(
        self,
        graph: WorkflowGraph,
        input: dict[str, Any],
        *,
        run_id: str | None = None,
        interrupt_before: set[str] | None = None,
        interrupt_after: set[str] | None = None,
        max_steps: int = 1000,
    ) -> dict[str, Any]:
        """Execute workflow graph, pausing at breakpoints or completing."""
        graph.validate()

        actual_run_id = run_id or input.get("__run_id__") or str(uuid.uuid4())
        context = dict(input)
        context["__run_id__"] = actual_run_id

        snapshot = WorkflowSnapshot(
            run_id=actual_run_id,
            graph=graph,
            status=WorkflowStatus.RUNNING,
            current_node=graph.entry_point,
            context=context,
        )
        self._runs[actual_run_id] = snapshot

        return self._execute_loop(
            snapshot,
            interrupt_before=interrupt_before or set(),
            interrupt_after=interrupt_after or set(),
            max_steps=max_steps,
        )

    def interrupt(self, run_id: str) -> None:
        """Signal an active workflow run to pause at the next checkpoint."""
        self._interrupt_signals.add(run_id)
        snapshot = self._runs.get(run_id)
        if snapshot and snapshot.status == WorkflowStatus.RUNNING:
            snapshot.status = WorkflowStatus.INTERRUPTED
            snapshot.context["__status__"] = WorkflowStatus.INTERRUPTED.value
            snapshot.updated_at = datetime.now(UTC).isoformat()

    def resume(
        self,
        run_id: str,
        input: dict[str, Any] | None = None,
        *,
        interrupt_before: set[str] | None = None,
        interrupt_after: set[str] | None = None,
        max_steps: int = 1000,
    ) -> dict[str, Any]:
        """Resume an interrupted workflow run with optional updated context."""
        snapshot = self._runs.get(run_id)
        if not snapshot:
            raise WorkflowExecutionError(f"Workflow run '{run_id}' not found.")
        if snapshot.status != WorkflowStatus.INTERRUPTED:
            raise WorkflowExecutionError(
                f"Workflow run '{run_id}' is in status '{snapshot.status}', "
                "only 'interrupted' runs can be resumed."
            )

        if input:
            snapshot.context.update(input)

        # If interrupted after a node, re-evaluate outgoing edges with updated context
        if snapshot.pending_transition_from is not None:
            snapshot.current_node = self._find_next_node(
                snapshot.graph,
                snapshot.pending_transition_from,
                snapshot.context,
            )
            snapshot.pending_transition_from = None

        self._interrupt_signals.discard(run_id)
        snapshot.status = WorkflowStatus.RUNNING
        snapshot.context["__status__"] = WorkflowStatus.RUNNING.value
        snapshot.updated_at = datetime.now(UTC).isoformat()

        return self._execute_loop(
            snapshot,
            interrupt_before=interrupt_before or set(),
            interrupt_after=interrupt_after or set(),
            max_steps=max_steps,
        )

    def get_run(self, run_id: str) -> WorkflowSnapshot | None:
        """Retrieve snapshot of a workflow run."""
        return self._runs.get(run_id)

    def replay(self, run_id: str) -> list[WorkflowStepRecord]:
        """Return the complete execution trace for replay and audit."""
        snapshot = self._runs.get(run_id)
        if not snapshot:
            raise WorkflowExecutionError(f"Workflow run '{run_id}' not found.")
        return list(snapshot.history)

    def _find_next_node(
        self,
        graph: WorkflowGraph,
        current_node_id: str,
        context: dict[str, Any],
    ) -> str | None:
        for edge in graph.edges:
            if edge.from_node == current_node_id:
                if edge.condition is None or edge.condition(context):
                    return edge.to_node
        return None

    def _execute_loop(
        self,
        snapshot: WorkflowSnapshot,
        *,
        interrupt_before: set[str],
        interrupt_after: set[str],
        max_steps: int,
    ) -> dict[str, Any]:
        step_count = len(snapshot.history)

        while snapshot.current_node is not None:
            step_count += 1
            if step_count > max_steps:
                snapshot.status = WorkflowStatus.FAILED
                snapshot.error = (
                    f"Execution exceeded max_steps={max_steps} (possible cycle)."
                )
                snapshot.context["__status__"] = WorkflowStatus.FAILED.value
                snapshot.context["__error__"] = snapshot.error
                raise WorkflowExecutionError(snapshot.error)

            current_id = snapshot.current_node

            # Check for interrupt before executing node
            if (
                current_id in interrupt_before
                or snapshot.run_id in self._interrupt_signals
            ):
                self._interrupt_signals.discard(snapshot.run_id)
                snapshot.status = WorkflowStatus.INTERRUPTED
                snapshot.context["__status__"] = WorkflowStatus.INTERRUPTED.value
                snapshot.context["__current_node__"] = current_id
                snapshot.updated_at = datetime.now(UTC).isoformat()
                return snapshot.context

            node = snapshot.graph.nodes[current_id]
            input_ctx = dict(snapshot.context)

            try:
                output_ctx = node.execute(input_ctx)
            except Exception as exc:
                snapshot.status = WorkflowStatus.FAILED
                snapshot.error = str(exc)
                snapshot.context["__status__"] = WorkflowStatus.FAILED.value
                snapshot.context["__error__"] = str(exc)
                snapshot.updated_at = datetime.now(UTC).isoformat()
                raise WorkflowExecutionError(
                    f"Node '{current_id}' failed: {exc}"
                ) from exc

            step_record = WorkflowStepRecord(
                step_index=len(snapshot.history),
                node_id=current_id,
                input_context=input_ctx,
                output_context=dict(output_ctx),
                timestamp=datetime.now(UTC).isoformat(),
            )
            snapshot.history.append(step_record)
            snapshot.context = output_ctx

            next_id = self._find_next_node(snapshot.graph, current_id, output_ctx)
            snapshot.current_node = next_id
            snapshot.updated_at = datetime.now(UTC).isoformat()

            # Check for interrupt after node execution
            explicit_interrupt = bool(output_ctx.get("__interrupt__"))
            if explicit_interrupt or (current_id in interrupt_after):
                output_ctx.pop("__interrupt__", None)
                snapshot.pending_transition_from = current_id
                snapshot.status = WorkflowStatus.INTERRUPTED
                snapshot.context["__status__"] = WorkflowStatus.INTERRUPTED.value
                snapshot.context["__current_node__"] = next_id
                snapshot.updated_at = datetime.now(UTC).isoformat()
                return snapshot.context

        # Workflow reached terminal node
        snapshot.status = WorkflowStatus.COMPLETED
        snapshot.context["__status__"] = WorkflowStatus.COMPLETED.value
        snapshot.context.pop("__current_node__", None)
        snapshot.updated_at = datetime.now(UTC).isoformat()
        return snapshot.context
