"""Parallel execution nodes and merge strategies (Phase13)."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from tools.base import Observation, ToolCall
from tools.executor import ToolExecutor

from workflow.node import WorkflowNode

MergeStrategy = Callable[
    [dict[str, Any], list[tuple[str, dict[str, Any]]]], dict[str, Any]
]


class ParallelExecutionError(Exception):
    """Raised when one or more parallel branches fail."""

    def __init__(self, errors: dict[str, Exception]) -> None:
        self.errors = errors
        details = ", ".join(f"{node_id}: {err}" for node_id, err in errors.items())
        super().__init__(
            f"Parallel execution failed in {len(errors)} node(s): {details}"
        )


def default_merge_strategy(
    base_context: dict[str, Any],
    branch_results: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Default merge: shallow-merges all branch key-values in deterministic order."""
    merged = dict(base_context)
    for _node_id, branch_ctx in branch_results:
        merged.update(branch_ctx)
    return merged


def namespaced_merge_strategy(
    namespace_key: str = "branches",
) -> MergeStrategy:
    """Namespaced merge: saves branch result under context[namespace_key][node_id]."""

    def _merge(
        base_context: dict[str, Any],
        branch_results: list[tuple[str, dict[str, Any]]],
    ) -> dict[str, Any]:
        merged = dict(base_context)
        ns = dict(merged.get(namespace_key, {}))
        for node_id, branch_ctx in branch_results:
            ns[node_id] = branch_ctx
        merged[namespace_key] = ns
        return merged

    return _merge


class ParallelNode:
    """Executes multiple WorkflowNodes concurrently in a thread pool."""

    def __init__(
        self,
        node_id: str,
        nodes: list[WorkflowNode],
        *,
        max_workers: int = 4,
        merge_strategy: MergeStrategy | None = None,
        timeout: float | None = None,
    ) -> None:
        self.id = node_id
        self.nodes = list(nodes)
        self.max_workers = max_workers
        self.merge_strategy = merge_strategy or default_merge_strategy
        self.timeout = timeout

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        if not self.nodes:
            return dict(context)

        results: list[tuple[str, dict[str, Any]]] = []
        errors: dict[str, Exception] = {}

        def _run_subnode(node: WorkflowNode) -> tuple[str, dict[str, Any]]:
            isolated_ctx = dict(context)
            return node.id, node.execute(isolated_ctx)

        workers = min(self.max_workers, len(self.nodes))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_run_subnode, node): node.id for node in self.nodes}
            for future in as_completed(futures, timeout=self.timeout):
                node_id = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    errors[node_id] = exc

        if errors:
            raise ParallelExecutionError(errors)

        # Sort results deterministically by node order in self.nodes
        node_order = {node.id: idx for idx, node in enumerate(self.nodes)}
        results.sort(key=lambda item: node_order.get(item[0], 0))

        return self.merge_strategy(context, results)

    def __repr__(self) -> str:
        return f"ParallelNode(id={self.id!r}, nodes={len(self.nodes)})"


class ParallelToolNode:
    """Executes multiple ToolCalls concurrently without race conditions."""

    def __init__(
        self,
        node_id: str,
        executor: ToolExecutor,
        tool_calls: list[ToolCall] | Callable[[dict[str, Any]], list[ToolCall]],
        *,
        max_workers: int = 4,
        result_key: str = "observations",
        timeout: float | None = None,
    ) -> None:
        self.id = node_id
        self._executor = executor
        self._tool_calls = tool_calls
        self.max_workers = max_workers
        self.result_key = result_key
        self.timeout = timeout

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        calls = (
            self._tool_calls(context)
            if callable(self._tool_calls)
            else self._tool_calls
        )
        if not calls:
            return dict(context)

        workers = min(self.max_workers, len(calls))
        results: list[tuple[int, ToolCall, Observation]] = []
        errors: dict[str, Exception] = {}

        def _invoke(idx: int, call: ToolCall) -> tuple[int, ToolCall, Observation]:
            finished, obs = self._executor.execute(call)
            return idx, finished, obs

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_invoke, idx, call): call for idx, call in enumerate(calls)
            }
            for future in as_completed(futures, timeout=self.timeout):
                call = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    errors[call.id] = exc

        if errors:
            raise ParallelExecutionError(errors)

        # Maintain original order of calls
        results.sort(key=lambda item: item[0])
        observations = [obs for _, _, obs in results]

        updated = dict(context)
        existing = list(updated.get(self.result_key, []))
        existing.extend(observations)
        updated[self.result_key] = existing
        return updated

    def __repr__(self) -> str:
        return f"ParallelToolNode(id={self.id!r})"
