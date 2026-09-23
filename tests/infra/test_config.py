"""Tests for Phase 15 centralized configuration system."""

from __future__ import annotations

from infra.config import JarvisConfig, get_config, reset_config, set_config


def test_config_defaults() -> None:
    reset_config()
    cfg = JarvisConfig()
    assert cfg.llm_model == "gpt-4o-mini"
    assert cfg.runtime_engine == "react"
    assert cfg.runtime_max_steps == 8
    assert cfg.trace_enabled is True
    assert cfg.metrics_enabled is True
    assert cfg.log_level == "INFO"


def test_config_env_override(monkeypatch) -> None:
    reset_config()
    monkeypatch.setenv("JARVIS_API_KEY", "sk-custom-key-123")
    monkeypatch.setenv("JARVIS_MODEL", "gpt-4o")
    monkeypatch.setenv("JARVIS_ENGINE", "workflow")
    monkeypatch.setenv("JARVIS_MAX_STEPS", "15")
    monkeypatch.setenv("JARVIS_LOG_FORMAT", "json")
    monkeypatch.setenv("JARVIS_TRACE_ENABLED", "false")
    monkeypatch.setenv("JARVIS_DB_PATH", "/tmp/jarvis.db")

    cfg = JarvisConfig.from_env()
    assert cfg.llm_api_key == "sk-custom-key-123"
    assert cfg.llm_model == "gpt-4o"
    assert cfg.runtime_engine == "workflow"
    assert cfg.runtime_max_steps == 15
    assert cfg.log_format == "json"
    assert cfg.trace_enabled is False
    assert cfg.storage_db_path == "/tmp/jarvis.db"


def test_get_and_set_config() -> None:
    reset_config()
    custom = JarvisConfig(llm_model="claude-3-opus", runtime_max_steps=20)
    set_config(custom)
    active = get_config()
    assert active.llm_model == "claude-3-opus"
    assert active.runtime_max_steps == 20
    reset_config()
