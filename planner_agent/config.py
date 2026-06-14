"""Environment-driven configuration for the planner agent."""

from __future__ import annotations

import os


def get_llm_config() -> dict[str, object]:
    """Build the LLM config for level/quiz inference from environment variables."""

    return {
        "routed_model": os.getenv("PLANNER_TEXT_MODEL", "gpt-4o-mini"),
        "api_base": os.getenv("PLANNER_TEXT_API_BASE"),
        "api_key": os.getenv("PLANNER_TEXT_API_KEY"),
        "temperature": float(os.getenv("PLANNER_TEXT_TEMPERATURE", "0.1")),
        "max_tokens": int(os.getenv("PLANNER_TEXT_MAX_TOKENS", "200")),
    }


def get_confidence_threshold() -> float:
    """Minimum confidence required to finalize an inferred user level."""

    return float(os.getenv("PLANNER_LEVEL_CONFIDENCE_THRESHOLD", "0.75"))


def get_bootstrap_servers() -> str:
    """Kafka bootstrap servers for the planner producer/consumer."""

    return os.getenv("PLANNER_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
