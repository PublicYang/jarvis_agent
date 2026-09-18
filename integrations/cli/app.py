"""Typer CLI — composition root for Jarvis (Phase7)."""

from __future__ import annotations

import os
from typing import Annotated

import typer
from llm.openai_compat import OpenAICompatAdapter
from memory.sqlite import SQLiteMemoryStore
from memory.store import MemoryStore
from planner.base import DecisionType, PlannerOutput
from planner.simple import SimplePlanner
from runtime.engine import RuntimeEngine
from runtime.models import Message, MessageRole, State
from tools.base import ToolCall
from tools.echo import EchoTool
from tools.executor import ToolExecutor
from tools.registry import InMemoryToolRegistry

app = typer.Typer(help="Jarvis Agent CLI", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Jarvis Agent CLI."""


class DemoPlanner:
    """Offline planner for CLI demo without an LLM API key."""

    def plan(self, state: State) -> PlannerOutput:
        if state.observations:
            last = state.observations[-1].content
            return PlannerOutput(
                decision_type=DecisionType.REPLY,
                content=f"Demo observed: {last}",
            )
        last_user = next(
            (
                message.content
                for message in reversed(state.messages)
                if message.role == MessageRole.USER
            ),
            "",
        )
        if last_user.startswith("echo "):
            return PlannerOutput(
                decision_type=DecisionType.TOOL_CALL,
                tool_call=ToolCall(
                    tool_name="echo",
                    arguments={"text": last_user.removeprefix("echo ")},
                ),
            )
        return PlannerOutput(
            decision_type=DecisionType.REPLY,
            content=f"Demo reply: {last_user}",
        )


def build_engine(
    *,
    demo: bool = False,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    memory: MemoryStore | None = None,
    approval_callback=None,
) -> RuntimeEngine:
    registry = InMemoryToolRegistry()
    registry.register(EchoTool())
    executor = ToolExecutor(registry)

    if demo:
        planner = DemoPlanner()
    else:
        if not api_key:
            raise typer.BadParameter(
                "API key required unless --demo is set "
                "(pass --api-key or set JARVIS_API_KEY)"
            )
        llm = OpenAICompatAdapter(api_key=api_key, base_url=base_url)
        planner = SimplePlanner(llm=llm, model=model, memory=memory)

    return RuntimeEngine(
        planner=planner,
        executor=executor,
        require_approval_for=frozenset(),
        approval_callback=approval_callback,
    )


@app.command()
def chat(
    message: Annotated[str, typer.Argument(help="User message for a single turn")],
    demo: Annotated[
        bool,
        typer.Option("--demo/--no-demo", help="Run offline with DemoPlanner (no LLM)"),
    ] = False,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", envvar="JARVIS_API_KEY", help="LLM API key"),
    ] = None,
    base_url: Annotated[
        str,
        typer.Option(
            "--base-url",
            envvar="JARVIS_BASE_URL",
            help="OpenAI-compatible base URL",
        ),
    ] = "https://api.openai.com/v1",
    model: Annotated[
        str,
        typer.Option("--model", envvar="JARVIS_MODEL", help="Model name"),
    ] = "gpt-4o-mini",
    db_path: Annotated[
        str | None,
        typer.Option(
            "--db-path",
            envvar="JARVIS_DB_PATH",
            help="Path to SQLite memory database for persistence",
        ),
    ] = None,
    session_id: Annotated[
        str | None,
        typer.Option(
            "--session-id",
            envvar="JARVIS_SESSION_ID",
            help="Session ID for state and conversation continuity",
        ),
    ] = None,
) -> None:
    """Run one Agent turn and print the assistant reply."""
    key = api_key or os.getenv("JARVIS_API_KEY")
    memory_store: SQLiteMemoryStore | None = None
    if db_path:
        memory_store = SQLiteMemoryStore(db_path=db_path)

    try:
        engine = build_engine(
            demo=demo,
            api_key=key,
            base_url=base_url,
            model=model,
            memory=memory_store,
            approval_callback=None,
        )

        user_msg = Message(role=MessageRole.USER, content=message)
        resume_state: State | None = None
        if memory_store and session_id:
            resume_state = memory_store.load_state(session_id)
            if resume_state is None:
                resume_state = State(id=session_id, messages=[])

        final = engine.run(user_msg, resume_state=resume_state)

        if memory_store and session_id:
            memory_store.save_state(final)

        if final.status.value == "failed":
            typer.echo(f"Failed: {final.error}", err=True)
            raise typer.Exit(code=1)
        if final.status.value == "cancelled":
            typer.echo("Cancelled", err=True)
            raise typer.Exit(code=1)

        assistant = next(
            (
                item.content
                for item in reversed(final.messages)
                if item.role == MessageRole.ASSISTANT
            ),
            "",
        )
        typer.echo(assistant)
        typer.echo(f"[status={final.status} state_id={final.id}]", err=True)
    finally:
        if memory_store:
            memory_store.close()


if __name__ == "__main__":
    app()
