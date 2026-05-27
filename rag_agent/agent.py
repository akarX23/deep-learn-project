"""RAG agent orchestration with LangGraph-driven page processing."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from project.schemas import ExtractedPage, PageExtractionStatus, RAGAgentInput, RAGAgentOutput
from rag_agent.config import get_embedding_model_name, get_text_llm_config, get_vlm_config
from rag_agent.helpers import assemble_page_content, build_compilation_context
from rag_agent.llm_client import call_llm
from rag_agent.prompts import MATERIAL_COMPILATION_PROMPT
from rag_agent.tools import (
    describe_image_with_vlm,
    extract_images_from_page,
    extract_tables_from_page,
    extract_text_from_page,
    get_page_count,
    score_page_relevance,
)


@dataclass
class PagePointer:
    """Represents a single file/page unit of work."""

    file_path: str
    file_name: str
    page_number: int


class AgentState(TypedDict):
    """Mutable state flowing through the LangGraph execution."""

    request: RAGAgentInput
    pointers: list[PagePointer]
    index: int
    extracted_pages: list[ExtractedPage]
    retained_pages: list[ExtractedPage]
    errors: list[str]


class _FallbackEmbeddingModel:
    """Small deterministic embedding fallback for offline/dev scenarios."""

    _vocab = [
        "gradient",
        "descent",
        "optimizer",
        "learning",
        "rate",
        "loss",
        "model",
        "epoch",
    ]

    def encode(self, sentences: list[str], normalize_embeddings: bool = False) -> list[list[float]]:
        vectors: list[list[float]] = []
        for sentence in sentences:
            text = sentence.lower()
            vectors.append([float(token in text) for token in self._vocab])
        return vectors


class RAGAgent:
    """Retrieval agent that extracts and compiles topic-relevant study material."""

    def __init__(self) -> None:
        self.text_llm_config = get_text_llm_config()
        self.vlm_config = get_vlm_config()
        self.embedding_model = self._load_embedding_model()
        self._graph = self._build_graph()

    @staticmethod
    def _load_embedding_model() -> Any:
        try:
            from sentence_transformers import SentenceTransformer
            return SentenceTransformer(get_embedding_model_name(), local_files_only=True)
        except Exception:
            # Keep the agent usable in offline/local environments.
            return _FallbackEmbeddingModel()

    def _build_graph(self):
        try:
            from langgraph.graph import END, StateGraph
        except Exception as exc:
            raise RuntimeError("langgraph is required") from exc

        graph = StateGraph(AgentState)
        graph.add_node("process_page", self._process_next_page)
        graph.add_conditional_edges(
            "process_page",
            self._should_continue,
            {
                "continue": "process_page",
                "end": END,
            },
        )
        graph.set_entry_point("process_page")
        return graph.compile()

    def _build_page_pointers(self, request: RAGAgentInput) -> tuple[list[PagePointer], list[str]]:
        pointers: list[PagePointer] = []
        errors: list[str] = []
        for file_path in request.file_paths:
            try:
                total = get_page_count(file_path)
            except Exception as exc:
                errors.append(f"{file_path}: {exc}")
                continue
            for page_num in range(1, total + 1):
                pointers.append(
                    PagePointer(
                        file_path=file_path,
                        file_name=Path(file_path).name,
                        page_number=page_num,
                    )
                )
        return pointers, errors

    def _should_continue(self, state: AgentState) -> str:
        if state["index"] < len(state["pointers"]):
            return "continue"
        return "end"

    def _process_next_page(self, state: AgentState) -> AgentState:
        pointer = state["pointers"][state["index"]]
        request = state["request"]

        errors: list[str] = []
        text = ""
        tables: list[str] = []
        image_descriptions: list[str] = []

        try:
            text = extract_text_from_page(pointer.file_path, pointer.page_number)
            if request.include_tables:
                tables = extract_tables_from_page(pointer.file_path, pointer.page_number)
            if request.include_images:
                for image in extract_images_from_page(pointer.file_path, pointer.page_number):
                    image_descriptions.append(
                        describe_image_with_vlm(image, request.user_prompt, self.vlm_config)
                    )
        except Exception as exc:
            errors.append(str(exc))

        assembled = assemble_page_content(text, tables, image_descriptions)
        relevance = score_page_relevance(assembled, request.user_prompt, self.embedding_model)

        page_status = PageExtractionStatus.SUCCESS
        retained_content: str | None = assembled

        if not assembled.strip():
            page_status = PageExtractionStatus.FAILED_EXTRACTION
            retained_content = None
            if not errors:
                errors.append("No extractable content found on page")
        elif relevance < request.relevance_threshold:
            page_status = PageExtractionStatus.SKIPPED_IRRELEVANT
            retained_content = None

        page_result = ExtractedPage(
            file_name=pointer.file_name,
            page_number=pointer.page_number,
            relevance_score=relevance,
            status=page_status,
            ocr_used=False,
            errors=errors,
            retained_content=retained_content,
        )

        state["extracted_pages"].append(page_result)
        if page_result.status == PageExtractionStatus.SUCCESS and page_result.retained_content:
            state["retained_pages"].append(page_result)

        if errors:
            state["errors"].extend(
                f"{pointer.file_name}:page:{pointer.page_number}: {err}" for err in errors
            )

        state["index"] += 1
        return state

    def _compile_material(self, request: RAGAgentInput, retained_pages: list[ExtractedPage]) -> str:
        context = build_compilation_context(retained_pages)
        if not context.strip():
            return ""

        prompt = MATERIAL_COMPILATION_PROMPT.format(
            user_prompt=request.user_prompt,
            context=context,
        )
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        try:
            compiled = call_llm(messages, self.text_llm_config).strip()
            if compiled:
                return compiled
        except Exception:
            # Fall back to deterministic markdown output if model call is unavailable.
            pass
        return "# Study Material\n\n" + context

    @staticmethod
    def _derive_status(
        pointers: list[PagePointer], retained_pages: list[ExtractedPage], errors: list[str]
    ) -> str:
        if not pointers:
            return "failed"
        if retained_pages and errors:
            return "partial"
        if retained_pages:
            return "complete"
        return "failed"

    def run(self, payload: RAGAgentInput) -> RAGAgentOutput:
        """Run the end-to-end retrieval and compilation pipeline."""

        pointers, initial_errors = self._build_page_pointers(payload)
        state: AgentState = {
            "request": payload,
            "pointers": pointers,
            "index": 0,
            "extracted_pages": [],
            "retained_pages": [],
            "errors": initial_errors,
        }
        final_state = self._graph.invoke(state)

        compiled_material = self._compile_material(payload, final_state["retained_pages"])
        status = self._derive_status(
            final_state["pointers"],
            final_state["retained_pages"],
            final_state["errors"],
        )
        if status != "failed" and not compiled_material.strip() and final_state["retained_pages"]:
            status = "partial"

        return RAGAgentOutput(
            request_id=payload.request_id,
            user_prompt=payload.user_prompt,
            schema_version=payload.schema_version,
            compiled_material=compiled_material,
            extracted_pages=final_state["extracted_pages"],
            total_pages_processed=len(final_state["extracted_pages"]),
            total_pages_included=len(final_state["retained_pages"]),
            errors=final_state["errors"],
            status=status,
        )


def _parse_input(path: str) -> RAGAgentInput:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return RAGAgentInput.model_validate(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RAG retrieval agent")
    parser.add_argument("--input", required=True, help="Path to a JSON RAGAgentInput file")
    args = parser.parse_args()

    payload = _parse_input(args.input)
    agent = RAGAgent()
    output = agent.run(payload)
    print(output.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
