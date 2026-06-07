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


# Matches an optional ```json or ``` fence wrapping the LLM response.
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def build_messages(prompt: str) -> list[dict[str, str]]:
    """Wrap a rendered prompt string into the LiteLLM messages format."""
    return [{"role": "user", "content": prompt}]


def parse_llm_response(raw: str) -> dict[str, Any]:
    """Extract and parse the JSON object from the LLM's raw text response.

    The LLM is instructed to return bare JSON, but may occasionally wrap it
    in markdown fences. This function strips fences before parsing.

    Returns:
        Parsed dict containing at least 'explanation' and 'notes'.

    Raises:
        ValueError: If the response cannot be parsed or required fields are missing.
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned an empty response")

    text = raw.strip()

    # Strip markdown fences only when the entire response is fence-wrapped
    # (i.e. the response starts with ```). Using match() rather than search()
    # avoids falsely matching ``` blocks that appear inside JSON string values
    # (e.g. a code example in the 'example' field).
    if text.startswith("```"):
        fence_match = _JSON_FENCE_RE.match(text)
        if fence_match:
            text = fence_match.group(1).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON is not an object")

    # 'explanation' and 'notes' are always required; diagram and example may be null.
    for required_field in ("explanation", "notes"):
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
