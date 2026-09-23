"""Tool adapter and registry integration for MCP tools (Phase14)."""

from __future__ import annotations

from typing import Any

from tools.base import Observation, Tool, ToolDefinition
from tools.registry import ToolRegistry

from integrations.mcp.client import MCPClient


class MCPToolAdapter(Tool):
    """Adapts an MCP-exposed tool into the internal Tool protocol."""

    def __init__(self, client: MCPClient, tool_definition: ToolDefinition) -> None:
        self._client = client
        self._definition = tool_definition

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    def execute(self, arguments: dict[str, Any]) -> Observation:
        return self._client.call_tool(self._definition["name"], arguments)


def register_mcp_client(registry: ToolRegistry, client: MCPClient) -> list[str]:
    """Discover and register all tools from an MCPClient into a ToolRegistry.

    Returns the list of newly registered tool names.
    """
    discovered_tools = client.discover_tools()
    registered_names: list[str] = []
    for defn in discovered_tools:
        adapter = MCPToolAdapter(client, defn)
        registry.register(adapter)
        registered_names.append(defn["name"])
    return registered_names
