"""LLM adapter interface (Phase4)."""

from __future__ import annotations

from typing import Protocol, TypedDict

from runtime.models import Message


class LLMRequest(TypedDict):
    messages: list[Message]
    model: str
    temperature: float
    max_tokens: int | None


class LLMResponse(TypedDict):
    content: str
    finish_reason: str
    usage: dict[str, int]


class LLMAdapter(Protocol):
    """Abstract contract for LLM providers."""

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Synchronously complete one LLM call."""
        ...

    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        """Asynchronously complete one LLM call."""
        ...
