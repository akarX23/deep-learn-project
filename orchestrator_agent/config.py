"""Runtime configuration for the Planner Agent — all values read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load planner_agent/.env first (agent-specific secrets), then project root .env.
# Neither call overrides vars already set in the process environment.
_AGENT_DOTENV = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_AGENT_DOTENV)
load_dotenv()  # project-root .env as fallback


@dataclass(frozen=True)
class LLMConfig:
    """Provider-agnostic LiteLLM call configuration for the Planner Agent.

    Set PLANNER_LLM_MODEL to any LiteLLM-compatible string:
      - Claude:  claude-sonnet-4-6
      - OpenAI:  gpt-4o
      - Local:   openai/local-model (with PLANNER_LLM_API_BASE)
    """

    model: str
    api_base: str | None = None
    api_key: str | None = None
    temperature: float = 0.2
    max_tokens: int = 2048


@dataclass(frozen=True)
class PlannerKafkaConfig:
    """Kafka connectivity and tuning parameters for the Planner Agent."""

    bootstrap_servers: str
    consumer_group_id: str = "planner-agent-group"
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = False
    session_timeout_ms: int = 45000
    max_poll_interval_ms: int = 300000
    poll_timeout_ms: int = 1000


@dataclass(frozen=True)
class PlannerConfig:
    """Aggregate runtime configuration for the Planner Agent pipeline."""

    llm: LLMConfig
    kafka: PlannerKafkaConfig
    max_retries: int = 3
    agent_response_timeout_sec: int = 120
    min_content_length: int = 100
    clarification_timeout_sec: int = 120
    level_confidence_threshold: float = 0.65
    max_query_length: int = 2000


def get_llm_config() -> LLMConfig:
    """Build LLM config from environment variables.

    Raises RuntimeError if PLANNER_LLM_MODEL is not set.
    """
    model = os.getenv("PLANNER_LLM_MODEL")
    if not model:
        raise RuntimeError(
            "PLANNER_LLM_MODEL is not set. "
            "Set it to any LiteLLM-compatible model string (e.g. claude-sonnet-4-6)."
        )
    return LLMConfig(
        model=model,
        api_base=_read_optional("PLANNER_LLM_API_BASE"),
        api_key=_read_optional("PLANNER_LLM_API_KEY"),
        temperature=_read_float("PLANNER_LLM_TEMPERATURE", 0.2),
        max_tokens=_read_int("PLANNER_LLM_MAX_TOKENS", 2048),
    )


def get_kafka_config() -> PlannerKafkaConfig:
    """Build Kafka config from environment variables.

    Raises RuntimeError if KAFKA_BOOTSTRAP_SERVERS is not set.
    """
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap_servers:
        raise RuntimeError("KAFKA_BOOTSTRAP_SERVERS is not set.")
    return PlannerKafkaConfig(
        bootstrap_servers=bootstrap_servers,
        consumer_group_id=os.getenv("KAFKA_CONSUMER_GROUP_ID", "planner-agent-group"),
        auto_offset_reset=os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest"),
        enable_auto_commit=_read_bool("KAFKA_ENABLE_AUTO_COMMIT", False),
        session_timeout_ms=_read_int("KAFKA_SESSION_TIMEOUT_MS", 45000),
        max_poll_interval_ms=_read_int("KAFKA_MAX_POLL_INTERVAL_MS", 300000),
        poll_timeout_ms=_read_int("PLANNER_KAFKA_POLL_TIMEOUT_MS", 1000),
    )


def get_confidence_threshold() -> float:
    """Return the minimum LLM confidence score to accept an inferred learner level.

    Below this threshold the planner routes to clarify_and_end and asks the
    learner to self-identify their level.
    """
    return _read_float("PLANNER_LEVEL_CONFIDENCE_THRESHOLD", 0.65)


def get_planner_config() -> PlannerConfig:
    """Build complete planner config from environment variables."""
    return PlannerConfig(
        llm=get_llm_config(),
        kafka=get_kafka_config(),
        max_retries=_read_int("PLANNER_MAX_RETRIES", 3),
        agent_response_timeout_sec=_read_int("AGENT_RESPONSE_TIMEOUT_SEC", 120),
        min_content_length=_read_int("PLANNER_MIN_CONTENT_LENGTH", 100),
        clarification_timeout_sec=_read_int("PLANNER_CLARIFICATION_TIMEOUT_SEC", 120),
        level_confidence_threshold=_read_float("PLANNER_LEVEL_CONFIDENCE_THRESHOLD", 0.65),
        max_query_length=_read_int("PLANNER_MAX_QUERY_LENGTH", 2000),
    )


# ---------------------------------------------------------------------------
# Internal env-read helpers
# ---------------------------------------------------------------------------


def _read_optional(name: str) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    return raw.strip() or None


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


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("true", "1", "yes")
