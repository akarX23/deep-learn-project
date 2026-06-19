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


_SECTION_HEADER_RE = re.compile(r"^\*\*(\w+)\*\*\s*$", re.MULTILINE | re.IGNORECASE)

# Opening markdown fence (```json or ```) at the very start of a fenced response.
_JSON_FENCE_OPEN_RE = re.compile(r"^```(?:json)?\s*\n", re.MULTILINE)


def build_messages(prompt: str) -> list[dict[str, str]]:
    """Wrap a rendered prompt string into the LiteLLM messages format."""
    return [{"role": "user", "content": prompt}]


def parse_markdown_response(raw: str) -> dict[str, Any]:
    """Parse a markdown bold-header LLM response into a field dict.

    Splits on **SectionName** headers (case-insensitive, must be on their own line).
    Returns dict with keys: explanation, diagram, notes, example.

    Raises:
        ValueError: If the response is empty or 'explanation'/'notes' sections are absent/empty.
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned an empty response")

    # re.split with a capturing group interleaves [pre, name, content, name, content, ...]
    parts = _SECTION_HEADER_RE.split(raw.strip())

    sections: dict[str, str] = {}
    i = 1  # skip parts[0] (text before first header)
    while i + 1 < len(parts):
        sections[parts[i].lower()] = parts[i + 1].strip()
        i += 2

    for required in ("explanation", "notes"):
        if not sections.get(required):
            raise ValueError(f"LLM response missing required section: '{required}'")

    return {
        "explanation": sections["explanation"],
        "diagram": sections.get("diagram") or None,
        "notes": sections["notes"],
        "example": sections.get("example") or None,
    }


def parse_llm_response(
    raw: str, required_fields: tuple[str, ...] = ("explanation", "notes")
) -> dict[str, Any]:
    """Extract and parse a JSON object from an LLM response.

    Generation now streams markdown (see ``parse_markdown_response``); this JSON
    parser is retained for the reflection loop, whose critique and revision calls
    return JSON. Strips a surrounding ```json fence if present.

    Each name in ``required_fields`` must be present and a non-empty string
    (default 'explanation'/'notes'; pass () for critique responses, which are
    validated by the ReflectionCritique model instead).

    Raises:
        ValueError: If the response cannot be parsed or a required field is missing.
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned an empty response")

    text = raw.strip()
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
