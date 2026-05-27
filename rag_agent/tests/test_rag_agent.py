"""Test suite for RAG retrieval agent behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project.schemas import PageExtractionStatus, RAGAgentInput, RAGAgentOutput
from rag_agent.agent import RAGAgent
from rag_agent.helpers import serialize_table_to_markdown
from rag_agent.tools import (
    extract_images_from_page,
    extract_tables_from_page,
    extract_text_from_page,
    get_page_count,
    score_page_relevance,
)


class _MockEmbeddingModel:
    def encode(self, sentences, normalize_embeddings=False):
        vectors = []
        for sentence in sentences:
            text = sentence.lower()
            vectors.append(
                [
                    float("gradient" in text),
                    float("descent" in text),
                    float("optimizer" in text),
                    float("photosynthesis" in text),
                    float("chlorophyll" in text),
                    float("plant" in text),
                ]
            )
        return vectors


@pytest.fixture(scope="session")
def inputs_dir() -> Path:
    return Path(__file__).parent / "inputs"


@pytest.fixture(scope="session")
def sample_pdf_path(inputs_dir: Path) -> Path:
    return inputs_dir / "sample.pdf"


@pytest.fixture(scope="session")
def sample_input_data(inputs_dir: Path) -> dict:
    with open(inputs_dir / "sample_input.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_get_page_count(sample_pdf_path: Path):
    assert get_page_count(str(sample_pdf_path)) == 6


def test_extract_text_from_page(sample_pdf_path: Path):
    text = extract_text_from_page(str(sample_pdf_path), 1)
    assert isinstance(text, str)
    assert text.strip()


def test_extract_tables_from_page(sample_pdf_path: Path):
    with_tables = extract_tables_from_page(str(sample_pdf_path), 2)
    without_tables = extract_tables_from_page(str(sample_pdf_path), 1)

    assert isinstance(with_tables, list)
    assert with_tables
    assert all(table.startswith("| ") for table in with_tables)
    assert without_tables == []


def test_extract_images_from_page(sample_pdf_path: Path):
    with_images = extract_images_from_page(str(sample_pdf_path), 3)
    without_images = extract_images_from_page(str(sample_pdf_path), 1)

    assert isinstance(with_images, list)
    assert with_images
    assert all(isinstance(blob, bytes) and blob for blob in with_images)
    assert without_images == []


def test_serialize_table_to_markdown():
    matrix = [["Topic", "Definition"], ["Gradient", "First derivative"], ["Descent", "Optimization step"]]
    markdown = serialize_table_to_markdown(matrix)

    assert "| Topic | Definition |" in markdown
    assert "| --- | --- |" in markdown
    assert "| Gradient | First derivative |" in markdown


def test_score_page_relevance_high():
    model = _MockEmbeddingModel()
    content = "Gradient descent is an optimizer that minimizes loss."
    prompt = "Teach me gradient descent optimization fundamentals."
    assert score_page_relevance(content, prompt, model) > 0.5


def test_score_page_relevance_low():
    model = _MockEmbeddingModel()
    content = "Photosynthesis in plants depends on chlorophyll and sunlight."
    prompt = "Teach me gradient descent optimization fundamentals."
    assert score_page_relevance(content, prompt, model) < 0.3


def test_rag_agent_output_schema(monkeypatch, sample_input_data: dict):
    monkeypatch.setattr("rag_agent.agent.call_llm", lambda messages, config: "# Compiled\n\nOrganized notes")
    monkeypatch.setattr(
        "rag_agent.tools.call_llm",
        lambda messages, config: "Diagram shows optimization trajectory",
    )

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(sample_input_data)
    output = agent.run(payload)

    assert isinstance(output, RAGAgentOutput)
    assert output.status in {"complete", "partial"}
    assert output.compiled_material.strip()
    assert output.total_pages_included > 0


def test_rag_agent_partial_failure(monkeypatch, sample_input_data: dict):
    monkeypatch.setattr("rag_agent.agent.call_llm", lambda messages, config: "# Compiled\n\nOrganized notes")
    monkeypatch.setattr(
        "rag_agent.tools.call_llm",
        lambda messages, config: "Image summary",
    )

    payload_data = dict(sample_input_data)
    payload_data["file_paths"] = [sample_input_data["file_paths"][0], "rag_agent/tests/inputs/missing.pdf"]

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(payload_data)
    output = agent.run(payload)

    assert output.status == "partial"
    assert output.errors


def test_relevance_threshold_filtering(monkeypatch, sample_input_data: dict):
    monkeypatch.setattr("rag_agent.agent.call_llm", lambda messages, config: "# Compiled\n\nOrganized notes")
    monkeypatch.setattr(
        "rag_agent.tools.call_llm",
        lambda messages, config: "Image summary",
    )

    payload_data = dict(sample_input_data)
    payload_data["relevance_threshold"] = 1.0

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(payload_data)
    output = agent.run(payload)

    assert output.total_pages_included == 0
    assert output.extracted_pages
    assert all(page.status == PageExtractionStatus.SKIPPED_IRRELEVANT for page in output.extracted_pages)
