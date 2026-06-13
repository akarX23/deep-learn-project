"""Stateless tool functions for page-wise PDF extraction and relevance scoring."""

from __future__ import annotations

import base64
import contextlib
import io
from pathlib import Path
from typing import Any

from rag_agent.utils.content_helpers import (
    cosine_similarity,
    serialize_table_to_markdown,
)
from rag_agent.utils.llm_client import call_embedding, call_llm
from rag_agent.utils.prompts import IMAGE_DESCRIPTION_PROMPT


def open_pdf(file_path: str):
    """Open a PDF document from disk."""

    try:
        import fitz
    except Exception as exc:
        raise RuntimeError("PyMuPDF is required for PDF extraction") from exc

    pdf_path = Path(file_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    return fitz.open(str(pdf_path))


def _page_from_source(pdf_source: Any, page_number: int):
    if page_number < 1:
        raise ValueError("page_number must be >= 1")
    return pdf_source.load_page(page_number - 1)


def _with_optional_open(pdf_source: Any):
    if isinstance(pdf_source, str):
        return open_pdf(pdf_source)
    return contextlib.nullcontext(pdf_source)


def get_page_count(file_path: str) -> int:
    """Return the total page count for a PDF file."""

    with open_pdf(file_path) as doc:
        return doc.page_count


def extract_text_from_page(pdf_source: Any, page_number: int) -> str:
    """Extract plain text from a single page (1-based index)."""

    with _with_optional_open(pdf_source) as doc:
        page = _page_from_source(doc, page_number)
        return page.get_text("text").strip()


def extract_tables_from_page(pdf_source: Any, page_number: int) -> list[str]:
    """Extract tables from a page and return markdown-serialized table strings."""

    with _with_optional_open(pdf_source) as doc:
        page = _page_from_source(doc, page_number)
        with contextlib.redirect_stdout(io.StringIO()):
            tables = page.find_tables()
        serialized: list[str] = []
        for table in tables.tables:
            data = table.extract() or []
            markdown = serialize_table_to_markdown(data)
            if markdown:
                serialized.append(markdown)
        return serialized


def extract_images_from_page(pdf_source: Any, page_number: int) -> list[bytes]:
    """Extract embedded image bytes from a single page."""

    with _with_optional_open(pdf_source) as doc:
        page = _page_from_source(doc, page_number)
        images: list[bytes] = []
        for image_ref in page.get_images(full=True):
            xref = image_ref[0]
            image_obj = doc.extract_image(xref)
            image_bytes = image_obj.get("image")
            if image_bytes:
                images.append(image_bytes)
        return images


def describe_images_with_vlm(
    image_bytes_list: list[bytes],
    user_prompt: str,
    llm_config: dict[str, object],
    batch_size: int,
) -> list[str]:
    """Describe images using page-scoped VLM batch calls."""

    if not image_bytes_list:
        return []

    safe_batch_size = max(1, batch_size)
    prompt = IMAGE_DESCRIPTION_PROMPT.format(user_prompt=user_prompt)

    descriptions: list[str] = []
    for start in range(0, len(image_bytes_list), safe_batch_size):
        batch = image_bytes_list[start : start + safe_batch_size]
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image_bytes in batch:
            image_b64 = base64.b64encode(image_bytes).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                }
            )

        messages: list[dict[str, Any]] = [{"role": "user", "content": content}]
        try:
            description = call_llm(messages, llm_config).strip()
            if description:
                descriptions.append(description)
        except Exception as exc:
            # Non-fatal behavior keeps page processing moving.
            descriptions.append(f"Image description unavailable: {exc}")

    return descriptions


def describe_image_with_vlm(
    image_bytes: bytes,
    user_prompt: str,
    llm_config: dict[str, object],
) -> str:
    """Backward-compatible single-image wrapper around batched image descriptions."""

    if not image_bytes:
        return ""

    descriptions = describe_images_with_vlm(
        [image_bytes], user_prompt, llm_config, batch_size=1
    )
    return descriptions[0] if descriptions else ""


def score_page_relevance(
    page_content: str,
    user_prompt: str,
    embedding_config: dict[str, object],
) -> float:
    """Score semantic relevance between page content and user prompt via remote embedding API."""

    if not page_content.strip() or not user_prompt.strip():
        return 0.0

    try:
        content_vector = call_embedding(page_content, embedding_config)
        prompt_vector = call_embedding(user_prompt, embedding_config)
        score = cosine_similarity(content_vector, prompt_vector)
        return max(0.0, min(1.0, float(score)))
    except Exception as exc:
        # Log error and return neutral score (non-fatal)
        import warnings

        warnings.warn(f"Embedding API call failed: {exc}. Returning neutral score.")
        return 0.6
