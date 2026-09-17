"""Unit tests for ContextBuilder and token management (Phase9)."""

from memory.context import (
    ContextBuilder,
    StandardContextBuilder,
    default_token_estimator,
)
from memory.models import MemoryRecord, MemoryScope
from memory.store import InMemoryMemoryStore
from runtime.models import Message, MessageRole, State


def test_default_token_estimator() -> None:
    assert default_token_estimator("") == 0
    # English: "hello world" (11 chars) -> 11 // 4 = 2
    assert default_token_estimator("hello world") == 2
    # CJK: 4 characters -> 4 tokens
    assert default_token_estimator("你好世界") == 4
    # Mixed: 4 CJK + 12 ASCII -> 4 + (12 // 4) = 7
    assert default_token_estimator("你好世界 hello world") == 7


def test_standard_context_builder_implements_protocol() -> None:
    builder = StandardContextBuilder()
    assert isinstance(builder, ContextBuilder)


def test_context_builder_empty_state() -> None:
    builder = StandardContextBuilder()
    state = State(messages=[])
    assert builder.build(state) == []


def test_context_builder_within_budget_no_truncation() -> None:
    builder = StandardContextBuilder(max_context_tokens=1000)
    messages = [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello"),
        Message(role=MessageRole.ASSISTANT, content="Hi there!"),
        Message(role=MessageRole.USER, content="How are you?"),
    ]
    state = State(messages=messages)
    built = builder.build(state)

    assert len(built) == 4
    assert [m.content for m in built] == [m.content for m in messages]


def test_context_builder_sliding_window_truncation() -> None:
    # Set a tight budget of 50 tokens
    builder = StandardContextBuilder(max_context_tokens=60, truncate_notice=True)
    system_msg = Message(role=MessageRole.SYSTEM, content="System prompt instructions.")
    # Generate 15 conversation turns
    history = []
    for i in range(15):
        history.append(
            Message(
                role=MessageRole.USER,
                content=f"User question {i} with some detailed description.",
            )
        )
        history.append(
            Message(
                role=MessageRole.ASSISTANT,
                content=f"Assistant reply {i} with long detailed answer explanation.",
            )
        )

    state = State(messages=[system_msg, *history])
    built = builder.build(state)

    # 1. Total tokens must fit within budget
    total_tokens = sum(builder.estimate_message_tokens(m) for m in built)
    assert total_tokens <= 60

    # 2. System prompt must be preserved at index 0
    assert built[0].role == MessageRole.SYSTEM
    assert "System prompt instructions." in built[0].content

    # 3. Truncation notice must be present
    assert any("truncated" in m.content.lower() for m in built)

    # 4. Latest user message must be preserved
    latest_user = history[-2]  # last turn user question
    assert any(latest_user.content == m.content for m in built)


def test_context_builder_memory_injection_with_existing_system_msg() -> None:
    store = InMemoryMemoryStore()
    rec1 = MemoryRecord(
        key="user_name",
        content="Alice",
        scope=MemoryScope.USER,
    )
    rec2 = MemoryRecord(
        key="topic",
        content="Artificial Intelligence",
        scope=MemoryScope.SESSION,
    )
    store.write(rec1)
    store.write(rec2)

    state = State(
        messages=[
            Message(role=MessageRole.SYSTEM, content="Base system prompt."),
            Message(
                role=MessageRole.USER,
                content="Tell me about Artificial Intelligence",
            ),
        ],
        memory_refs=[rec1.id],  # Explicit reference
    )

    builder = StandardContextBuilder()
    built = builder.build(state, store)

    assert len(built) == 2
    system_content = built[0].content
    assert "Base system prompt." in system_content
    assert "[Relevant Memories & Context]" in system_content
    assert "user_name: Alice" in system_content
    assert "topic: Artificial Intelligence" in system_content


def test_context_builder_memory_injection_without_existing_system_msg() -> None:
    store = InMemoryMemoryStore()
    rec = MemoryRecord(
        key="language",
        content="Python",
        scope=MemoryScope.USER,
    )
    store.write(rec)

    state = State(
        messages=[Message(role=MessageRole.USER, content="Code in Python")],
        memory_refs=[rec.id],
    )

    builder = StandardContextBuilder()
    built = builder.build(state, store)

    # Should create a leading system message with memory context
    assert len(built) == 2
    assert built[0].role == MessageRole.SYSTEM
    assert "language: Python" in built[0].content
    assert built[1].content == "Code in Python"


def test_context_builder_custom_estimator() -> None:
    def fixed_estimator(text: str) -> int:
        return 5

    builder = StandardContextBuilder(
        max_context_tokens=30,
        token_estimator=fixed_estimator,
    )
    # Each message has 5 + 4 = 9 tokens
    messages = [Message(role=MessageRole.USER, content=f"msg_{i}") for i in range(10)]
    state = State(messages=messages)
    built = builder.build(state)

    # 30 budget with 9 tokens for notice and 9 tokens per msg allows ~2 messages
    assert len(built) < len(messages)
