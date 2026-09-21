"""Tests for ParallelNode, ParallelToolNode, and merge strategies (Phase13)."""

from __future__ import annotations

import time
from typing import Any

import pytest
from tools.base import ToolCall
from tools.echo import EchoTool
from tools.executor import ToolExecutor
from tools.registry import InMemoryToolRegistry

from workflow import (
    FunctionNode,
    ParallelExecutionError,
    ParallelNode,
    ParallelToolNode,
    WorkflowEngine,
    WorkflowGraph,
    WorkflowStatus,
    namespaced_merge_strategy,
)


def test_parallel_node_concurrent_speedup() -> None:
    """Verify that sub-nodes run concurrently rather than sequentially."""

    def make_sleep_step(key: str, delay: float = 0.15):
        def _step(ctx: dict[str, Any]) -> dict[str, Any]:
            time.sleep(delay)
            return {**ctx, key: True}

        return _step

    nodes = [
        FunctionNode("task_1", make_sleep_step("t1")),
        FunctionNode("task_2", make_sleep_step("t2")),
        FunctionNode("task_3", make_sleep_step("t3")),
    ]
    parallel = ParallelNode("parallel_tasks", nodes, max_workers=3)

    start = time.monotonic()
    result = parallel.execute({"base": 1})
    elapsed = time.monotonic() - start

    assert result["base"] == 1
    assert result["t1"] is True
    assert result["t2"] is True
    assert result["t3"] is True
    # Sequential would take >= 0.45s, parallel takes ~0.15-0.30s
    assert elapsed < 0.40


def test_parallel_node_race_condition_free() -> None:
    """Quality Gate: High concurrency execution is free of race conditions."""

    def make_calc_step(idx: int):
        def _step(ctx: dict[str, Any]) -> dict[str, Any]:
            return {**ctx, f"val_{idx}": idx * 10}

        return _step

    task_count = 20
    nodes = [FunctionNode(f"node_{i}", make_calc_step(i)) for i in range(task_count)]
    parallel = ParallelNode("mass_compute", nodes, max_workers=8)

    result = parallel.execute({"initial": "ok"})
    assert result["initial"] == "ok"
    for i in range(task_count):
        assert result[f"val_{i}"] == i * 10


def test_parallel_node_namespaced_merge() -> None:
    node1 = FunctionNode("crawler_a", lambda ctx: {**ctx, "score": 85, "data": "A"})
    node2 = FunctionNode("crawler_b", lambda ctx: {**ctx, "score": 92, "data": "B"})

    parallel = ParallelNode(
        "gather",
        [node1, node2],
        merge_strategy=namespaced_merge_strategy("crawlers"),
    )
    result = parallel.execute({"job": "audit"})

    assert result["job"] == "audit"
    assert "crawlers" in result
    assert result["crawlers"]["crawler_a"]["score"] == 85
    assert result["crawlers"]["crawler_b"]["score"] == 92


def test_parallel_node_failure_raises() -> None:
    def good_step(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "ok": True}

    def bad_step(_ctx: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("Network timeout in branch")

    nodes = [
        FunctionNode("good", good_step),
        FunctionNode("bad", bad_step),
    ]
    parallel = ParallelNode("mixed", nodes, max_workers=2)

    with pytest.raises(ParallelExecutionError) as exc_info:
        parallel.execute({})

    assert "bad" in exc_info.value.errors
    assert "Network timeout in branch" in str(exc_info.value)


def test_parallel_tool_node_execution() -> None:
    """Quality Gate: Parallel Tool execution collects Observations safely."""
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    executor = ToolExecutor(registry)

    calls = [
        ToolCall(tool_name="echo", arguments={"text": "first"}),
        ToolCall(tool_name="echo", arguments={"text": "second"}),
        ToolCall(tool_name="echo", arguments={"text": "third"}),
    ]

    tool_node = ParallelToolNode("parallel_echo", executor, calls, max_workers=3)
    result = tool_node.execute({"run_id": "r1"})

    assert "observations" in result
    observations = result["observations"]
    assert len(observations) == 3
    assert all(obs.success for obs in observations)
    assert [obs.content for obs in observations] == ["first", "second", "third"]


def test_parallel_in_workflow_graph_integration() -> None:
    """Test integrating ParallelNode into a complete WorkflowGraph."""
    graph = WorkflowGraph()

    def prepare(ctx: dict[str, Any]) -> dict[str, Any]:
        return {**ctx, "target": "dataset_01"}

    sub1 = FunctionNode("fetch_sql", lambda ctx: {**ctx, "sql": "SELECT 1"})
    sub2 = FunctionNode("fetch_api", lambda ctx: {**ctx, "api": "HTTP 200"})
    parallel_step = ParallelNode("parallel_fetch", [sub1, sub2])

    def summarize(ctx: dict[str, Any]) -> dict[str, Any]:
        return {
            **ctx,
            "report": f"Done {ctx['target']} with {ctx['sql']} and {ctx['api']}",
        }

    graph.add_node(FunctionNode("prep", prepare))
    graph.add_node(parallel_step)
    graph.add_node(FunctionNode("summary", summarize))

    graph.add_edge("prep", "parallel_fetch")
    graph.add_edge("parallel_fetch", "summary")
    graph.set_entry_point("prep")

    engine = WorkflowEngine()
    final = engine.run(graph, {}, run_id="parallel_wf")

    assert final["__status__"] == WorkflowStatus.COMPLETED.value
    assert final["report"] == "Done dataset_01 with SELECT 1 and HTTP 200"

    # Verify execution history recorded each step including ParallelNode
    trace = engine.replay("parallel_wf")
    assert len(trace) == 3
    assert [t.node_id for t in trace] == ["prep", "parallel_fetch", "summary"]
