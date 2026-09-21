"""Workflow edge and graph definitions (Phase11)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from workflow.node import WorkflowNode


class WorkflowValidationError(Exception):
    """Raised when a WorkflowGraph is structurally invalid."""


@dataclass(frozen=True)
class WorkflowEdge:
    """A directed edge connecting two workflow nodes."""

    from_node: str
    to_node: str
    condition: Callable[[dict[str, Any]], bool] | None = None


class WorkflowGraph:
    """Directed graph representing an executable workflow."""

    def __init__(self) -> None:
        self._nodes: dict[str, WorkflowNode] = {}
        self._edges: list[WorkflowEdge] = []
        self._entry_point: str | None = None

    @property
    def nodes(self) -> dict[str, WorkflowNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[WorkflowEdge]:
        return list(self._edges)

    @property
    def entry_point(self) -> str | None:
        return self._entry_point

    def add_node(self, node: WorkflowNode) -> None:
        """Add a node to the workflow graph."""
        if node.id in self._nodes:
            raise WorkflowValidationError(f"Node '{node.id}' already exists in graph.")
        self._nodes[node.id] = node

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        condition: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        """Add a directed edge between two nodes."""
        self._edges.append(
            WorkflowEdge(from_node=from_node, to_node=to_node, condition=condition)
        )

    def set_entry_point(self, node_id: str) -> None:
        """Specify the initial starting node for graph execution."""
        self._entry_point = node_id

    def validate(self) -> None:
        """Validate the structural integrity of the graph."""
        if not self._entry_point:
            raise WorkflowValidationError("Graph has no entry_point defined.")
        if self._entry_point not in self._nodes:
            raise WorkflowValidationError(
                f"Entry point '{self._entry_point}' not found in graph nodes."
            )

        for edge in self._edges:
            if edge.from_node not in self._nodes:
                raise WorkflowValidationError(
                    f"Edge source '{edge.from_node}' does not exist in graph nodes."
                )
            if edge.to_node not in self._nodes:
                raise WorkflowValidationError(
                    f"Edge target '{edge.to_node}' does not exist in graph nodes."
                )

    def run(
        self,
        initial_context: dict[str, Any] | None = None,
        *,
        max_steps: int = 1000,
    ) -> dict[str, Any]:
        """Execute the workflow starting from entry_point until terminal node."""
        self.validate()

        context: dict[str, Any] = dict(initial_context or {})
        current_id = self._entry_point
        step_count = 0

        while current_id is not None:
            step_count += 1
            if step_count > max_steps:
                raise RuntimeError(
                    f"Workflow execution exceeded max_steps={max_steps} "
                    "(possible cycle)."
                )

            node = self._nodes[current_id]
            context = node.execute(context)

            # Find matching outgoing edges
            next_id: str | None = None
            for edge in self._edges:
                if edge.from_node == current_id:
                    if edge.condition is None or edge.condition(context):
                        next_id = edge.to_node
                        break

            current_id = next_id

        return context
