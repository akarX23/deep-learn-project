"""Stateless tool functions for page-wise PDF extraction and relevance scoring."""

from __future__ import annotations

import base64
import contextlib
import io
from pathlib import Path
from typing import Any

from rag_agent.config import LLMConfig
from rag_agent.helpers import cosine_similarity, serialize_table_to_markdown
from rag_agent.llm_client import call_llm
from rag_agent.prompts import IMAGE_DESCRIPTION_PROMPT


def _open_pdf(file_path: str):
    try:
        import fitz
    except Exception as exc:
        raise RuntimeError("PyMuPDF is required for PDF extraction") from exc

    pdf_path = Path(file_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    return fitz.open(str(pdf_path))


def get_page_count(file_path: str) -> int:
    """Return the total page count for a PDF file."""

    with _open_pdf(file_path) as doc:
        return doc.page_count


def extract_text_from_page(file_path: str, page_number: int) -> str:
    """Extract plain text from a single page (1-based index)."""

    with _open_pdf(file_path) as doc:
        page = doc.load_page(page_number - 1)
        return page.get_text("text").strip()


def extract_tables_from_page(file_path: str, page_number: int) -> list[str]:
    """Extract tables from a page and return markdown-serialized table strings."""

    with _open_pdf(file_path) as doc:
        page = doc.load_page(page_number - 1)
        with contextlib.redirect_stdout(io.StringIO()):
            tables = page.find_tables()
        serialized: list[str] = []
        for table in tables.tables:
            data = table.extract() or []
            markdown = serialize_table_to_markdown(data)
            if markdown:
                serialized.append(markdown)
        return serialized


def extract_images_from_page(file_path: str, page_number: int) -> list[bytes]:
    """Extract embedded image bytes from a single page."""

    with _open_pdf(file_path) as doc:
        page = doc.load_page(page_number - 1)
        images: list[bytes] = []
        for image_ref in page.get_images(full=True):
            xref = image_ref[0]
            image_obj = doc.extract_image(xref)
            image_bytes = image_obj.get("image")
            if image_bytes:
                images.append(image_bytes)
        return images


def describe_image_with_vlm(image_bytes: bytes, user_prompt: str, llm_config: LLMConfig) -> str:
    """Describe one image in the context of the user's topic via VLM."""

    if not image_bytes:
        return ""

    prompt = IMAGE_DESCRIPTION_PROMPT.format(user_prompt=user_prompt)
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                },
            ],
        }
    ]
    try:
        return call_llm(messages, llm_config).strip()
    except Exception as exc:
        # Non-fatal behavior keeps page processing moving.
        return f"Image description unavailable: {exc}"


def score_page_relevance(page_content: str, user_prompt: str, embedding_model: Any) -> float:
    """Score semantic relevance between page content and user prompt."""

    if not page_content.strip() or not user_prompt.strip():
        return 0.0
    vectors = embedding_model.encode([page_content, user_prompt], normalize_embeddings=False)
    score = cosine_similarity(vectors[0], vectors[1])
    return max(0.0, min(1.0, float(score)))
