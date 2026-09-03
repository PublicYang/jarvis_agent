"""Tool execution adapter (Phase6)."""

from __future__ import annotations

from tools.base import Observation, ToolCall, ToolCallStatus
from tools.registry import ToolRegistry


class ToolExecutor:
    """Run a ToolCall through the registry and record status transitions."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, tool_call: ToolCall) -> tuple[ToolCall, Observation]:
        running = tool_call.model_copy(update={"status": ToolCallStatus.RUNNING})
        observation = self._registry.execute(running)
        final_status = (
            ToolCallStatus.COMPLETED if observation.success else ToolCallStatus.FAILED
        )
        finished = running.model_copy(update={"status": final_status})
        return finished, observation
