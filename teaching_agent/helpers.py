"""Pure deterministic helpers for the Teaching Agent pipeline."""

from __future__ import annotations

import json
import re
from typing import Any

from project.schemas import (
    OutputMode,
    TeachingAgentOutput,
    TeachingMetadata,
)


# Matches the opening fence line (```json or ```) at the start of a response.
_JSON_FENCE_OPEN_RE = re.compile(r"^```(?:json)?\s*\n", re.MULTILINE)


def build_messages(prompt: str) -> list[dict[str, str]]:
    """Wrap a rendered prompt string into the LiteLLM messages format."""
    return [{"role": "user", "content": prompt}]


def parse_llm_response(
    raw: str, required_fields: tuple[str, ...] = ("explanation", "notes")
) -> dict[str, Any]:
    """Extract and parse the JSON object from the LLM's raw text response.

    The LLM is instructed to return bare JSON, but may occasionally wrap it
    in markdown fences. This function strips fences before parsing.

    Returns:
        Parsed dict. Each name in `required_fields` must be present and a
        non-empty string (default 'explanation'/'notes' for generation and
        revision; pass () for critique responses, which are validated by the
        ReflectionCritique model instead).

    Raises:
        ValueError: If the response cannot be parsed or required fields are missing.
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned an empty response")

    text = raw.strip()

    # Strip markdown fences only when the entire response is fence-wrapped
    # (i.e. the response starts with ``` or ```json). Strip the opening fence
    # line, then find the LAST ``` as the closing delimiter so that triple-
    # backtick code blocks inside JSON string values (e.g. in 'example') do
    # not prematurely terminate the match.
    if text.startswith("```"):
        open_match = _JSON_FENCE_OPEN_RE.match(text)
        if open_match:
            body = text[open_match.end():]
            close_pos = body.rfind("```")
            text = (body[:close_pos] if close_pos != -1 else body).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON is not an object")

    # Each required field must be present and a non-empty string.
    for required_field in required_fields:
        if required_field not in parsed:
            raise ValueError(f"LLM response missing required field: '{required_field}'")
        if not isinstance(parsed[required_field], str) or not parsed[required_field].strip():
            raise ValueError(f"LLM response field '{required_field}' must be a non-empty string")

    return parsed


def build_error_output(topic: str, output_mode: str, model: str) -> TeachingAgentOutput:
    """Build a schema-valid error TeachingAgentOutput.

    Used on any failure path (input validation, LLM call failure, JSON parse failure).
    content is always null; tokens_used is always 0.
    """
    return TeachingAgentOutput(
        status="error",
        output_mode=OutputMode(output_mode),
        content=None,
        metadata=TeachingMetadata(
            topic=topic,
            tokens_used=0,
            model=model,
        ),
    )
