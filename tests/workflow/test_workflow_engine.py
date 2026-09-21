"""Tests for WorkflowEngine with interrupt, resume, and replay (Phase12)."""

from __future__ import annotations

from typing import Any

import pytest

from workflow import (
    FunctionNode,
    WorkflowEngine,
    WorkflowExecutionError,
    WorkflowGraph,
    WorkflowStatus,
)


def _create_sample_graph() -> WorkflowGraph:
    graph = WorkflowGraph()

    def step_a(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "a": 1, "log": [*ctx.get("log", []), "step_a"]}

    def step_b(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "b": 2, "log": [*ctx.get("log", []), "step_b"]}

    def step_c(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "c": 3, "log": [*ctx.get("log", []), "step_c"]}

    graph.add_node(FunctionNode("node_a", step_a))
    graph.add_node(FunctionNode("node_b", step_b))
    graph.add_node(FunctionNode("node_c", step_c))

    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", "node_c")
    graph.set_entry_point("node_a")
    return graph


def test_engine_run_linear_completion() -> None:
    engine = WorkflowEngine()
    graph = _create_sample_graph()

    result = engine.run(graph, {"initial": True}, run_id="run_101")
    assert result["__status__"] == WorkflowStatus.COMPLETED.value
    assert result["__run_id__"] == "run_101"
    assert result["log"] == ["step_a", "step_b", "step_c"]
    assert result["a"] == 1 and result["b"] == 2 and result["c"] == 3

    snapshot = engine.get_run("run_101")
    assert snapshot is not None
    assert snapshot.status == WorkflowStatus.COMPLETED


def test_engine_interrupt_before() -> None:
    engine = WorkflowEngine()
    graph = _create_sample_graph()

    result = engine.run(
        graph,
        {"log": []},
        run_id="run_102",
        interrupt_before={"node_b"},
    )
    assert result["__status__"] == WorkflowStatus.INTERRUPTED.value
    assert result["__current_node__"] == "node_b"
    assert result["log"] == ["step_a"]

    snapshot = engine.get_run("run_102")
    assert snapshot is not None
    assert snapshot.status == WorkflowStatus.INTERRUPTED
    assert snapshot.current_node == "node_b"


def test_engine_interrupt_after() -> None:
    engine = WorkflowEngine()
    graph = _create_sample_graph()

    result = engine.run(
        graph,
        {"log": []},
        run_id="run_103",
        interrupt_after={"node_b"},
    )
    assert result["__status__"] == WorkflowStatus.INTERRUPTED.value
    assert result["__current_node__"] == "node_c"
    assert result["log"] == ["step_a", "step_b"]

    snapshot = engine.get_run("run_103")
    assert snapshot is not None
    assert snapshot.status == WorkflowStatus.INTERRUPTED
    assert snapshot.current_node == "node_c"


def test_engine_resume_with_human_input() -> None:
    engine = WorkflowEngine()
    graph = _create_sample_graph()

    # Run with interrupt before node_b
    paused = engine.run(
        graph,
        {"log": []},
        run_id="run_104",
        interrupt_before={"node_b"},
    )
    assert paused["__status__"] == WorkflowStatus.INTERRUPTED.value

    # Resume with injected human feedback
    final = engine.resume(
        "run_104",
        input={"human_reviewed": True},
    )
    assert final["__status__"] == WorkflowStatus.COMPLETED.value
    assert final["human_reviewed"] is True
    assert final["log"] == ["step_a", "step_b", "step_c"]


def test_engine_explicit_interrupt_and_conditional_approval() -> None:
    """Human-in-the-loop: sensitive node triggers interrupt for approval."""
    graph = WorkflowGraph()

    def draft_order(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            **ctx,
            "order_id": "ORD-999",
            "__interrupt__": True,
            "prompt": "Please approve payment of $100",
        }

    def process_payment(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "paid": True}

    def cancel_order(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "cancelled": True}

    graph.add_node(FunctionNode("draft", draft_order))
    graph.add_node(FunctionNode("pay", process_payment))
    graph.add_node(FunctionNode("abort", cancel_order))

    graph.add_edge("draft", "pay", condition=lambda ctx: bool(ctx.get("approved")))
    graph.add_edge(
        "draft", "abort", condition=lambda ctx: not bool(ctx.get("approved"))
    )
    graph.set_entry_point("draft")

    engine = WorkflowEngine()
    res = engine.run(graph, {}, run_id="order_run")
    assert res["__status__"] == WorkflowStatus.INTERRUPTED.value
    assert res["order_id"] == "ORD-999"

    # Human approves
    res_approved = engine.resume("order_run", {"approved": True})
    assert res_approved["__status__"] == WorkflowStatus.COMPLETED.value
    assert res_approved["paid"] is True


def test_engine_resume_invalid_run_raises() -> None:
    engine = WorkflowEngine()

    with pytest.raises(WorkflowExecutionError, match="not found"):
        engine.resume("non_existent_id")

    graph = _create_sample_graph()
    engine.run(graph, {}, run_id="done_run")
    with pytest.raises(WorkflowExecutionError, match="only 'interrupted' runs"):
        engine.resume("done_run")


def test_engine_replay_trace() -> None:
    """Quality Gate test: Workflow history is recorded and replayable."""
    engine = WorkflowEngine()
    graph = _create_sample_graph()

    engine.run(graph, {"init": 0}, run_id="replay_test")
    trace = engine.replay("replay_test")

    assert len(trace) == 3
    assert trace[0].node_id == "node_a"
    assert trace[0].step_index == 0
    assert trace[0].output_context["a"] == 1

    assert trace[1].node_id == "node_b"
    assert trace[1].step_index == 1
    assert trace[1].output_context["b"] == 2

    assert trace[2].node_id == "node_c"
    assert trace[2].step_index == 2
    assert trace[2].output_context["c"] == 3


def test_engine_node_failure() -> None:
    graph = WorkflowGraph()

    def ok_step(ctx: dict[str, Any]) -> dict[str, Any]:
        return ctx

    def fail_step(_ctx: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("Database disconnected")

    graph.add_node(FunctionNode("ok", ok_step))
    graph.add_node(FunctionNode("boom", fail_step))
    graph.add_edge("ok", "boom")
    graph.set_entry_point("ok")

    engine = WorkflowEngine()
    with pytest.raises(WorkflowExecutionError, match="Database disconnected"):
        engine.run(graph, {}, run_id="fail_run")

    snapshot = engine.get_run("fail_run")
    assert snapshot is not None
    assert snapshot.status == WorkflowStatus.FAILED
    assert "Database disconnected" in (snapshot.error or "")
