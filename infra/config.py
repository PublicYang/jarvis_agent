"""Centralized configuration management with env override (Phase15)."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field


class JarvisConfig(BaseModel):
    """Central configuration for Jarvis Agent runtime, models, storage,
    and telemetry.
    """

    # LLM Settings
    llm_api_key: str | None = Field(default=None)
    llm_base_url: str = Field(default="https://api.openai.com/v1")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_timeout: float = Field(default=60.0)

    # Runtime Settings
    runtime_engine: str = Field(default="react")
    runtime_max_steps: int = Field(default=8)
    runtime_max_retries: int = Field(default=3)
    runtime_tool_timeout: float = Field(default=30.0)

    # Storage Settings
    storage_db_path: str | None = Field(default=None)

    # Telemetry Settings
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="text")  # "text" or "json"
    trace_enabled: bool = Field(default=True)
    metrics_enabled: bool = Field(default=True)

    @classmethod
    def from_env(cls, **overrides: Any) -> JarvisConfig:
        """Create configuration loaded from environment variables with overrides."""
        env_mapping: dict[str, Any] = {}

        if "JARVIS_API_KEY" in os.environ:
            env_mapping["llm_api_key"] = os.environ["JARVIS_API_KEY"]
        if "JARVIS_BASE_URL" in os.environ:
            env_mapping["llm_base_url"] = os.environ["JARVIS_BASE_URL"]
        if "JARVIS_MODEL" in os.environ:
            env_mapping["llm_model"] = os.environ["JARVIS_MODEL"]
        if "JARVIS_LLM_TIMEOUT" in os.environ:
            env_mapping["llm_timeout"] = float(os.environ["JARVIS_LLM_TIMEOUT"])
        if "JARVIS_ENGINE" in os.environ:
            env_mapping["runtime_engine"] = os.environ["JARVIS_ENGINE"]
        if "JARVIS_MAX_STEPS" in os.environ:
            env_mapping["runtime_max_steps"] = int(os.environ["JARVIS_MAX_STEPS"])
        if "JARVIS_DB_PATH" in os.environ:
            env_mapping["storage_db_path"] = os.environ["JARVIS_DB_PATH"]
        if "JARVIS_LOG_LEVEL" in os.environ:
            env_mapping["log_level"] = os.environ["JARVIS_LOG_LEVEL"]
        if "JARVIS_LOG_FORMAT" in os.environ:
            env_mapping["log_format"] = os.environ["JARVIS_LOG_FORMAT"]
        if "JARVIS_TRACE_ENABLED" in os.environ:
            env_mapping["trace_enabled"] = os.environ[
                "JARVIS_TRACE_ENABLED"
            ].strip().lower() in {"1", "true", "yes"}
        if "JARVIS_METRICS_ENABLED" in os.environ:
            env_mapping["metrics_enabled"] = os.environ[
                "JARVIS_METRICS_ENABLED"
            ].strip().lower() in {"1", "true", "yes"}

        # Merge environment values with explicit keyword overrides
        combined = {
            **env_mapping,
            **{k: v for k, v in overrides.items() if v is not None},
        }
        return cls(**combined)


_GLOBAL_CONFIG: JarvisConfig | None = None


def get_config(**overrides: Any) -> JarvisConfig:
    """Get the active global config or initialize from environment with overrides."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None or overrides:
        _GLOBAL_CONFIG = JarvisConfig.from_env(**overrides)
    return _GLOBAL_CONFIG


def set_config(config: JarvisConfig) -> None:
    """Explicitly set global configuration."""
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = config


def reset_config() -> None:
    """Reset global configuration to None (used in test teardown)."""
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = None
