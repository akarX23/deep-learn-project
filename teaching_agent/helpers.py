"""Pure deterministic helpers for the Teaching Agent pipeline."""

from __future__ import annotations

import re
from typing import Any

from project.schemas import (
    OutputMode,
    TeachingAgentOutput,
    TeachingMetadata,
)


_SECTION_HEADER_RE = re.compile(r"^\*\*(\w+)\*\*\s*$", re.MULTILINE | re.IGNORECASE)


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
