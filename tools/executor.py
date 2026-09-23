"""Tool execution adapter with observability (Phase6 & Phase15)."""

from __future__ import annotations

import time

from infra.telemetry import get_logger, get_metrics, get_tracer

from tools.base import Observation, ToolCall, ToolCallStatus
from tools.registry import ToolRegistry

_logger = get_logger("tool_executor")
_tracer = get_tracer()
_metrics = get_metrics()


class ToolExecutor:
    """Run a ToolCall through the registry and record status transitions."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, tool_call: ToolCall) -> tuple[ToolCall, Observation]:
        running = tool_call.model_copy(update={"status": ToolCallStatus.RUNNING})
        tool_name = tool_call.tool_name
        _logger.debug(
            f"Executing tool {tool_name}", tool=tool_name, call_id=tool_call.id
        )

        start = time.monotonic()
        with _tracer.start_span(
            "tool_execution",
            tags={"tool": tool_name, "call_id": tool_call.id},
        ):
            observation = self._registry.execute(running)

        duration = time.monotonic() - start
        _metrics.increment("tool_calls_total", tags={"tool": tool_name})
        _metrics.observe(
            "tool_call_duration_seconds", duration, tags={"tool": tool_name}
        )

        if not observation.success:
            _metrics.increment("tool_errors_total", tags={"tool": tool_name})
            _logger.warning(
                f"Tool {tool_name} failed: {observation.error}",
                tool=tool_name,
                call_id=tool_call.id,
            )

        final_status = (
            ToolCallStatus.COMPLETED if observation.success else ToolCallStatus.FAILED
        )
        finished = running.model_copy(update={"status": final_status})
        return finished, observation
