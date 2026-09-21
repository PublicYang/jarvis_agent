"""Workflow node definitions (Phase11)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


class NodeExecutionError(Exception):
    """Raised when an error occurs during workflow node execution."""

    def __init__(self, node_id: str, message: str) -> None:
        self.node_id = node_id
        super().__init__(f"Node '{node_id}' failed: {message}")


@runtime_checkable
class WorkflowNode(Protocol):
    """Protocol for a node within a WorkflowGraph."""

    id: str

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute node logic, returning updated or mutated context."""
        ...


class FunctionNode:
    """A concrete WorkflowNode wrapping a python function/callable."""

    def __init__(
        self,
        node_id: str,
        func: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self.id = node_id
        self._func = func

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._func(context)
        except Exception as exc:
            raise NodeExecutionError(self.id, str(exc)) from exc

    def __repr__(self) -> str:
        return f"FunctionNode(id={self.id!r})"
