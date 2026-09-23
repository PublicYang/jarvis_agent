"""Tests for Phase 14 MCP Integration."""

from __future__ import annotations

import sys
from typing import Any

import pytest
from integrations.mcp import (
    InMemoryMCPClient,
    MCPError,
    StdioMCPClient,
    register_mcp_client,
)
from planner.base import DecisionType, PlannerOutput
from runtime.engine import RuntimeEngine
from runtime.models import Message, MessageRole, State
from tools.base import ToolCall, ToolDefinition
from tools.executor import ToolExecutor
from tools.registry import InMemoryToolRegistry

from workflow import FunctionNode, WorkflowEngine, WorkflowGraph


def test_in_memory_mcp_client_tools_and_resources() -> None:
    client = InMemoryMCPClient()

    calc_def = ToolDefinition(
        name="calculator",
        description="Add two numbers",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
    )

    def calc_handler(args: dict[str, Any]) -> str:
        return str(args["a"] + args["b"])

    client.register_tool(calc_def, calc_handler)
    client.register_resource(
        uri="docs://intro",
        name="Introduction",
        content="Welcome to Jarvis Agent",
    )

    # Test tools discovery
    tools = client.discover_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "calculator"
    assert tools[0]["description"] == "Add two numbers"

    # Test tool calling
    obs = client.call_tool("calculator", {"a": 10, "b": 25})
    assert obs.success is True
    assert obs.content == "35"

    # Test calling unknown tool
    unknown_obs = client.call_tool("unknown", {})
    assert unknown_obs.success is False
    assert "not found" in (unknown_obs.error or "")

    # Test resources
    resources = client.list_resources()
    assert len(resources) == 1
    assert resources[0]["uri"] == "docs://intro"

    content = client.read_resource("docs://intro")
    assert content == "Welcome to Jarvis Agent"

    with pytest.raises(MCPError):
        client.read_resource("docs://missing")


def test_mcp_tool_adapter_and_registry_registration() -> None:
    client = InMemoryMCPClient()
    tool_def = ToolDefinition(
        name="get_weather",
        description="Get weather for city",
        parameters={"type": "object", "properties": {"city": {"type": "string"}}},
    )
    client.register_tool(tool_def, lambda args: f"Sunny in {args.get('city')}")

    registry = InMemoryToolRegistry()
    registered = register_mcp_client(registry, client)
    assert registered == ["get_weather"]

    # Verify tool metadata
    tool = registry.get("get_weather")
    assert tool.definition["name"] == "get_weather"

    # Verify execution via ToolExecutor
    executor = ToolExecutor(registry)
    call = ToolCall(tool_name="get_weather", arguments={"city": "Shenzhen"})
    finished, obs = executor.execute(call)
    assert obs.success is True
    assert obs.content == "Sunny in Shenzhen"
    assert finished.status.value == "completed"


def test_mcp_dual_engine_synchronous_support() -> None:
    """Verify both ReAct engine and Workflow engine can seamlessly call MCP tools."""
    client = InMemoryMCPClient()
    client.register_tool(
        ToolDefinition(
            name="multiply",
            description="Multiply two numbers",
            parameters={"type": "object"},
        ),
        lambda args: str(args["x"] * args["y"]),
    )

    registry = InMemoryToolRegistry()
    register_mcp_client(registry, client)
    executor = ToolExecutor(registry)

    # 1. Test ReAct Engine Loop with MCP tool
    class MockReActPlanner:
        def __init__(self) -> None:
            self.turns = 0

        def plan(self, state: State) -> PlannerOutput:
            self.turns += 1
            if self.turns == 1:
                return PlannerOutput(
                    decision_type=DecisionType.TOOL_CALL,
                    tool_call=ToolCall(
                        tool_name="multiply",
                        arguments={"x": 6, "y": 7},
                    ),
                )
            return PlannerOutput(
                decision_type=DecisionType.REPLY,
                content=f"Result is {state.observations[-1].content}",
            )

    engine = RuntimeEngine(
        planner=MockReActPlanner(),
        executor=executor,
        max_steps=5,
    )
    react_state = engine.run(Message(role=MessageRole.USER, content="calc 6*7"))
    assert react_state.status.value == "completed"
    assert any("Result is 42" in msg.content for msg in react_state.messages)

    # 2. Test Workflow Engine with MCP tool
    def workflow_mcp_step(context: dict[str, Any]) -> dict[str, Any]:
        call = ToolCall(tool_name="multiply", arguments={"x": 3, "y": 9})
        _, obs = executor.execute(call)
        return {**context, "wf_result": obs.content}

    wf_graph = WorkflowGraph()
    wf_graph.add_node(FunctionNode("mcp_node", workflow_mcp_step))
    wf_graph.set_entry_point("mcp_node")

    wf_engine = WorkflowEngine()
    wf_context = wf_engine.run(wf_graph, {})
    assert wf_context["wf_result"] == "27"


def test_stdio_mcp_client_subprocess() -> None:
    """Quality Gate: StdioMCPClient communicates via JSON-RPC 2.0."""
    script = (
        "import sys, json\n"
        "for line in sys.stdin:\n"
        "    req = json.loads(line.strip())\n"
        "    method = req.get('method')\n"
        "    if method == 'tools/list':\n"
        "        t = [{'name': 'echo_mcp', 'description': 'Echoes input'}]\n"
        "        res = {'tools': t}\n"
        "    elif method == 'tools/call':\n"
        "        args = req['params']['arguments']\n"
        "        txt = 'echo: ' + args.get('msg', '')\n"
        "        res = {'content': [{'type': 'text', 'text': txt}]}\n"
        "    else:\n"
        "        res = {}\n"
        "    out = json.dumps({'jsonrpc': '2.0', 'id': req['id'], 'result': res})\n"
        "    sys.stdout.write(out + '\\n')\n"
        "    sys.stdout.flush()\n"
    )

    client = StdioMCPClient([sys.executable, "-c", script])
    try:
        tools = client.discover_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "echo_mcp"

        obs = client.call_tool("echo_mcp", {"msg": "hello mcp"})
        assert obs.success is True
        assert obs.content == "echo: hello mcp"
    finally:
        client.close()
