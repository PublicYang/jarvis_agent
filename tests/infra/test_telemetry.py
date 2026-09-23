"""Tests for Phase 15 telemetry: logging, tracing, and metrics."""

from __future__ import annotations

import time

from infra.telemetry import (
    MetricsRegistry,
    Tracer,
    bind_context,
    clear_context,
    get_context,
    get_logger,
)


def test_structured_logging_context_binding() -> None:
    clear_context()
    bind_context(run_id="run-123", session_id="sess-abc")
    ctx = get_context()
    assert ctx["run_id"] == "run-123"
    assert ctx["session_id"] == "sess-abc"

    logger = get_logger("test_logger")
    # Formatting output should contain context fields
    line = logger._format_msg("INFO", "test execution", {"step": 1})
    assert "run_id=run-123" in line
    assert "session_id=sess-abc" in line
    assert "step=1" in line
    assert "test execution" in line

    clear_context()
    assert get_context() == {}


def test_tracer_span_nesting_and_lifecycle() -> None:
    tracer = Tracer()

    with tracer.start_span("root_operation", tags={"env": "prod"}):
        time.sleep(0.01)
        with tracer.start_span("child_operation", tags={"sub": "1"}):
            time.sleep(0.01)

    spans = tracer.get_spans()
    assert len(spans) == 2

    # Spans are recorded in completion order: child finishes before root
    child_rec = next(s for s in spans if s.name == "child_operation")
    root_rec = next(s for s in spans if s.name == "root_operation")

    assert child_rec.trace_id == root_rec.trace_id
    assert child_rec.parent_span_id == root_rec.span_id
    assert child_rec.tags["sub"] == "1"
    assert root_rec.tags["env"] == "prod"
    assert child_rec.duration_seconds > 0.005
    assert root_rec.duration_seconds > child_rec.duration_seconds


def test_tracer_captures_errors() -> None:
    tracer = Tracer()
    try:
        with tracer.start_span("failing_step"):
            raise RuntimeError("Operation aborted")
    except RuntimeError:
        pass

    spans = tracer.get_spans()
    assert len(spans) == 1
    assert spans[0].error == "Operation aborted"
    assert spans[0].tags.get("error") is True


def test_metrics_registry_recording_and_snapshot() -> None:
    registry = MetricsRegistry()

    # Counter
    registry.increment("llm_calls_total", tags={"model": "gpt-4o-mini"})
    registry.increment("llm_calls_total", 2.0, tags={"model": "gpt-4o-mini"})
    registry.increment("tool_errors_total")

    # Gauge
    registry.gauge("active_tasks", 3.0)

    # Observation
    registry.observe("turn_latency_seconds", 0.15)
    registry.observe("turn_latency_seconds", 0.25)

    snap = registry.snapshot()
    counters = snap["counters"]
    gauges = snap["gauges"]
    observations = snap["observations"]

    assert counters["llm_calls_total{model=gpt-4o-mini}"] == 3.0
    assert counters["tool_errors_total"] == 1.0
    assert gauges["active_tasks"] == 3.0

    obs = observations["turn_latency_seconds"]
    assert obs["count"] == 2
    assert abs(obs["total"] - 0.40) < 1e-4
    assert abs(obs["avg"] - 0.20) < 1e-4


def test_engine_critical_path_tracing_and_metrics() -> None:
    """Quality Gate: Critical paths (ReAct & Workflow) generate traces and metrics."""
    from infra.telemetry import get_metrics, get_tracer
    from planner.base import DecisionType, PlannerOutput
    from runtime.engine import RuntimeEngine
    from runtime.models import Message, MessageRole, State
    from tools.base import ToolCall
    from tools.echo import EchoTool
    from tools.executor import ToolExecutor
    from tools.registry import InMemoryToolRegistry

    from workflow import FunctionNode, WorkflowEngine, WorkflowGraph

    tracer = get_tracer()
    tracer.clear()
    metrics = get_metrics()
    metrics.clear()

    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    executor = ToolExecutor(registry)

    # 1. ReAct critical path trace & metrics
    class EchoPlanner:
        def __init__(self):
            self.turn = 0

        def plan(self, state: State) -> PlannerOutput:
            self.turn += 1
            if self.turn == 1:
                return PlannerOutput(
                    decision_type=DecisionType.TOOL_CALL,
                    tool_call=ToolCall(tool_name="echo", arguments={"text": "hello"}),
                )
            return PlannerOutput(
                decision_type=DecisionType.REPLY,
                content="done echo",
            )

    react_engine = RuntimeEngine(planner=EchoPlanner(), executor=executor)
    react_engine.run(Message(role=MessageRole.USER, content="test react"))

    # 2. Workflow critical path trace & metrics
    wf_graph = WorkflowGraph()
    wf_graph.add_node(FunctionNode("step_a", lambda ctx: {**ctx, "val": "a"}))
    wf_graph.set_entry_point("step_a")
    wf_engine = WorkflowEngine()
    wf_engine.run(wf_graph, {})

    spans = tracer.get_spans()
    span_names = {s.name for s in spans}

    # Verify critical path spans exist
    assert "react_engine_run" in span_names
    assert "react_plan_step" in span_names
    assert "tool_execution" in span_names
    assert "workflow_engine_run" in span_names
    assert "workflow_node_execute" in span_names

    # Verify metrics recorded
    snap = metrics.snapshot()
    counters = snap["counters"]
    assert counters.get("engine_runs_total{engine=react}", 0) >= 1
    assert counters.get("engine_runs_total{engine=workflow}", 0) >= 1
    assert counters.get("tool_calls_total{tool=echo}", 0) >= 1
    assert counters.get("workflow_node_executions_total{node=step_a}", 0) >= 1
