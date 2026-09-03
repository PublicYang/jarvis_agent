"""CLI composition-root tests (Phase7)."""

from __future__ import annotations

from integrations.cli.app import app, build_engine
from runtime.models import Message, MessageRole, StateStatus
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_chat_demo_reply() -> None:
    result = runner.invoke(app, ["chat", "--demo", "hello"])
    assert result.exit_code == 0
    assert "Demo reply: hello" in result.stdout


def test_cli_chat_demo_echo_tool() -> None:
    result = runner.invoke(app, ["chat", "--demo", "echo jarvis"])
    assert result.exit_code == 0
    assert "Demo observed: jarvis" in result.stdout


def test_cli_chat_requires_api_key_without_demo() -> None:
    result = runner.invoke(app, ["chat", "hello"], env={"JARVIS_API_KEY": ""})
    assert result.exit_code != 0


def test_build_engine_demo_runs() -> None:
    engine = build_engine(
        demo=True,
        api_key=None,
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
    )
    final = engine.run(Message(role=MessageRole.USER, content="ping"))
    assert final.status == StateStatus.COMPLETED
    assert final.messages[-1].content == "Demo reply: ping"
