"""Pure helper utilities for table formatting and context assembly."""

from __future__ import annotations

from math import sqrt
from typing import Any, Iterable


def serialize_table_to_markdown(table_matrix: list[list[object]]) -> str:
    """Convert a 2D table matrix to a markdown table."""

    if not table_matrix:
        return ""
    rows = [["" if cell is None else str(cell).strip() for cell in row] for row in table_matrix]
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else []
    sep = ["---"] * len(header)

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in body:
        padded = row + [""] * max(0, len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(lines)


def assemble_page_content(text: str, tables: list[str], image_descriptions: list[str]) -> str:
    """Assemble text, tables, and image descriptions for one page."""

    sections: list[str] = []
    if text and text.strip():
        sections.append(text.strip())
    if tables:
        sections.append("\n\n".join(t for t in tables if t.strip()))
    if image_descriptions:
        image_block = "\n".join(f"- {item.strip()}" for item in image_descriptions if item.strip())
        if image_block:
            sections.append("Image Notes:\n" + image_block)
    return "\n\n".join(section for section in sections if section.strip())


def build_compilation_context(retained_pages: list[dict[str, Any]]) -> str:
    """Build labeled context text from retained pages for final compilation."""

    chunks: list[str] = []
    for page in retained_pages:
        content = str(page.get("content", "")).strip()
        if not content:
            continue
        file_name = str(page.get("file_name", "unknown"))
        page_number = int(page.get("page_number", 0))
        relevance_score = float(page.get("relevance_score", 0.0))
        chunks.append(
            f"### Source: {file_name} | Page {page_number} | Score {relevance_score:.3f}\n"
            f"{content}"
        )
    return "\n\n".join(chunks)


def cosine_similarity(vec_a: Iterable[float], vec_b: Iterable[float]) -> float:
    """Compute cosine similarity without external math dependencies."""

    a = list(vec_a)
    b = list(vec_b)
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))
