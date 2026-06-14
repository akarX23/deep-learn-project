"""Runtime configuration for the Teaching Agent LLM calls."""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # loads .env from project root
load_dotenv(".env.local", override=False)  # loads local dev overrides; existing env vars win

@dataclass(frozen=True)
class LLMConfig:
    """Provider-agnostic LiteLLM call configuration.

    Set TEACHING_MODEL to any LiteLLM model string:
      - Claude:  claude-sonnet-4-6
      - Gemini:  gemini/gemini-1.5-flash
      - OpenAI:  gpt-4o
      - Local:   openai/local-model  (with TEACHING_API_BASE)

    Provider API keys are read automatically by LiteLLM from their standard
    env vars (ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, etc.).
    TEACHING_API_KEY / TEACHING_API_BASE are optional overrides for
    non-standard or self-hosted endpoints.
    """

    model: str
    api_base: str | None = None
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 1024


# Per-mode completion token ceilings enforced at the LiteLLM call boundary.
MODE_MAX_TOKENS: dict[str, int] = {
    "beginner": 4096,
    "intermediate": 4096,
    "advanced": 4096,
}


def _read_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float") from exc


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def get_llm_config(output_mode: str) -> LLMConfig:
    """Build LLM config from environment variables for the given output mode.

    TEACHING_MODEL is required. Set it to any LiteLLM-compatible model string.
    The token ceiling is read from TEACHING_{MODE}_MAX_TOKENS if set,
    otherwise falls back to the spec default for that mode.
    """
    model = os.getenv("TEACHING_MODEL")
    if not model:
        raise RuntimeError(
            "TEACHING_MODEL environment variable is not set. "
            "Set it to any LiteLLM-compatible model string "
            "(e.g. claude-sonnet-4-6, gemini/gemini-1.5-flash, gpt-4o)."
        )

    max_tokens = _read_int(
        f"TEACHING_{output_mode.upper()}_MAX_TOKENS",
        MODE_MAX_TOKENS[output_mode],
    )
    return LLMConfig(
        model=model,
        api_base=os.getenv("TEACHING_API_BASE"),
        api_key=os.getenv("TEACHING_API_KEY"),
        temperature=_read_float("TEACHING_TEMPERATURE", 0.7),
        max_tokens=max_tokens,
    )


# ---------------------------------------------------------------------------
# Kafka runtime configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KafkaRuntimeConfig:
    """Kafka connection config for the Teaching Agent worker.

    Reads BACKEND_KAFKA_* env vars — the same cluster used by the backend service
    and RAG agent. Uses teaching-agent-specific client_id and consumer_group_id.
    """

    bootstrap_servers: str
    client_id: str = "teaching-agent"
    security_protocol: str | None = None
    consumer_group_id: str = "teaching-agent-consumer"
    poll_timeout_ms: int = 1000

    @classmethod
    def from_env(cls, dotenv_path: str = ".env.local") -> "KafkaRuntimeConfig":
        """Build Kafka runtime config from environment variables."""
        from pathlib import Path
        if Path(dotenv_path).exists():
            load_dotenv(dotenv_path=dotenv_path, override=False)
        bootstrap_servers = os.environ.get("BACKEND_KAFKA_BOOTSTRAP_SERVERS", "").strip()
        if not bootstrap_servers:
            raise RuntimeError("BACKEND_KAFKA_BOOTSTRAP_SERVERS is required")
        return cls(
            bootstrap_servers=bootstrap_servers,
            security_protocol=os.environ.get("BACKEND_KAFKA_SECURITY_PROTOCOL") or None,
            poll_timeout_ms=_read_int("BACKEND_KAFKA_POLL_TIMEOUT_MS", 1000),
        )

    def producer_kwargs(self) -> dict:
        """Return kafka-python kwargs for the producer."""
        kwargs: dict = {
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": self.client_id,
        }
        if self.security_protocol:
            kwargs["security_protocol"] = self.security_protocol
        return kwargs

    def consumer_kwargs(self) -> dict:
        """Return kafka-python kwargs for the consumer."""
        kwargs: dict = {
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": self.client_id,
            "group_id": self.consumer_group_id,
            "auto_offset_reset": "earliest",
            "enable_auto_commit": True,
        }
        if self.security_protocol:
            kwargs["security_protocol"] = self.security_protocol
        return kwargs
