"""OpenAI-compatible LLM adapter implementation (Phase4)."""

from __future__ import annotations

from typing import Any

import httpx
from runtime.models import Message

from llm.adapter import LLMRequest, LLMResponse


class OpenAICompatAdapter:
    """Adapter for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        client: httpx.Client | None = None,
        async_client: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)
        self._async_client = async_client or httpx.AsyncClient(timeout=timeout)
        self._owns_sync_client = client is None
        self._owns_async_client = async_client is None

    def complete(self, request: LLMRequest) -> LLMResponse:
        response = self._client.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers(),
            json=self._build_payload(request),
        )
        response.raise_for_status()
        return self._parse_response(response.json())

    async def acomplete(self, request: LLMRequest) -> LLMResponse:
        response = await self._async_client.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers(),
            json=self._build_payload(request),
        )
        response.raise_for_status()
        return self._parse_response(response.json())

    def close(self) -> None:
        if self._owns_sync_client:
            self._client.close()

    async def aclose(self) -> None:
        if self._owns_async_client:
            await self._async_client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request["model"],
            "messages": [_message_to_api(message) for message in request["messages"]],
            "temperature": request["temperature"],
        }
        max_tokens = request.get("max_tokens")
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        return payload

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage", {})
        return LLMResponse(
            content=message["content"],
            finish_reason=choice["finish_reason"],
            usage={
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
                "total_tokens": int(usage.get("total_tokens", 0)),
            },
        )


def _message_to_api(message: Message) -> dict[str, str]:
    return {"role": message.role.value, "content": message.content}
