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


def test_build_engine_accepts_memory() -> None:
    from memory.store import InMemoryMemoryStore

    store = InMemoryMemoryStore()
    engine = build_engine(
        demo=True,
        api_key=None,
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        memory=store,
    )
    assert engine is not None


def test_cli_chat_with_sqlite_persistence(tmp_path) -> None:
    from memory.sqlite import SQLiteMemoryStore

    db_file = tmp_path / "cli_test.db"

    # Turn 1
    res1 = runner.invoke(
        app,
        [
            "chat",
            "--demo",
            "--db-path",
            str(db_file),
            "--session-id",
            "session-abc",
            "first turn message",
        ],
    )
    assert res1.exit_code == 0
    assert "Demo reply: first turn message" in res1.stdout

    # Verify state was saved to SQLite
    with SQLiteMemoryStore(db_path=str(db_file)) as store:
        saved = store.load_state("session-abc")
        assert saved is not None
        assert len(saved.messages) == 2

    # Turn 2 with same session ID
    res2 = runner.invoke(
        app,
        [
            "chat",
            "--demo",
            "--db-path",
            str(db_file),
            "--session-id",
            "session-abc",
            "second turn message",
        ],
    )
    assert res2.exit_code == 0
    assert "Demo reply: second turn message" in res2.stdout

    # Verify state was updated with all 4 messages
    with SQLiteMemoryStore(db_path=str(db_file)) as store:
        saved = store.load_state("session-abc")
        assert saved is not None
        assert len(saved.messages) == 4
        assert saved.messages[0].content == "first turn message"
        assert saved.messages[1].content == "Demo reply: first turn message"
        assert saved.messages[2].content == "second turn message"
        assert saved.messages[3].content == "Demo reply: second turn message"


def test_cli_chat_explicit_react_engine() -> None:
    result = runner.invoke(app, ["chat", "--engine", "react", "--demo", "hello react"])
    assert result.exit_code == 0
    assert "Demo reply: hello react" in result.stdout


def test_cli_chat_workflow_engine_demo_reply() -> None:
    result = runner.invoke(
        app, ["chat", "--engine", "workflow", "--demo", "hello flow"]
    )
    assert result.exit_code == 0
    assert "Demo reply: hello flow" in result.stdout


def test_cli_chat_workflow_engine_demo_echo_tool() -> None:
    result = runner.invoke(
        app, ["chat", "--engine", "workflow", "--demo", "echo graph"]
    )
    assert result.exit_code == 0
    assert "Demo observed: graph" in result.stdout


def test_cli_chat_workflow_engine_with_sqlite_persistence(tmp_path) -> None:
    from memory.sqlite import SQLiteMemoryStore

    db_file = tmp_path / "cli_workflow_test.db"

    # Turn 1 via chat --engine workflow
    res1 = runner.invoke(
        app,
        [
            "chat",
            "--engine",
            "workflow",
            "--demo",
            "--db-path",
            str(db_file),
            "--session-id",
            "flow-session-1",
            "first turn",
        ],
    )
    assert res1.exit_code == 0
    assert "Demo reply: first turn" in res1.stdout

    # Turn 2 via chat --engine workflow
    res2 = runner.invoke(
        app,
        [
            "chat",
            "--engine",
            "workflow",
            "--demo",
            "--db-path",
            str(db_file),
            "--session-id",
            "flow-session-1",
            "second turn",
        ],
    )
    assert res2.exit_code == 0
    assert "Demo reply: second turn" in res2.stdout

    with SQLiteMemoryStore(db_path=str(db_file)) as store:
        saved = store.load_state("flow-session-1")
        assert saved is not None
        assert len(saved.messages) == 4
        assert saved.messages[0].content == "first turn"
        assert saved.messages[2].content == "second turn"


def test_cli_chat_invalid_engine() -> None:
    result = runner.invoke(
        app,
        ["chat", "--engine", "unsupported", "--demo", "ping"],
    )
    assert result.exit_code != 0
    assert "Unknown engine" in result.output
