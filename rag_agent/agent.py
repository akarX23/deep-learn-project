"""RAG agent orchestration with deterministic bounded parallel page processing."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import logging

from project.schemas import (
    ExtractedPage,
    PageExtractionStatus,
    RAGAgentInput,
    RAGAgentOutput,
)
from rag_agent.utils.content_helpers import (
    assemble_page_content,
    build_compilation_context,
)
from rag_agent.utils.helpers import (
    get_embedding_config,
    get_page_parallelism,
    get_text_llm_config,
    get_vlm_config,
)
from rag_agent.utils.llm_client import call_llm
from rag_agent.utils.prompts import MATERIAL_COMPILATION_PROMPT
from rag_agent.utils import tools as rag_tools

logger = logging.getLogger(__name__)


@dataclass
class PagePointer:
    """Represents a single file/page unit of work."""

    file_path: str
    file_name: str
    page_number: int


@dataclass
class PageTaskResult:
    """Result payload for one independently processed page."""

    pointer_order: int
    page: ExtractedPage
    retained_payload: dict[str, Any] | None
    failed_reason: str | None


class RAGAgent:
    """Retrieval agent that extracts and compiles topic-relevant study material."""

    def __init__(self) -> None:
        self.text_llm_config = None
        self.vlm_config = None
        self.vlm_batch_size = 1
        self.embedding_config = None
        self.page_parallelism = 4

    def _build_page_pointers(
        self, request: RAGAgentInput
    ) -> tuple[list[PagePointer], list[str]]:
        pointers: list[PagePointer] = []
        errors: list[str] = []
        # TODO: Add optional page-range and file-level include/exclude controls.
        for file_path in request.file_paths:
            try:
                total = int(rag_tools.get_page_count(file_path))
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

    def _process_pointer(
        self,
        pointer: PagePointer,
        pointer_order: int,
        request: RAGAgentInput,
    ) -> PageTaskResult:
        def _failed(reason: str) -> PageTaskResult:
            return PageTaskResult(
                pointer_order=pointer_order,
                page=ExtractedPage(
                    file_name=pointer.file_name,
                    page_number=pointer.page_number,
                    relevance_score=0.0,
                    status=PageExtractionStatus.FAILED_EXTRACTION,
                    ocr_used=False,
                    errors=[reason],
                ),
                retained_payload=None,
                failed_reason=reason,
            )

        try:
            with rag_tools.open_pdf(pointer.file_path) as document:
                text = rag_tools.extract_text_from_page(document, pointer.page_number)
                tables: list[str] = []
                if request.include_tables:
                    tables = rag_tools.extract_tables_from_page(
                        document, pointer.page_number
                    )
                image_descriptions: list[str] = []
                if request.include_images:
                    images = rag_tools.extract_images_from_page(
                        document, pointer.page_number
                    )
                    image_descriptions = rag_tools.describe_images_with_vlm(
                        images,
                        request.user_prompt,
                        self.vlm_config,
                        self.vlm_batch_size,
                    )
            assembled = assemble_page_content(text, tables, image_descriptions).strip()
            if not assembled:
                return _failed("No extractable content found on page")

            relevance = rag_tools.score_page_relevance(
                assembled, request.user_prompt, self.embedding_config
            )
        except Exception as exc:
            return _failed(str(exc))

        page_status = PageExtractionStatus.SUCCESS
        if relevance < request.relevance_threshold:
            page_status = PageExtractionStatus.SKIPPED_IRRELEVANT

        page_result = ExtractedPage(
            file_name=pointer.file_name,
            page_number=pointer.page_number,
            relevance_score=relevance,
            status=page_status,
            ocr_used=False,
            errors=[],
        )

        retained_payload: dict[str, Any] | None = None
        if page_result.status == PageExtractionStatus.SUCCESS:
            retained_payload = {
                "file_name": pointer.file_name,
                "page_number": pointer.page_number,
                "relevance_score": 0.0,
                "content": assembled,
            }

        return PageTaskResult(
            pointer_order=pointer_order,
            page=page_result,
            retained_payload=retained_payload,
            failed_reason=None,
        )

    def _process_pages(
        self,
        request: RAGAgentInput,
        pointers: list[PagePointer],
    ) -> list[PageTaskResult]:
        if not pointers:
            return []

        results: list[PageTaskResult] = []
        with ThreadPoolExecutor(max_workers=self.page_parallelism) as pool:
            future_map = {}
            for idx, pointer in enumerate(pointers):
                logger.info(
                    "page_dispatched request_id=%s file=%s page=%d pointer_order=%d",
                    request.request_id,
                    pointer.file_name,
                    pointer.page_number,
                    idx,
                )
                future = pool.submit(self._process_pointer, pointer, idx, request)
                future_map[future] = (idx, pointer)

            for future in as_completed(future_map):
                idx, pointer = future_map[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result.page.status == PageExtractionStatus.FAILED_EXTRACTION:
                        reason = result.failed_reason or "Page processing failed"
                        logger.warning(
                            "page_failed request_id=%s file=%s page=%d reason=%s",
                            request.request_id,
                            pointer.file_name,
                            pointer.page_number,
                            reason,
                        )
                    else:
                        logger.info(
                            "page_processed request_id=%s file=%s page=%d status=%s",
                            request.request_id,
                            pointer.file_name,
                            pointer.page_number,
                            result.page.status.value,
                        )
                except Exception as exc:
                    reason = str(exc)
                    logger.warning(
                        "page_failed request_id=%s file=%s page=%d reason=%s",
                        request.request_id,
                        pointer.file_name,
                        pointer.page_number,
                        reason,
                    )
                    results.append(
                        PageTaskResult(
                            pointer_order=idx,
                            page=ExtractedPage(
                                file_name=pointer.file_name,
                                page_number=pointer.page_number,
                                relevance_score=0.0,
                                status=PageExtractionStatus.FAILED_EXTRACTION,
                                ocr_used=False,
                                errors=[reason],
                            ),
                            retained_payload=None,
                            failed_reason=reason,
                        )
                    )
        return results

    def _reduce_page_results(
        self,
        request_id: str,
        pointers: list[PagePointer],
        page_results: list[PageTaskResult],
        base_errors: list[str],
    ) -> tuple[list[ExtractedPage], list[dict[str, Any]], list[str]]:
        ordered = sorted(page_results, key=lambda item: item.pointer_order)

        extracted_pages: list[ExtractedPage] = []
        retained_pages: list[dict[str, Any]] = []
        errors = list(base_errors)
        failed_count = 0

        for item in ordered:
            if item.page.status == PageExtractionStatus.FAILED_EXTRACTION:
                pointer = pointers[item.pointer_order]
                reason = item.failed_reason or "Page processing failed"
                errors.append(
                    f"{pointer.file_name}:page:{pointer.page_number}: {reason}"
                )
                failed_count += 1
                continue

            extracted_pages.append(item.page)
            if item.retained_payload is not None:
                retained_pages.append(item.retained_payload)

        logger.info(
            "state_reduced request_id=%s processed=%d included=%d failed=%d",
            request_id,
            len(extracted_pages),
            len(retained_pages),
            failed_count,
        )
        return extracted_pages, retained_pages, errors

    def _compile_material(
        self, request: RAGAgentInput, retained_pages: list[dict[str, Any]]
    ) -> str:
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
            # TODO: Add explicit LLM error taxonomy and retry strategy.
            # Fall back to deterministic markdown output if model call is unavailable.
            pass
        return "# Study Material\n\n" + context

    @staticmethod
    def _derive_status(
        pointers: list[PagePointer],
        retained_pages: list[dict[str, Any]],
        errors: list[str],
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
        self.vlm_batch_size = self.vlm_config.get("batch_size", 1)
        self.embedding_config = get_embedding_config()
        self.page_parallelism = max(1, get_page_parallelism())

        pointers, pointer_errors = self._build_page_pointers(payload)
        page_results = self._process_pages(payload, pointers)
        extracted_pages, retained_pages, errors = self._reduce_page_results(
            payload.request_id,
            pointers,
            page_results,
            pointer_errors,
        )

        compiled_material = self._compile_material(payload, retained_pages)
        status = self._derive_status(
            pointers,
            retained_pages,
            errors,
        )
        if status != "failed" and not compiled_material.strip() and retained_pages:
            status = "partial"

        return RAGAgentOutput(
            request_id=payload.request_id,
            user_prompt=payload.user_prompt,
            schema_version=payload.schema_version,
            compiled_material=compiled_material,
            extracted_pages=extracted_pages,
            total_pages_processed=len(extracted_pages),
            total_pages_included=len(retained_pages),
            errors=errors[:10],
            status=status,
        )


def _parse_input(path: str) -> RAGAgentInput:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return RAGAgentInput.model_validate(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the RAG retrieval agent")
    parser.add_argument(
        "--input", required=True, help="Path to a JSON RAGAgentInput file"
    )
    args = parser.parse_args()

    payload = _parse_input(args.input)
    agent = RAGAgent()
    output = agent.run(payload)
    print(output.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
