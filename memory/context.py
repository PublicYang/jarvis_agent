"""Context builder and token management (Phase9)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from runtime.models import Message, MessageRole, State

from memory.models import MemoryRecord
from memory.store import MemoryStore

TokenEstimator = Callable[[str], int]


def default_token_estimator(text: str) -> int:
    """Heuristic token estimator: CJK chars ~1 token, Latin chars ~4 chars/token."""
    if not text:
        return 0
    cjk_count = 0
    ascii_count = 0
    for char in text:
        if ord(char) > 127:
            cjk_count += 1
        else:
            ascii_count += 1
    ascii_tokens = max(1, ascii_count // 4) if ascii_count > 0 else 0
    return cjk_count + ascii_tokens


@runtime_checkable
class ContextBuilder(Protocol):
    """Protocol for building LLM context messages from State and Memory."""

    def build(
        self,
        state: State,
        memory: MemoryStore | None = None,
    ) -> list[Message]:
        """Build compressed, budget-compliant list of Messages for LLM."""
        ...


class StandardContextBuilder:
    """Standard ContextBuilder with sliding window compression and memory injection."""

    def __init__(
        self,
        *,
        max_context_tokens: int = 4000,
        memory_budget_tokens: int = 800,
        max_memory_records: int = 5,
        token_estimator: TokenEstimator | None = None,
        truncate_notice: bool = True,
    ) -> None:
        self._max_context_tokens = max_context_tokens
        self._memory_budget_tokens = memory_budget_tokens
        self._max_memory_records = max_memory_records
        self._estimate = token_estimator or default_token_estimator
        self._truncate_notice = truncate_notice

    def estimate_message_tokens(self, message: Message) -> int:
        """Estimate tokens for a single message including structural overhead."""
        return self._estimate(message.content) + 4

    def _retrieve_memories(
        self,
        state: State,
        memory: MemoryStore | None,
    ) -> list[MemoryRecord]:
        if memory is None:
            return []

        records_dict: dict[str, MemoryRecord] = {}

        # 1. Explicitly referenced memories in state.memory_refs
        for ref_id in state.memory_refs:
            rec = memory.get(ref_id)
            if rec and not rec.is_expired():
                records_dict[rec.id] = rec

        # 2. Search relevant memories based on latest user message
        user_msgs = [m for m in state.messages if m.role == MessageRole.USER]
        if user_msgs:
            query = user_msgs[-1].content
            search_results = memory.search(query=query, limit=self._max_memory_records)
            for rec in search_results:
                if (
                    rec.id not in records_dict
                    and len(records_dict) < self._max_memory_records
                ):
                    records_dict[rec.id] = rec

        return list(records_dict.values())

    def _format_memory_section(self, memories: list[MemoryRecord]) -> str:
        if not memories:
            return ""
        lines = ["[Relevant Memories & Context]"]
        for rec in memories:
            lines.append(f"- [{rec.scope.value}] {rec.key}: {rec.content}")
        return "\n".join(lines)

    def build(
        self,
        state: State,
        memory: MemoryStore | None = None,
    ) -> list[Message]:
        """Build budget-compliant context messages combining State and Memory."""
        if not state.messages:
            memories = self._retrieve_memories(state, memory)
            if memories:
                mem_text = self._format_memory_section(memories)
                return [Message(role=MessageRole.SYSTEM, content=mem_text)]
            return []

        # 1. Retrieve and format memories
        memories = self._retrieve_memories(state, memory)
        memory_section = self._format_memory_section(memories)

        # 2. Extract leading system message if present
        original_messages = list(state.messages)
        system_msg: Message | None = None
        history_msgs: list[Message]

        if original_messages[0].role == MessageRole.SYSTEM:
            system_msg = original_messages[0]
            history_msgs = original_messages[1:]
        else:
            history_msgs = original_messages

        # Merge memory section into system message
        if memory_section:
            if system_msg is not None:
                merged_content = f"{system_msg.content}\n\n{memory_section}"
                system_msg = Message(
                    role=MessageRole.SYSTEM,
                    content=merged_content,
                    metadata=system_msg.metadata,
                )
            else:
                system_msg = Message(
                    role=MessageRole.SYSTEM,
                    content=memory_section,
                )

        if not history_msgs:
            return [system_msg] if system_msg else []

        # 3. Calculate budget for history messages
        system_tokens = self.estimate_message_tokens(system_msg) if system_msg else 0
        available_history_tokens = max(0, self._max_context_tokens - system_tokens)

        # Check if entire history fits
        total_history_tokens = sum(
            self.estimate_message_tokens(m) for m in history_msgs
        )
        if total_history_tokens <= available_history_tokens:
            result: list[Message] = []
            if system_msg:
                result.append(system_msg)
            result.extend(history_msgs)
            return result

        # 4. Sliding window selection
        # Identify latest user message index to preserve current query
        latest_user_idx: int | None = None
        for idx in range(len(history_msgs) - 1, -1, -1):
            if history_msgs[idx].role == MessageRole.USER:
                latest_user_idx = idx
                break

        selected_indices: set[int] = set()
        used_tokens = 0

        # Always preserve latest user message
        if latest_user_idx is not None:
            latest_user_msg = history_msgs[latest_user_idx]
            user_tokens = self.estimate_message_tokens(latest_user_msg)
            selected_indices.add(latest_user_idx)
            used_tokens += user_tokens

        notice_msg = (
            Message(
                role=MessageRole.SYSTEM,
                content=(
                    "[Context: Earlier conversation history was "
                    "truncated due to token budget limit.]"
                ),
            )
            if self._truncate_notice
            else None
        )
        notice_tokens = self.estimate_message_tokens(notice_msg) if notice_msg else 0
        budget_for_selection = max(0, available_history_tokens - notice_tokens)

        # Traverse remaining messages backwards (newest to oldest)
        for idx in range(len(history_msgs) - 1, -1, -1):
            if idx in selected_indices:
                continue
            msg_tokens = self.estimate_message_tokens(history_msgs[idx])
            if used_tokens + msg_tokens <= budget_for_selection:
                selected_indices.add(idx)
                used_tokens += msg_tokens

        selected_msgs = [history_msgs[idx] for idx in sorted(selected_indices)]

        # Guarantee at least the latest message is present
        if not selected_msgs and history_msgs:
            selected_msgs.append(history_msgs[-1])

        result = []
        if system_msg:
            result.append(system_msg)
        if len(selected_indices) < len(history_msgs) and notice_msg:
            result.append(notice_msg)
        result.extend(selected_msgs)

        return result
