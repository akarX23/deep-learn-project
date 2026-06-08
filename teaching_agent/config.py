"""Runtime configuration for the Teaching Agent LLM calls."""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # loads .env from project root automatically

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
    "beginner": 512,
    "intermediate": 1024,
    "advanced": 2048,
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
