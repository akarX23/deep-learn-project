"""LiteLLM wrapper for all model calls."""

from __future__ import annotations

from typing import Any

from rag_agent.config import LLMConfig


def call_llm(messages: list[dict[str, Any]], config: LLMConfig) -> str:
    """Execute a LiteLLM chat completion and return text content."""

    # Prevent accidental remote calls with missing credentials during local/offline runs.
    if not config.api_base and not config.api_key:
        raise RuntimeError(
            "No api_base or api_key configured for model call. "
            "Set environment variables or provide a local model endpoint."
        )

    try:
        from litellm import completion
    except Exception as exc:
        raise RuntimeError("LiteLLM is required for model calls") from exc

    kwargs: dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    if config.api_base:
        kwargs["api_base"] = config.api_base
    if config.api_key:
        kwargs["api_key"] = config.api_key

    response = completion(**kwargs)
    return response.choices[0].message.content or ""
