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

# Characters that break the Mermaid renderer when unquoted inside node labels.
_SPECIAL_LABEL_CHARS: frozenset[str] = frozenset(':(){}#%÷×≤≥≠')

# Matches square-bracket node labels: A[text] or A[text with spaces].
# Does not span newlines so subgraph lines are not accidentally captured.
_NODE_LABEL_RE = re.compile(r'\[([^\[\]\n]+)\]')


def sanitize_mermaid_labels(diagram: str) -> str:
    """Wrap unquoted Mermaid node labels that contain special characters in double quotes.

    Fixes diagrams where the LLM emits labels like A[Start: Step] which break the
    Mermaid renderer. Already-quoted labels (A["text"]) are left untouched.
    Literal double-quote characters inside a label are escaped as &quot;.
    """
    def _quote_if_needed(match: re.Match) -> str:
        inner = match.group(1)
        if inner.startswith('"') and inner.endswith('"'):
            return match.group(0)
        if any(c in inner for c in _SPECIAL_LABEL_CHARS):
            escaped = inner.replace('"', '&quot;')
            return f'["{escaped}"]'
        return match.group(0)

    return _NODE_LABEL_RE.sub(_quote_if_needed, diagram)


def build_messages(
    prompt: str, chat_history: list[dict] | None = None
) -> list[dict[str, str]]:
    """Wrap a rendered prompt into the LiteLLM messages format.

    Phase 5: when ``chat_history`` (prior turns, oldest->newest) is provided it is
    prepended, so the current structured prompt is the final user message.
    ``None``/``[]`` returns a single user message — identical to the single-turn
    pipeline, keeping existing callers byte-for-byte unchanged.
    """
    return [*(chat_history or []), {"role": "user", "content": prompt}]


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
