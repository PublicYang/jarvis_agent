"""Unit tests for Workflow Foundation (Phase11)."""

from __future__ import annotations

from typing import Any

import pytest

from workflow import (
    FunctionNode,
    NodeExecutionError,
    WorkflowGraph,
    WorkflowNode,
    WorkflowValidationError,
)


def test_workflow_node_protocol() -> None:
    node = FunctionNode("test_node", lambda ctx: ctx)
    assert isinstance(node, WorkflowNode)
    assert node.id == "test_node"
    assert repr(node) == "FunctionNode(id='test_node')"


def test_function_node_execution() -> None:
    def step(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "count": ctx.get("count", 0) + 1}

    node = FunctionNode("counter", step)
    res = node.execute({"initial": True})
    assert res == {"initial": True, "count": 1}


def test_function_node_execution_error() -> None:
    def failing_step(_ctx: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("Something went wrong")

    node = FunctionNode("bad_node", failing_step)
    with pytest.raises(NodeExecutionError) as exc_info:
        node.execute({})
    assert "bad_node" in str(exc_info.value)
    assert "Something went wrong" in str(exc_info.value)
    assert exc_info.value.node_id == "bad_node"


def test_graph_add_duplicate_node_raises() -> None:
    graph = WorkflowGraph()
    graph.add_node(FunctionNode("n1", lambda ctx: ctx))
    with pytest.raises(WorkflowValidationError, match="already exists"):
        graph.add_node(FunctionNode("n1", lambda ctx: ctx))


def test_graph_validation_missing_entry_point() -> None:
    graph = WorkflowGraph()
    graph.add_node(FunctionNode("n1", lambda ctx: ctx))
    with pytest.raises(WorkflowValidationError, match="no entry_point"):
        graph.validate()


def test_graph_validation_entry_point_not_in_nodes() -> None:
    graph = WorkflowGraph()
    graph.add_node(FunctionNode("n1", lambda ctx: ctx))
    graph.set_entry_point("non_existent")
    with pytest.raises(
        WorkflowValidationError, match="Entry point 'non_existent' not found"
    ):
        graph.validate()


def test_graph_validation_edge_unknown_source() -> None:
    graph = WorkflowGraph()
    graph.add_node(FunctionNode("n1", lambda ctx: ctx))
    graph.set_entry_point("n1")
    graph.add_edge("unknown_source", "n1")
    with pytest.raises(WorkflowValidationError, match="Edge source 'unknown_source'"):
        graph.validate()


def test_graph_validation_edge_unknown_target() -> None:
    graph = WorkflowGraph()
    graph.add_node(FunctionNode("n1", lambda ctx: ctx))
    graph.set_entry_point("n1")
    graph.add_edge("n1", "unknown_target")
    with pytest.raises(WorkflowValidationError, match="Edge target 'unknown_target'"):
        graph.validate()


def test_linear_workflow_execution() -> None:
    """Quality Gate test: Linear Workflow executes NodeA -> NodeB -> NodeC."""
    graph = WorkflowGraph()

    def step1(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "raw_data": "  jarvis workflow  "}

    def step2(ctx: dict[str, Any]) -> dict[str, Any]:
        raw = ctx["raw_data"]
        return {**ctx, "cleaned_data": raw.strip().upper()}

    def step3(ctx: dict[str, Any]) -> dict[str, Any]:
        cleaned = ctx["cleaned_data"]
        return {**ctx, "summary": f"Result: {cleaned} (len={len(cleaned)})"}

    graph.add_node(FunctionNode("fetch", step1))
    graph.add_node(FunctionNode("clean", step2))
    graph.add_node(FunctionNode("summarize", step3))

    graph.add_edge("fetch", "clean")
    graph.add_edge("clean", "summarize")
    graph.set_entry_point("fetch")

    final_context = graph.run({"user_id": "u123"})

    assert final_context["user_id"] == "u123"
    assert final_context["raw_data"] == "  jarvis workflow  "
    assert final_context["cleaned_data"] == "JARVIS WORKFLOW"
    assert final_context["summary"] == "Result: JARVIS WORKFLOW (len=15)"


def test_conditional_edge_workflow() -> None:
    graph = WorkflowGraph()

    def check_input(ctx: dict[str, Any]) -> dict[str, Any]:
        return ctx

    def path_positive(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "branch": "positive"}

    def path_negative(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "branch": "negative"}

    graph.add_node(FunctionNode("check", check_input))
    graph.add_node(FunctionNode("pos", path_positive))
    graph.add_node(FunctionNode("neg", path_negative))

    graph.add_edge("check", "pos", condition=lambda ctx: ctx.get("value", 0) > 0)
    graph.add_edge("check", "neg", condition=lambda ctx: ctx.get("value", 0) <= 0)
    graph.set_entry_point("check")

    res_pos = graph.run({"value": 10})
    assert res_pos["branch"] == "positive"

    res_neg = graph.run({"value": -5})
    assert res_neg["branch"] == "negative"


def test_graph_cycle_detection_exceeds_max_steps() -> None:
    graph = WorkflowGraph()
    graph.add_node(FunctionNode("loop_a", lambda ctx: ctx))
    graph.add_node(FunctionNode("loop_b", lambda ctx: ctx))

    graph.add_edge("loop_a", "loop_b")
    graph.add_edge("loop_b", "loop_a")
    graph.set_entry_point("loop_a")

    with pytest.raises(RuntimeError, match="exceeded max_steps=5"):
        graph.run({}, max_steps=5)
