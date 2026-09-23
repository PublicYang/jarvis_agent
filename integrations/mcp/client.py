"""MCP client protocol and implementations (Phase14)."""

from __future__ import annotations

import json
import subprocess
import uuid
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from tools.base import Observation, ToolDefinition


class MCPError(Exception):
    """Raised when an MCP protocol or server error occurs."""


@runtime_checkable
class MCPClient(Protocol):
    """Protocol for Model Context Protocol (MCP) clients."""

    def discover_tools(self) -> list[ToolDefinition]:
        """Discover tools exposed by the MCP server."""
        ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Observation:
        """Invoke a tool exposed by the MCP server."""
        ...

    def list_resources(self) -> list[dict[str, Any]]:
        """List resources available from the MCP server."""
        ...

    def read_resource(self, uri: str) -> str:
        """Read a resource from the MCP server by URI."""
        ...


class InMemoryMCPClient:
    """In-memory MCP client for testing, mocking, and in-process tools."""

    def __init__(self) -> None:
        self._tools: dict[
            str, tuple[ToolDefinition, Callable[[dict[str, Any]], Any]]
        ] = {}
        self._resources: dict[str, dict[str, Any]] = {}

    def register_tool(
        self,
        definition: ToolDefinition,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register an in-memory tool definition and handler."""
        self._tools[definition["name"]] = (definition, handler)

    def register_resource(
        self,
        uri: str,
        name: str,
        content: str,
        mime_type: str = "text/plain",
    ) -> None:
        """Register an in-memory resource."""
        self._resources[uri] = {
            "uri": uri,
            "name": name,
            "mimeType": mime_type,
            "content": content,
        }

    def discover_tools(self) -> list[ToolDefinition]:
        return [defn for defn, _ in self._tools.values()]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Observation:
        tool_entry = self._tools.get(name)
        if not tool_entry:
            return Observation(
                tool_call_id=str(uuid.uuid4()),
                success=False,
                content="",
                error=f"MCP tool not found: {name}",
            )

        _defn, handler = tool_entry
        try:
            result = handler(arguments)
            return Observation(
                tool_call_id=str(uuid.uuid4()),
                success=True,
                content=result,
            )
        except Exception as exc:
            return Observation(
                tool_call_id=str(uuid.uuid4()),
                success=False,
                content="",
                error=str(exc),
            )

    def list_resources(self) -> list[dict[str, Any]]:
        return [
            {"uri": r["uri"], "name": r["name"], "mimeType": r["mimeType"]}
            for r in self._resources.values()
        ]

    def read_resource(self, uri: str) -> str:
        res = self._resources.get(uri)
        if not res:
            raise MCPError(f"Resource not found: {uri}")
        return str(res["content"])


class StdioMCPClient:
    """Subprocess stdio-based JSON-RPC 2.0 MCP Client."""

    def __init__(
        self,
        command: list[str],
        *,
        timeout: float = 30.0,
    ) -> None:
        self.command = command
        self.timeout = timeout
        self._process: subprocess.Popen[str] | None = None
        self._req_id = 0

    def start(self) -> None:
        """Start the MCP server subprocess."""
        if self._process is None or self._process.poll() is not None:
            self._process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

    def close(self) -> None:
        """Terminate the MCP server subprocess."""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=2.0)
            except Exception:
                self._process.kill()
            finally:
                self._process = None

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def send_request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a JSON-RPC 2.0 request and wait for the response."""
        self.start()
        assert self._process is not None
        assert self._process.stdin is not None
        assert self._process.stdout is not None

        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        raw_msg = json.dumps(payload) + "\n"
        try:
            self._process.stdin.write(raw_msg)
            self._process.stdin.flush()
        except OSError as exc:
            raise MCPError(f"Failed to send request to MCP process: {exc}") from exc

        line = self._process.stdout.readline()
        if not line:
            stderr_out = ""
            if self._process.stderr:
                stderr_out = self._process.stderr.read()
            raise MCPError(
                f"MCP server closed stdout unexpectedly. Stderr: {stderr_out}"
            )

        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MCPError(f"Invalid JSON from MCP server: {line!r}") from exc

        if "error" in response and response["error"] is not None:
            err = response["error"]
            code = err.get("code", "UNKNOWN")
            msg = err.get("message", "Unknown error")
            raise MCPError(f"MCP error {code}: {msg}")

        return response.get("result")

    def discover_tools(self) -> list[ToolDefinition]:
        result = self.send_request("tools/list")
        if not isinstance(result, dict) or "tools" not in result:
            return []
        tools: list[ToolDefinition] = []
        for item in result["tools"]:
            tools.append(
                ToolDefinition(
                    name=item["name"],
                    description=item.get("description", ""),
                    parameters=item.get("inputSchema", item.get("parameters", {})),
                )
            )
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Observation:
        call_id = str(uuid.uuid4())
        try:
            result = self.send_request(
                "tools/call",
                {"name": name, "arguments": arguments},
            )
            content = (
                result.get("content", result) if isinstance(result, dict) else result
            )
            # MCP tools typically return [{"type": "text", "text": "..."}]
            if isinstance(content, list) and content and isinstance(content[0], dict):
                text_parts = [
                    item.get("text", str(item))
                    for item in content
                    if "text" in item or "type" in item
                ]
                content_str = "\n".join(text_parts) if text_parts else str(content)
            else:
                content_str = str(content)

            return Observation(
                tool_call_id=call_id,
                success=True,
                content=content_str,
            )
        except Exception as exc:
            return Observation(
                tool_call_id=call_id,
                success=False,
                content="",
                error=str(exc),
            )

    def list_resources(self) -> list[dict[str, Any]]:
        result = self.send_request("resources/list")
        if isinstance(result, dict) and "resources" in result:
            return result["resources"]
        return []

    def read_resource(self, uri: str) -> str:
        result = self.send_request("resources/read", {"uri": uri})
        if isinstance(result, dict) and "contents" in result:
            contents = result["contents"]
            if isinstance(contents, list) and contents:
                first = contents[0]
                return str(first.get("text", first))
            return str(contents)
        return str(result)
