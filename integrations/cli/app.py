"""Typer CLI — composition root for Jarvis (Phase7)."""

from __future__ import annotations

import os
from typing import Annotated

import typer
from llm.openai_compat import OpenAICompatAdapter
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
    demo: bool,
    api_key: str | None,
    base_url: str,
    model: str,
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
        planner = SimplePlanner(llm=llm, model=model)

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
) -> None:
    """Run one Agent turn and print the assistant reply."""
    key = api_key or os.getenv("JARVIS_API_KEY")
    engine = build_engine(
        demo=demo,
        api_key=key,
        base_url=base_url,
        model=model,
        approval_callback=None,
    )
    final = engine.run(Message(role=MessageRole.USER, content=message))
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


if __name__ == "__main__":
    app()
