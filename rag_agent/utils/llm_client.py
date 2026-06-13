"""Simplified LLM and embedding call wrappers for the RAG agent."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def call_llm(messages: list[dict[str, Any]], config: dict[str, object]) -> str:
    """Execute a LiteLLM chat completion and return text content."""

    # TODO: Add credential validation guard (check api_base / api_key present)
    # TODO: Handle missing litellm gracefully with a clear error message

    from litellm import completion

    kwargs: dict[str, Any] = {
        "model": str(config.get("routed_model", "")),
        "messages": messages,
        "temperature": config.get("temperature"),
        "max_tokens": config.get("max_tokens"),
    }
    api_base = config.get("api_base")
    api_key = config.get("api_key")
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    # TODO: Validate response format before returning
    response = completion(**kwargs)
    return response.choices[0].message.content or ""


def call_embedding(text: str, config: dict[str, object]) -> list[float]:
    """Execute a LiteLLM embedding call and return embedding vector."""

    # TODO: Add credential validation guard (check api_base / api_key present)
    # TODO: Handle missing litellm gracefully with a clear error message

    from litellm import embedding

    kwargs: dict[str, Any] = {
        "model": str(config.get("routed_model", "")),
        "input": text,
    }
    api_base = config.get("api_base")
    api_key = config.get("api_key")
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    # TODO: Validate response format before returning
    response = embedding(**kwargs)
    return response["data"][0]["embedding"]
