"""Thin LiteLLM wrapper for the Quiz Agent.

call_llm(messages, config) -> tuple[str, int]
  Returns (content_str, completion_tokens).
  Raises RuntimeError if neither api_base nor api_key is set (prevents
  accidental remote calls when running offline / in tests without mock).
"""

from __future__ import annotations

from quiz_agent.config import LLMConfig


def call_llm(messages: list[dict[str, str]], config: LLMConfig) -> tuple[str, int]:
    """Call the LLM via LiteLLM and return (response_text, tokens_used).

    Raises:
        RuntimeError: If neither api_base nor api_key is configured.
        RuntimeError: On any LiteLLM / provider error.
    """
    if not config.api_base and not config.api_key:
        raise RuntimeError(
            "Quiz Agent LLM is not configured: set QUIZ_API_BASE or QUIZ_API_KEY "
            "(and QUIZ_MODEL) to make real model calls."
        )

    try:
        import litellm  # type: ignore

        kwargs: dict = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        if config.api_base:
            kwargs["api_base"] = config.api_base
        if config.api_key:
            kwargs["api_key"] = config.api_key

        response = litellm.completion(**kwargs)
        content: str = response.choices[0].message.content or ""
        tokens_used: int = getattr(response.usage, "completion_tokens", 0)
        return content, tokens_used
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"LLM call failed: {exc}") from exc
