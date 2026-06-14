"""Runtime configuration for the Quiz Agent LLM calls."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class LLMConfig:
    """Provider-agnostic LiteLLM call configuration.

    Set QUIZ_MODEL to any LiteLLM model string.
    Provider API keys are read automatically by LiteLLM from their standard
    env vars (ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, etc.).
    QUIZ_API_KEY / QUIZ_API_BASE are optional overrides for non-standard endpoints.
    """

    model: str
    api_base: str | None = None
    api_key: str | None = None
    temperature: float = 0.2
    max_tokens: int = 3000


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


def get_generation_config() -> LLMConfig:
    """Return LLM config for the question-generation call (max 3000 completion tokens)."""
    model = os.getenv("QUIZ_MODEL", "gpt-4o-mini")
    api_base = os.getenv("QUIZ_API_BASE")
    api_key = os.getenv("QUIZ_API_KEY")
    temperature = _read_float("QUIZ_TEMPERATURE", 0.2)
    max_tokens = _read_int("QUIZ_GENERATION_MAX_TOKENS", 3000)
    return LLMConfig(
        model=model,
        api_base=api_base or None,
        api_key=api_key or None,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_grading_config() -> LLMConfig:
    """Return LLM config for the descriptive-grading call (max 1200 completion tokens)."""
    model = os.getenv("QUIZ_MODEL", "gpt-4o-mini")
    api_base = os.getenv("QUIZ_API_BASE")
    api_key = os.getenv("QUIZ_API_KEY")
    temperature = _read_float("QUIZ_TEMPERATURE", 0.1)
    max_tokens = _read_int("QUIZ_GRADING_MAX_TOKENS", 1200)
    return LLMConfig(
        model=model,
        api_base=api_base or None,
        api_key=api_key or None,
        temperature=temperature,
        max_tokens=max_tokens,
    )
