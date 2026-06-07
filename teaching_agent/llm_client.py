"""LiteLLM wrapper for Teaching Agent model calls."""

from __future__ import annotations

from typing import Any

from teaching_agent.config import LLMConfig


def call_llm(messages: list[dict[str, Any]], config: LLMConfig) -> tuple[str, int]:
    """Execute a LiteLLM chat completion and return (content, tokens_used).

    LiteLLM routes to any provider based on the model string in config.
    Provider API keys are read automatically from standard env vars
    (ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, etc.).
    TEACHING_API_KEY / TEACHING_API_BASE are optional overrides.

    Returns:
        content: The model's text response.
        tokens_used: Completion tokens consumed (reported by the provider).

    Raises:
        RuntimeError: If the LiteLLM call fails for any reason.
    """
    try:
        from litellm import completion
    except Exception as exc:
        raise RuntimeError("litellm is required but not installed") from exc

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

    try:
        response = completion(**kwargs)
    except Exception as exc:
        raise RuntimeError(f"LLM call failed: {exc}") from exc

    content = response.choices[0].message.content or ""
    tokens_used = getattr(response.usage, "completion_tokens", 0) or 0
    return content, tokens_used
