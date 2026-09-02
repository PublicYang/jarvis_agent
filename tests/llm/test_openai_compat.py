"""Tests for OpenAI-compatible LLM adapter (Phase4)."""

from __future__ import annotations

import json

import httpx
import pytest

from llm.openai_compat import OpenAICompatAdapter
from runtime.models import Message, MessageRole


def _success_response() -> dict:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": "hello back"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 3,
            "total_tokens": 15,
        },
    }


def _mock_transport(*, assert_payload: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        if assert_payload:
            payload = json.loads(request.content)
            assert payload["model"] == "gpt-4o-mini"
            assert payload["temperature"] == 0.2
            assert payload["max_tokens"] == 64
            assert payload["messages"] == [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "hi"},
            ]
        return httpx.Response(200, json=_success_response())

    return httpx.MockTransport(handler)


def _request() -> dict:
    return {
        "messages": [
            Message(role=MessageRole.SYSTEM, content="You are helpful."),
            Message(role=MessageRole.USER, content="hi"),
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "max_tokens": 64,
    }


def test_complete_success() -> None:
    client = httpx.Client(
        transport=_mock_transport(assert_payload=True),
        base_url="https://api.example.com",
    )
    adapter = OpenAICompatAdapter(
        api_key="test-key",
        base_url="https://api.example.com/v1",
        client=client,
        async_client=httpx.AsyncClient(transport=_mock_transport()),
    )

    response = adapter.complete(_request())

    assert response["content"] == "hello back"
    assert response["finish_reason"] == "stop"
    assert response["usage"] == {
        "prompt_tokens": 12,
        "completion_tokens": 3,
        "total_tokens": 15,
    }


@pytest.mark.asyncio
async def test_acomplete_success() -> None:
    async_client = httpx.AsyncClient(
        transport=_mock_transport(),
        base_url="https://api.example.com",
    )
    adapter = OpenAICompatAdapter(
        api_key="test-key",
        base_url="https://api.example.com/v1",
        client=httpx.Client(transport=_mock_transport()),
        async_client=async_client,
    )

    response = await adapter.acomplete(
        {
            "messages": [Message(role=MessageRole.USER, content="hi")],
            "model": "gpt-4o-mini",
            "temperature": 0.0,
            "max_tokens": None,
        }
    )

    assert response["content"] == "hello back"
    assert response["finish_reason"] == "stop"


def test_complete_http_error() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(401, json={"error": "unauthorized"})
    )
    client = httpx.Client(transport=transport, base_url="https://api.example.com")
    adapter = OpenAICompatAdapter(
        api_key="bad-key",
        base_url="https://api.example.com/v1",
        client=client,
        async_client=httpx.AsyncClient(transport=transport),
    )

    with pytest.raises(httpx.HTTPStatusError):
        adapter.complete(
            {
                "messages": [Message(role=MessageRole.USER, content="hi")],
                "model": "gpt-4o-mini",
                "temperature": 0.0,
                "max_tokens": None,
            }
        )
