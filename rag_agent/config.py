"""Runtime configuration for LLM, VLM, and embedding models."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for a LiteLLM model call."""

    model: str
    api_base: str | None = None
    api_key: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1200


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


def get_text_llm_config() -> LLMConfig:
    """Build text model config from environment variables."""

    return LLMConfig(
        model=os.getenv("RAG_TEXT_MODEL", "gpt-4o-mini"),
        api_base=os.getenv("RAG_TEXT_API_BASE"),
        api_key=os.getenv("RAG_TEXT_API_KEY"),
        temperature=_read_float("RAG_TEXT_TEMPERATURE", 0.2),
        max_tokens=_read_int("RAG_TEXT_MAX_TOKENS", 1800),
    )


def get_vlm_config() -> LLMConfig:
    """Build vision model config from environment variables."""

    return LLMConfig(
        model=os.getenv("RAG_VLM_MODEL", "gpt-4o-mini"),
        api_base=os.getenv("RAG_VLM_API_BASE"),
        api_key=os.getenv("RAG_VLM_API_KEY"),
        temperature=_read_float("RAG_VLM_TEMPERATURE", 0.1),
        max_tokens=_read_int("RAG_VLM_MAX_TOKENS", 600),
    )


def get_embedding_model_name() -> str:
    """Return embedding model name from environment."""

    return os.getenv("RAG_EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
