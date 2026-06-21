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

    effort: optional output compute level (low/medium/high); passed as
    output_config to Claude 4.6 models only (Sonnet 4.6, Opus 4.6);
    silently ignored for all other models.
    """

    model: str
    api_base: str | None = None
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 1024
    effort: str | None = None


_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_REFLECTION_MAX_TOKENS = 512
_DEFAULT_REFLECTION_ITERATIONS = 1

# Multi-turn conversation memory (maintained inside the Teaching Agent).
_DEFAULT_MAX_HISTORY_MESSAGES = 6
_DEFAULT_SESSION_TTL_SECONDS = 300


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


def _resolve_temperature(mode_upper: str) -> float:
    """Per-mode temperature override, else shared TEACHING_TEMPERATURE, else 0.7."""
    if os.getenv(f"TEACHING_{mode_upper}_TEMPERATURE"):
        return _read_float(f"TEACHING_{mode_upper}_TEMPERATURE", 0.7)
    return _read_float("TEACHING_TEMPERATURE", 0.7)


def get_llm_config(output_mode: str) -> LLMConfig:
    """Build LLM config from environment variables for the given output mode.

    Per-mode overrides (TEACHING_{MODE}_MODEL, TEACHING_{MODE}_API_KEY,
    TEACHING_{MODE}_MAX_TOKENS) take precedence over the shared fallbacks.
    TEACHING_MODEL is required when no per-mode model override is set.
    """
    mode_upper = output_mode.upper()

    model = os.getenv(f"TEACHING_{mode_upper}_MODEL") or os.getenv("TEACHING_MODEL")
    if not model:
        raise RuntimeError(
            f"No model configured for '{output_mode}' mode. "
            f"Set TEACHING_{mode_upper}_MODEL or TEACHING_MODEL to any "
            "LiteLLM-compatible model string "
            "(e.g. groq/llama-3.3-70b-versatile, anthropic/claude-sonnet-4-6, gpt-4o)."
        )

    api_key = os.getenv(f"TEACHING_{mode_upper}_API_KEY") or os.getenv("TEACHING_API_KEY")
    max_tokens = _read_int(f"TEACHING_{mode_upper}_MAX_TOKENS", _DEFAULT_MAX_TOKENS)
    temperature = _resolve_temperature(mode_upper)
    effort = os.getenv(f"TEACHING_{mode_upper}_EFFORT") or None

    return LLMConfig(
        model=model,
        api_base=os.getenv("TEACHING_API_BASE"),
        api_key=api_key or None,
        temperature=temperature,
        max_tokens=max_tokens,
        effort=effort,
    )


def get_reflection_config(output_mode: str) -> LLMConfig:
    """Build the reflection (critique) LLM config for the given output mode.

    Returns a generic LLMConfig whose `model` and `max_tokens` ARE the reflection
    model and reflection ceiling (no extra fields on LLMConfig). Resolution:
      - model:       TEACHING_{MODE}_REFLECTION_MODEL -> TEACHING_REFLECTION_MODEL
                     -> TEACHING_MODEL (required)
      - api_key:     TEACHING_{MODE}_API_KEY -> TEACHING_API_KEY (same as generation)
      - max_tokens:  TEACHING_REFLECTION_MAX_TOKENS -> 512
      - temperature: same resolution as generation
      - effort:      never set for reflection calls
    """
    mode_upper = output_mode.upper()

    model = (
        os.getenv(f"TEACHING_{mode_upper}_REFLECTION_MODEL")
        or os.getenv("TEACHING_REFLECTION_MODEL")
        or os.getenv("TEACHING_MODEL")
    )
    if not model:
        raise RuntimeError(
            f"No reflection model configured for '{output_mode}' mode. "
            f"Set TEACHING_{mode_upper}_REFLECTION_MODEL, TEACHING_REFLECTION_MODEL, "
            "or TEACHING_MODEL to a LiteLLM-compatible model string."
        )

    api_key = os.getenv(f"TEACHING_{mode_upper}_API_KEY") or os.getenv("TEACHING_API_KEY")

    return LLMConfig(
        model=model,
        api_base=os.getenv("TEACHING_API_BASE"),
        api_key=api_key or None,
        temperature=_resolve_temperature(mode_upper),
        max_tokens=_read_int(
            "TEACHING_REFLECTION_MAX_TOKENS", _DEFAULT_REFLECTION_MAX_TOKENS
        ),
        effort=None,
    )


def get_guardrail_config() -> LLMConfig | None:
    """Build LLM config for the guardrail classification call.

    Returns None when TEACHING_GUARDRAIL_ENABLED is explicitly set to "false"
    (any other value, including unset, is treated as enabled).
    Model: TEACHING_GUARDRAIL_MODEL -> TEACHING_MODEL (required).
    """
    enabled = os.getenv("TEACHING_GUARDRAIL_ENABLED", "true").strip().lower()
    if enabled == "false":
        return None

    model = os.getenv("TEACHING_GUARDRAIL_MODEL") or os.getenv("TEACHING_MODEL")
    if not model:
        raise RuntimeError(
            "No model configured for the guardrail. "
            "Set TEACHING_GUARDRAIL_MODEL or TEACHING_MODEL to a LiteLLM-compatible model string."
        )

    api_key = os.getenv("TEACHING_GUARDRAIL_API_KEY") or os.getenv("TEACHING_API_KEY")

    return LLMConfig(
        model=model,
        api_base=os.getenv("TEACHING_API_BASE"),
        api_key=api_key or None,
        temperature=0.0,
        max_tokens=128,
        effort=None,
    )


def get_max_reflection_iterations(output_mode: str) -> int:
    """Resolve the reflection iteration count (N) for the given output mode.

    TEACHING_{MODE}_MAX_REFLECTION_ITERATIONS -> TEACHING_MAX_REFLECTION_ITERATIONS
    -> default 1. Clamped to >= 0 (0 disables reflection).
    """
    mode_upper = output_mode.upper()
    raw = (
        os.getenv(f"TEACHING_{mode_upper}_MAX_REFLECTION_ITERATIONS")
        or os.getenv("TEACHING_MAX_REFLECTION_ITERATIONS")
    )
    if raw is None:
        return _DEFAULT_REFLECTION_ITERATIONS
    try:
        return max(0, int(raw))
    except ValueError as exc:
        raise ValueError(
            "TEACHING_MAX_REFLECTION_ITERATIONS must be an integer"
        ) from exc


# ---------------------------------------------------------------------------
# Multi-turn conversation memory
# ---------------------------------------------------------------------------


def get_max_history_messages() -> int:
    """Max chat-history messages the agent keeps per session.

    Each user/assistant entry counts as one message. TEACHING_MAX_HISTORY_MESSAGES
    -> default 6 (~3 back-and-forth exchanges). Clamped to >= 0; 0 disables memory.
    """
    raw = os.getenv("TEACHING_MAX_HISTORY_MESSAGES")
    if raw is None:
        return _DEFAULT_MAX_HISTORY_MESSAGES
    try:
        return max(0, int(raw))
    except ValueError as exc:
        raise ValueError("TEACHING_MAX_HISTORY_MESSAGES must be an integer") from exc


def get_session_ttl_seconds() -> float:
    """Idle lifetime of a conversation session, in seconds.

    A session with no new turn within this window is dropped (history reset on
    the next request). TEACHING_SESSION_TTL_SECONDS -> default 300 (5 minutes).
    Clamped to >= 0.
    """
    raw = os.getenv("TEACHING_SESSION_TTL_SECONDS")
    if raw is None:
        return float(_DEFAULT_SESSION_TTL_SECONDS)
    try:
        return max(0.0, float(raw))
    except ValueError as exc:
        raise ValueError("TEACHING_SESSION_TTL_SECONDS must be a number") from exc


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
