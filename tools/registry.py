"""In-memory Tool registry (Phase6)."""

from __future__ import annotations

from typing import Protocol

from tools.base import Observation, Tool, ToolCall, ToolDefinition


class ToolRegistry(Protocol):
    def register(self, tool: Tool) -> None: ...

    def get(self, name: str) -> Tool: ...

    def list_tools(self) -> list[ToolDefinition]: ...

    def execute(self, tool_call: ToolCall) -> Observation: ...


class InMemoryToolRegistry:
    """Name-keyed tool registry used by the Runtime loop."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = tool.definition["name"]
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list_tools(self) -> list[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    def execute(self, tool_call: ToolCall) -> Observation:
        try:
            tool = self.get(tool_call.tool_name)
        except KeyError:
            return Observation(
                tool_call_id=tool_call.id,
                success=False,
                content="",
                error=f"unknown tool: {tool_call.tool_name}",
            )
        observation = tool.execute(tool_call.arguments)
        return observation.model_copy(update={"tool_call_id": tool_call.id})
