"""RAG agent orchestration with LangGraph-driven page processing."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

import fitz

from project.schemas import ExtractedPage, PageExtractionStatus, RAGAgentInput, RAGAgentOutput
from rag_agent.config import (
    get_embedding_config,
    get_text_llm_config,
    get_vlm_batch_size,
    get_vlm_config,
)
from rag_agent.helpers import assemble_page_content, build_compilation_context
from rag_agent.llm_client import call_llm
from rag_agent.prompts import MATERIAL_COMPILATION_PROMPT
from rag_agent.tools import (
    describe_images_with_vlm,
    extract_images_from_page,
    extract_tables_from_page,
    extract_text_from_page,
    open_pdf,
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
    retained_pages: list[dict[str, Any]]
    errors: list[str]


class RAGAgent:
    """Retrieval agent that extracts and compiles topic-relevant study material."""

    def __init__(self) -> None:
        self.text_llm_config = None
        self.vlm_config = None
        self.vlm_batch_size = 1
        self.embedding_config = None
        self._open_docs: dict[str, fitz.Document] = {}
        self._graph = self._build_graph()

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
            document = self._open_docs.get(file_path)
            if document is None:
                errors.append(f"{file_path}: document not available")
                continue
            total = int(document.page_count)
            for page_num in range(1, total + 1):
                pointers.append(
                    PagePointer(
                        file_path=file_path,
                        file_name=Path(file_path).name,
                        page_number=page_num,
                    )
                )
        return pointers, errors

    def _open_documents(self, file_paths: list[str]) -> list[str]:
        errors: list[str] = []
        self._open_docs = {}
        for file_path in file_paths:
            if file_path in self._open_docs:
                continue
            try:
                self._open_docs[file_path] = open_pdf(file_path)
            except Exception as exc:
                errors.append(f"{file_path}: {exc}")
        return errors

    def _close_documents(self) -> None:
        for document in self._open_docs.values():
            try:
                document.close()
            except Exception:
                continue
        self._open_docs = {}

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
        document = self._open_docs.get(pointer.file_path)

        if document is None:
            errors.append("Document handle unavailable")
        else:
            try:
                text = extract_text_from_page(document, pointer.page_number)
                if request.include_tables:
                    tables = extract_tables_from_page(document, pointer.page_number)
                if request.include_images:
                    images = extract_images_from_page(document, pointer.page_number)
                    image_descriptions = describe_images_with_vlm(
                        images,
                        request.user_prompt,
                        self.vlm_config,
                        self.vlm_batch_size,
                    )
            except Exception as exc:
                errors.append(str(exc))

        assembled = assemble_page_content(text, tables, image_descriptions)
        relevance = score_page_relevance(assembled, request.user_prompt, self.embedding_config)

        page_status = PageExtractionStatus.SUCCESS

        if not assembled.strip():
            page_status = PageExtractionStatus.FAILED_EXTRACTION
            if not errors:
                errors.append("No extractable content found on page")
        elif relevance < request.relevance_threshold:
            page_status = PageExtractionStatus.SKIPPED_IRRELEVANT

        page_result = ExtractedPage(
            file_name=pointer.file_name,
            page_number=pointer.page_number,
            relevance_score=relevance,
            status=page_status,
            ocr_used=False,
            errors=errors,
        )

        state["extracted_pages"].append(page_result)
        if page_result.status == PageExtractionStatus.SUCCESS and assembled.strip():
            state["retained_pages"].append(
                {
                    "file_name": pointer.file_name,
                    "page_number": pointer.page_number,
                    "relevance_score": relevance,
                    "content": assembled.strip(),
                }
            )

        if errors:
            state["errors"].extend(
                f"{pointer.file_name}:page:{pointer.page_number}: {err}" for err in errors
            )

        state["index"] += 1
        return state

    def _compile_material(self, request: RAGAgentInput, retained_pages: list[dict[str, Any]]) -> str:
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
        pointers: list[PagePointer], retained_pages: list[dict[str, Any]], errors: list[str]
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

        # Load runtime config once per request execution.
        self.text_llm_config = get_text_llm_config()
        self.vlm_config = get_vlm_config()
        self.vlm_batch_size = get_vlm_batch_size()
        self.embedding_config = get_embedding_config()

        initial_errors = self._open_documents(payload.file_paths)
        pointers, pointer_errors = self._build_page_pointers(payload)
        state: AgentState = {
            "request": payload,
            "pointers": pointers,
            "index": 0,
            "extracted_pages": [],
            "retained_pages": [],
            "errors": initial_errors + pointer_errors,
        }
        try:
            final_state = self._graph.invoke(state)
        finally:
            self._close_documents()

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
