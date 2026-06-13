"""Test suite for RAG retrieval agent behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project.schemas import PageExtractionStatus, RAGAgentInput, RAGAgentOutput
from rag_agent.agent import RAGAgent
from rag_agent.utils.content_helpers import serialize_table_to_markdown
from rag_agent.utils.helpers import build_routed_model, get_text_llm_config
from rag_agent.utils.llm_client import call_embedding, call_llm
from rag_agent.utils.tools import (
    extract_images_from_page,
    extract_tables_from_page,
    extract_text_from_page,
    get_page_count,
    score_page_relevance,
)


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


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAG_EMBEDDING_MODEL", "test-embedding-model")
    monkeypatch.setenv("RAG_EMBEDDING_API_BASE", "http://localhost:8000/v1")


def test_build_routed_model():
    assert build_routed_model("hosted_vllm", "qwen3") == "hosted_vllm/qwen3"


def test_get_text_llm_config_provider_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RAG_TEXT_PROVIDER", raising=False)
    monkeypatch.setenv("RAG_TEXT_MODEL", "my-model")
    cfg = get_text_llm_config()
    assert cfg["provider"] == "hosted_vllm"
    assert cfg["routed_model"] == "hosted_vllm/my-model"


def test_get_text_llm_config_custom_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAG_TEXT_PROVIDER", "openai")
    monkeypatch.setenv("RAG_TEXT_MODEL", "gpt-4o-mini")
    cfg = get_text_llm_config()
    assert cfg["provider"] == "openai"
    assert cfg["routed_model"] == "openai/gpt-4o-mini"


def test_call_llm_uses_routed_model(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, str] = {}

    class _Msg:
        content = "ok"

    class _Choice:
        message = _Msg()

    class _Response:
        choices = [_Choice()]

    def _completion(**kwargs):
        captured["model"] = kwargs["model"]
        return _Response()

    import types
    import sys

    monkeypatch.setitem(
        sys.modules, "litellm", types.SimpleNamespace(completion=_completion)
    )

    cfg = {
        "model": "model-x",
        "provider": "hosted_vllm",
        "routed_model": "hosted_vllm/model-x",
        "api_base": "http://localhost:8000/v1",
        "api_key": None,
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    text = call_llm([{"role": "user", "content": "hello"}], cfg)
    assert text == "ok"
    assert captured["model"] == "hosted_vllm/model-x"


def test_call_embedding_uses_routed_model(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, str] = {}

    def _embedding(**kwargs):
        captured["model"] = kwargs["model"]
        return {"data": [{"embedding": [1.0, 0.0, 0.0]}]}

    import types
    import sys

    monkeypatch.setitem(
        sys.modules, "litellm", types.SimpleNamespace(embedding=_embedding)
    )

    cfg = {
        "model": "embed-x",
        "provider": "hosted_vllm",
        "routed_model": "hosted_vllm/embed-x",
        "api_base": "http://localhost:8000/v1",
        "api_key": None,
    }
    vec = call_embedding("abc", cfg)
    assert vec == [1.0, 0.0, 0.0]
    assert captured["model"] == "hosted_vllm/embed-x"


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
    matrix = [
        ["Topic", "Definition"],
        ["Gradient", "First derivative"],
        ["Descent", "Optimization step"],
    ]
    markdown = serialize_table_to_markdown(matrix)

    assert "| Topic | Definition |" in markdown
    assert "| --- | --- |" in markdown
    assert "| Gradient | First derivative |" in markdown


def test_score_page_relevance_high(monkeypatch: pytest.MonkeyPatch):
    vectors = {
        "content": [0.9, 0.9, 0.1],
        "prompt": [0.8, 0.8, 0.2],
    }

    def _mock_call_embedding(text: str, config: dict[str, object]):
        if "gradient" in text.lower():
            return vectors["content"]
        return vectors["prompt"]

    monkeypatch.setattr("rag_agent.utils.tools.call_embedding", _mock_call_embedding)
    cfg = {
        "model": "m",
        "provider": "hosted_vllm",
        "routed_model": "hosted_vllm/m",
        "api_base": "http://localhost:8000/v1",
        "api_key": None,
    }
    score = score_page_relevance(
        "Gradient descent is an optimizer that minimizes loss.",
        "Teach me gradient descent optimization fundamentals.",
        cfg,
    )
    assert score > 0.5


def test_score_page_relevance_low(monkeypatch: pytest.MonkeyPatch):
    def _mock_call_embedding(text: str, config: dict[str, object]):
        if "gradient" in text.lower():
            return [1.0, 0.0, 0.0]
        return [0.0, 1.0, 0.0]

    monkeypatch.setattr("rag_agent.utils.tools.call_embedding", _mock_call_embedding)
    cfg = {
        "model": "m",
        "provider": "hosted_vllm",
        "routed_model": "hosted_vllm/m",
        "api_base": "http://localhost:8000/v1",
        "api_key": None,
    }
    score = score_page_relevance(
        "Photosynthesis in plants depends on chlorophyll and sunlight.",
        "Teach me gradient descent optimization fundamentals.",
        cfg,
    )
    assert score < 0.3


def test_rag_agent_one_time_document_open(
    monkeypatch: pytest.MonkeyPatch, sample_input_data: dict
):
    open_calls = {"count": 0}
    from rag_agent.utils import tools as tools_mod

    real_open_pdf = tools_mod.open_pdf

    def _counted_open(file_path: str):
        open_calls["count"] += 1
        return real_open_pdf(file_path)

    monkeypatch.setattr("rag_agent.utils.tools.open_pdf", _counted_open)
    monkeypatch.setattr(
        "rag_agent.agent.call_llm", lambda messages, config: "# Compiled"
    )
    monkeypatch.setattr(
        "rag_agent.utils.tools.call_llm", lambda messages, config: "Image summary"
    )

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(sample_input_data)
    output = agent.run(payload)

    assert isinstance(output, RAGAgentOutput)
    assert open_calls["count"] == 1


def test_rag_agent_single_final_compilation_call(
    monkeypatch: pytest.MonkeyPatch, sample_input_data: dict
):
    calls = {"compile": 0}

    def _mock_compile(messages, config):
        calls["compile"] += 1
        return "# Compiled\n\nOrganized notes"

    monkeypatch.setattr("rag_agent.agent.call_llm", _mock_compile)
    monkeypatch.setattr(
        "rag_agent.utils.tools.call_llm", lambda messages, config: "Image summary"
    )

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(sample_input_data)
    _ = agent.run(payload)

    assert calls["compile"] == 1


def test_rag_agent_output_schema(
    monkeypatch: pytest.MonkeyPatch, sample_input_data: dict
):
    monkeypatch.setattr(
        "rag_agent.agent.call_llm",
        lambda messages, config: "# Compiled\n\nOrganized notes",
    )
    monkeypatch.setattr(
        "rag_agent.utils.tools.call_llm",
        lambda messages, config: "Diagram shows optimization trajectory",
    )

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(sample_input_data)
    output = agent.run(payload)

    assert isinstance(output, RAGAgentOutput)
    assert output.status in {"complete", "partial"}
    assert output.compiled_material.strip()
    assert output.total_pages_included >= 0


def test_rag_agent_partial_failure(
    monkeypatch: pytest.MonkeyPatch, sample_input_data: dict
):
    monkeypatch.setattr(
        "rag_agent.agent.call_llm",
        lambda messages, config: "# Compiled\n\nOrganized notes",
    )
    monkeypatch.setattr(
        "rag_agent.utils.tools.call_llm", lambda messages, config: "Image summary"
    )

    payload_data = dict(sample_input_data)
    payload_data["file_paths"] = [
        sample_input_data["file_paths"][0],
        "rag_agent/tests/inputs/missing.pdf",
    ]

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(payload_data)
    output = agent.run(payload)

    assert output.status == "partial"
    assert output.errors


def test_failed_extraction_continues_processing(
    monkeypatch: pytest.MonkeyPatch, sample_input_data: dict
):
    monkeypatch.setattr(
        "rag_agent.agent.call_llm",
        lambda messages, config: "# Compiled\n\nOrganized notes",
    )
    monkeypatch.setattr(
        "rag_agent.utils.tools.call_llm", lambda messages, config: "Image summary"
    )

    from rag_agent.utils import tools as tools_mod

    original_extract_text = tools_mod.extract_text_from_page

    def _extract_with_one_failure(pdf_source, page_number: int) -> str:
        if page_number == 1:
            raise RuntimeError("synthetic extraction failure")
        return original_extract_text(pdf_source, page_number)

    monkeypatch.setattr(
        "rag_agent.utils.tools.extract_text_from_page", _extract_with_one_failure
    )

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(sample_input_data)
    output = agent.run(payload)

    assert output.total_pages_processed == 6
    assert any(
        page.status == PageExtractionStatus.FAILED_EXTRACTION
        for page in output.extracted_pages
    )


def test_compiled_material_retains_table_and_image_context(
    monkeypatch: pytest.MonkeyPatch, sample_input_data: dict
):
    # Force fallback markdown to verify retained context is preserved in compiled output.
    monkeypatch.setattr("rag_agent.agent.call_llm", lambda messages, config: "")
    monkeypatch.setattr(
        "rag_agent.utils.tools.call_llm", lambda messages, config: "Image summary"
    )

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(sample_input_data)
    output = agent.run(payload)

    assert "Image Notes:" in output.compiled_material
    assert "|" in output.compiled_material


def test_relevance_threshold_filtering(
    monkeypatch: pytest.MonkeyPatch, sample_input_data: dict
):
    monkeypatch.setattr(
        "rag_agent.agent.call_llm",
        lambda messages, config: "# Compiled\n\nOrganized notes",
    )
    monkeypatch.setattr(
        "rag_agent.utils.tools.call_llm", lambda messages, config: "Image summary"
    )

    payload_data = dict(sample_input_data)
    payload_data["relevance_threshold"] = 1.0

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(payload_data)
    output = agent.run(payload)

    assert output.total_pages_included == 0
    assert output.extracted_pages
    assert all(
        page.status == PageExtractionStatus.SKIPPED_IRRELEVANT
        for page in output.extracted_pages
    )


def test_output_mirrors_request_metadata(
    monkeypatch: pytest.MonkeyPatch, sample_input_data: dict
):
    monkeypatch.setattr(
        "rag_agent.agent.call_llm",
        lambda messages, config: "# Compiled\n\nOrganized notes",
    )
    monkeypatch.setattr(
        "rag_agent.utils.tools.call_llm", lambda messages, config: "Image summary"
    )

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(sample_input_data)
    output = agent.run(payload)

    assert output.request_id == payload.request_id
    assert output.user_prompt == payload.user_prompt
    assert output.schema_version == payload.schema_version


def test_extracted_pages_are_audit_only(
    monkeypatch: pytest.MonkeyPatch, sample_input_data: dict
):
    monkeypatch.setattr(
        "rag_agent.agent.call_llm",
        lambda messages, config: "# Compiled\n\nOrganized notes",
    )
    monkeypatch.setattr(
        "rag_agent.utils.tools.call_llm", lambda messages, config: "Image summary"
    )

    agent = RAGAgent()
    payload = RAGAgentInput.model_validate(sample_input_data)
    output = agent.run(payload)

    assert output.extracted_pages
    for page in output.extracted_pages:
        dumped = page.model_dump()
        assert "retained_content" not in dumped
