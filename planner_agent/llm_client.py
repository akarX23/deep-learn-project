"""Planner-local LiteLLM wrapper.

Kept independent from ``rag_agent`` so the planner owns its own LLM
configuration surface (see FR-015). Mirrors the minimal call pattern used
elsewhere in the codebase.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def call_llm(messages: list[dict[str, str]], config: dict[str, object]) -> str:
    """Execute a LiteLLM chat completion and return the text content."""

    from litellm import completion

    kwargs: dict[str, object] = {
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

    response = completion(**kwargs)
    return response.choices[0].message.content or ""
