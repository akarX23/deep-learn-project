"""Simplified LLM and embedding call wrappers for the RAG agent."""

from __future__ import annotations

import logging
from typing import Any

from rag_agent.utils.helpers import EmbeddingConfig, LLMConfig

logger = logging.getLogger(__name__)


def call_llm(messages: list[dict[str, Any]], config: LLMConfig) -> str:
    """Execute a LiteLLM chat completion and return text content."""

    # TODO: Add credential validation guard (check api_base / api_key present)
    # TODO: Handle missing litellm gracefully with a clear error message

    from litellm import completion

    kwargs: dict[str, Any] = {
        "model": config.routed_model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    if config.api_base:
        kwargs["api_base"] = config.api_base
    if config.api_key:
        kwargs["api_key"] = config.api_key

    # TODO: Validate response format before returning
    response = completion(**kwargs)
    return response.choices[0].message.content or ""


def call_embedding(text: str, config: EmbeddingConfig) -> list[float]:
    """Execute a LiteLLM embedding call and return embedding vector."""

    # TODO: Add credential validation guard (check api_base / api_key present)
    # TODO: Handle missing litellm gracefully with a clear error message

    from litellm import embedding

    kwargs: dict[str, Any] = {
        "model": config.routed_model,
        "input": text,
    }
    if config.api_base:
        kwargs["api_base"] = config.api_base
    if config.api_key:
        kwargs["api_key"] = config.api_key

    # TODO: Validate response format before returning
    response = embedding(**kwargs)
    return response["data"][0]["embedding"]
