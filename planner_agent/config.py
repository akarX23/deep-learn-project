"""Environment-driven configuration for the planner agent.

The planner owns its own LLM configuration surface (``PLANNER_TEXT_*``) and does
not reuse rag_agent runtime configuration (FR-015).
"""

from __future__ import annotations

import os
import dotenv

DOTENV_PATH = ".env.local"

dotenv.load_dotenv(dotenv_path=DOTENV_PATH, override=False)


def _build_routed_model(provider: str, model: str) -> str:
    """Build a provider-routed model string used by LiteLLM."""

    return f"{provider.strip()}/{model.strip()}"


def get_llm_config() -> dict[str, object]:
    """Build the LLM config for level/quiz inference from environment variables."""

    provider = os.getenv("PLANNER_TEXT_PROVIDER", "hosted_vllm")
    model = os.getenv("PLANNER_TEXT_MODEL", "gpt-4o-mini")
    return {
        "provider": provider,
        "model": model,
        "routed_model": _build_routed_model(provider, model),
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
