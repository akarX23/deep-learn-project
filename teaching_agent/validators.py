"""Mermaid diagram structural validator."""

from __future__ import annotations

import re

# Recognized Mermaid diagram type keywords (first non-empty line of the diagram).
_MERMAID_HEADER_RE = re.compile(
    r"^\s*(graph\s+(TD|LR|TB|RL|BT)|flowchart\s+(TD|LR|TB|RL|BT)|"
    r"sequenceDiagram|classDiagram|stateDiagram(-v2)?|"
    r"erDiagram|pie|mindmap|timeline)\b",
    re.IGNORECASE,
)


def validate_mermaid(diagram: str) -> bool:
    """Return True if diagram passes structural Mermaid validation.

    Checks:
    1. First non-empty line matches a recognized Mermaid diagram type keyword.
    2. At least one additional non-empty line follows (diagram has content).

    This is a lightweight structural check, not a full Mermaid parse.
    A structurally valid but semantically broken diagram may still pass —
    that is an accepted v1 limitation per research.md Decision 6.
    """
    if not diagram or not diagram.strip():
        return False

    lines = [line for line in diagram.splitlines() if line.strip()]
    if len(lines) < 2:
        return False

    if not _MERMAID_HEADER_RE.match(lines[0]):
        return False

    return True
