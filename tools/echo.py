"""Example echo tool (Phase6)."""

from __future__ import annotations

from typing import Any

from tools.base import Observation, ToolDefinition


class EchoTool:
    """Returns the provided text unchanged."""

    @property
    def definition(self) -> ToolDefinition:
        return {
            "name": "echo",
            "description": "Echo the input text.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        }

    def execute(self, arguments: dict[str, Any]) -> Observation:
        text = arguments.get("text", "")
        if not isinstance(text, str):
            return Observation(
                tool_call_id="",
                success=False,
                content="",
                error="argument 'text' must be a string",
            )
        return Observation(tool_call_id="", success=True, content=text)

    async def aexecute(self, arguments: dict[str, Any]) -> Observation:
        return self.execute(arguments)
