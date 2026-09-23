"""Observability system: structured logging, tracing, and metrics (Phase15)."""

from __future__ import annotations

import contextvars
import json
import logging
import threading
import time
import uuid
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# Context management for log & trace propagation
_LOG_CONTEXT: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "_LOG_CONTEXT", default={}
)
_ACTIVE_SPAN: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
    "_ACTIVE_SPAN", default=None
)


def bind_context(**kwargs: Any) -> None:
    """Bind key-value pairs to current execution context."""
    current = dict(_LOG_CONTEXT.get())
    current.update(kwargs)
    _LOG_CONTEXT.set(current)


def get_context() -> dict[str, Any]:
    """Retrieve current bound context."""
    return dict(_LOG_CONTEXT.get())


def clear_context() -> None:
    """Clear all bound context."""
    _LOG_CONTEXT.set({})


class StructuredLogger:
    """Context-aware structured logger supporting text and JSON formats."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._logger = logging.getLogger(name)

    def _format_msg(self, level: str, message: str, extra: dict[str, Any]) -> str:
        ctx = get_context()
        combined = {**ctx, **extra}
        ts = datetime.now(UTC).isoformat()

        # Check configured log format from infra.config if available
        fmt = "text"
        try:
            from infra.config import get_config

            fmt = get_config().log_format
        except Exception:
            pass

        if fmt == "json":
            record = {
                "timestamp": ts,
                "level": level,
                "logger": self.name,
                "message": message,
                "context": combined,
            }
            return json.dumps(record, ensure_ascii=False)

        ctx_str = (
            " " + " ".join(f"{k}={v}" for k, v in combined.items()) if combined else ""
        )
        return f"[{ts}] [{level}] ({self.name}){ctx_str} - {message}"

    def info(self, message: str, **extra: Any) -> None:
        formatted = self._format_msg("INFO", message, extra)
        self._logger.info(formatted)

    def error(self, message: str, **extra: Any) -> None:
        formatted = self._format_msg("ERROR", message, extra)
        self._logger.error(formatted)

    def warning(self, message: str, **extra: Any) -> None:
        formatted = self._format_msg("WARNING", message, extra)
        self._logger.warning(formatted)

    def debug(self, message: str, **extra: Any) -> None:
        formatted = self._format_msg("DEBUG", message, extra)
        self._logger.debug(formatted)


def get_logger(name: str = "jarvis") -> StructuredLogger:
    """Factory for structured loggers."""
    return StructuredLogger(name)


@dataclass
class Span:
    """A trace span representing an operation's execution lifetime."""

    name: str
    trace_id: str
    span_id: str
    parent_span_id: str | None
    start_time: float
    end_time: float | None = None
    tags: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def duration_seconds(self) -> float:
        if self.end_time is None:
            return time.monotonic() - self.start_time
        return self.end_time - self.start_time


class Tracer:
    """Thread-safe lightweight in-memory tracer with parent-child span linkage."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._spans: list[Span] = []

    @contextmanager
    def start_span(
        self,
        name: str,
        tags: dict[str, Any] | None = None,
    ) -> Generator[Span, None, None]:
        parent = _ACTIVE_SPAN.get()
        trace_id = parent.trace_id if parent else str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent.span_id if parent else None,
            start_time=time.monotonic(),
            tags=dict(tags or {}),
        )

        token = _ACTIVE_SPAN.set(span)
        try:
            yield span
        except Exception as exc:
            span.error = str(exc)
            span.tags["error"] = True
            raise
        finally:
            span.end_time = time.monotonic()
            _ACTIVE_SPAN.reset(token)
            with self._lock:
                self._spans.append(span)

    def get_spans(self) -> list[Span]:
        with self._lock:
            return list(self._spans)

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()


_GLOBAL_TRACER = Tracer()


def get_tracer() -> Tracer:
    return _GLOBAL_TRACER


class MetricsRegistry:
    """Thread-safe collector for counters, gauges, and latency observations."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._observations: dict[str, list[float]] = defaultdict(list)

    def increment(
        self,
        metric: str,
        value: float = 1.0,
        tags: dict[str, str] | None = None,
    ) -> None:
        key = self._format_key(metric, tags)
        with self._lock:
            self._counters[key] += value

    def gauge(
        self,
        metric: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        key = self._format_key(metric, tags)
        with self._lock:
            self._gauges[key] = value

    def observe(
        self,
        metric: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        key = self._format_key(metric, tags)
        with self._lock:
            self._observations[key].append(value)

    @staticmethod
    def _format_key(metric: str, tags: dict[str, str] | None) -> str:
        if not tags:
            return metric
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric}{{{tag_str}}}"

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            summary_obs = {}
            for k, vals in self._observations.items():
                if vals:
                    summary_obs[k] = {
                        "count": len(vals),
                        "total": sum(vals),
                        "avg": sum(vals) / len(vals),
                        "min": min(vals),
                        "max": max(vals),
                    }
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "observations": summary_obs,
            }

    def clear(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._observations.clear()


_GLOBAL_METRICS = MetricsRegistry()


def get_metrics() -> MetricsRegistry:
    return _GLOBAL_METRICS
