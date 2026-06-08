# Feature Specification: RAG Retrieval Agent

**Feature Branch**: `[001-build-rag-retrieval-agent]`  
**Created**: 2026-05-27  
**Status**: Draft  
**Input**: User description: "Implement the RAG/Retrieval Agent for a multi-agent AI Tutor application, scoped to this agent only."

## Clarifications

### Session 2026-06-08

- Q: How should the fitz document lifecycle be modeled for one-time initialization across page processing? → A: Keep an in-memory dict of file path to fitz.Document on the RAGAgent instance for a single invocation, outside serializable graph state.
- Q: How should .env.local be structured across agents? → A: Use one global .env.local with comment-based section headers per agent plus a shared section for variables used by all agents.
- Q: How should requirements be structured across agents? → A: Use one requirements.txt with comment-based sections for shared dependencies and each agent (RAG, Planner, Teaching).
- Q: What should be the batching scope for vision model image-description calls? → A: Batch images per page, preserve image order, and keep page association; apply VLM_BATCH_SIZE within each page.
- Q: How should retained_content be handled in extracted_pages output? → A: Exclude retained_content from output payloads to avoid bloating extracted_pages; keep compiled_material as the only final assembled text output.
- Q: How should LiteLLM provider keys be configured for text, VLM, and embedding models? → A: Use separate provider env vars for each modality and default each provider to hosted_vllm.

### Session 2026-06-08 (Post-Implementation Refinement)

- Q: How should fitz document handles be typed for type-safety? → A: Import fitz.Document type and use it in type hints (e.g., dict[str, fitz.Document]) for explicit type safety in agent state management.
- Q: Should the embedding model be local or remote? → A: Use remote LiteLLM-backed embedding API as primary path for consistency with existing text/VLM LiteLLM configuration pattern.
- Q: What environment variables should configure remote embedding? → A: Use RAG_EMBEDDING_MODEL, RAG_EMBEDDING_API_BASE, RAG_EMBEDDING_API_KEY, and RAG_EMBEDDING_MAX_TOKENS to parallel the text and VLM configuration structure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract Relevant PDF Content (Priority: P1)

As a Planner Agent workflow, I need the RAG Agent to process uploaded PDFs page by page and keep only content relevant to the study prompt so downstream teaching receives focused material.

**Why this priority**: Without reliable extraction and relevance filtering, no useful study material can be produced.

**Independent Test**: Can be fully tested by providing a valid input payload with one sample PDF and verifying page-level extraction records, relevance scores, and inclusion/skipping behavior.

**Acceptance Scenarios**:

1. **Given** a valid request with one or more PDF paths and a study prompt, **When** processing runs, **Then** every page in each reachable PDF is evaluated and logged in page audit output.
2. **Given** extracted page content with relevance below threshold, **When** scoring is applied, **Then** that page is marked SKIPPED_IRRELEVANT and excluded from compiled material.
3. **Given** a page that cannot be extracted or has no usable content, **When** extraction is attempted, **Then** the page is marked FAILED_EXTRACTION and processing continues.

---

### User Story 2 - Compile Study Material for Teaching (Priority: P2)

As a Planner Agent workflow, I need one coherent Markdown study document from retained pages so it can be forwarded to the Teaching Agent without additional transformation.

**Why this priority**: The compiled document is the primary payload consumed by downstream tutoring behavior.

**Independent Test**: Can be tested by running the full agent with a realistic prompt and verifying non-empty Markdown output containing organized sections and retained supporting content.

**Acceptance Scenarios**:

1. **Given** at least one retained page, **When** final compilation runs, **Then** the output contains a single non-empty Markdown document with coherent section headings.
2. **Given** retained tables and image descriptions, **When** compilation runs, **Then** tabular and image-derived information is preserved in the final Markdown content.

---

### User Story 3 - Return Contract-Safe Status and Audit (Priority: P3)

As the Planner Agent integration point, I need schema-valid output with completion status and error reporting so I can decide whether to proceed, retry, or fail fast.

**Why this priority**: Planner orchestration depends on explicit status and page-level audit details.

**Independent Test**: Can be tested by mixing valid and invalid file paths and verifying status, error list population, and mirrored request metadata in the output schema.

**Acceptance Scenarios**:

1. **Given** one valid PDF and one missing path, **When** processing completes, **Then** status is partial and non-fatal errors are reported.
2. **Given** all files are unreadable, **When** processing cannot produce any successful extraction, **Then** status is failed and a fatal exception or failed-state behavior is raised consistently.
3. **Given** a successful request, **When** output is returned, **Then** request_id, user_prompt, and schema_version are mirrored from input.
4. **Given** successful page extraction, **When** output is returned, **Then** extracted_pages includes audit metadata only and omits retained page text content.

---

### Edge Cases

- One or more file paths do not exist.
- A file exists but has zero readable pages.
- A page contains images only and little or no text.
- A page contains text but no tables or images.
- Relevance threshold is set to 1.0, causing all pages to be skipped as irrelevant.
- Table extraction succeeds on some pages and fails on others in the same file.
- Image description generation fails for one image while other page extraction succeeds.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a RAG Agent input payload containing request metadata, prompt, file paths, and extraction options.
- **FR-002**: The system MUST process each provided PDF page by page and attempt extraction without requiring Planner or Teaching Agent runtime participation.
- **FR-003**: The system MUST maintain strict scope to the RAG Agent and shared schema updates only.
- **FR-004**: The system MUST produce page-level extraction audit entries containing file name, page number, relevance score, extraction status, OCR usage flag, and per-page errors.
- **FR-005**: The system MUST support three page extraction statuses: SUCCESS, SKIPPED_IRRELEVANT, and FAILED_EXTRACTION.
- **FR-006**: The system MUST score assembled page content against the user prompt and skip pages below the provided relevance threshold.
- **FR-007**: The system MUST compile retained content into a single Markdown document intended as primary study material input for downstream teaching.
- **FR-008**: The system MUST preserve relevant textual content and include extracted table and image-derived information when requested by input flags.
- **FR-009**: The system MUST return output metadata that mirrors request_id, user_prompt, and schema_version from input.
- **FR-010**: The system MUST return aggregate counters for total pages processed and total pages included.
- **FR-011**: The system MUST report non-fatal errors in an errors list and continue processing remaining files/pages when possible.
- **FR-012**: The system MUST return status as complete, partial, or failed, where partial indicates mixed success and failed indicates no usable completion path.
- **FR-013**: The system MUST perform image understanding calls in one or more batches per page (bounded by VLM_BATCH_SIZE) and exactly one final compilation call after all pages have been processed.
- **FR-014**: The system MUST expose extraction, assembly, scoring, prompt, configuration, and LLM client responsibilities through the requested module/file structure.
- **FR-015**: The system MUST provide standalone test inputs including at least one sample PDF and a valid serialized sample input payload.
- **FR-016**: The system MUST include automated tests that cover page counting, text/table/image extraction behavior, table serialization, relevance scoring high/low cases, schema-valid full-run output, partial failure handling, and strict relevance-threshold filtering.
- **FR-017**: The system MUST define UX consistency requirements, including stable Markdown formatting conventions, predictable section organization, and clear labeling of retained study content.
- **FR-018**: The system MUST define measurable performance requirements for synchronous processing, including per-request completion and graceful handling under expected document sizes.
- **FR-019**: The system MUST load each source PDF document once per request and reuse that in-memory document handle across page-level extraction to avoid repeated document re-open operations.
- **FR-020**: The system MUST keep runtime-only document handles outside serializable LangGraph state and manage their lifecycle within the request execution boundary.
- **FR-021**: The system MUST define one project-level .env.local that includes a shared section and distinct agent-specific sections for configuration variables.
- **FR-022**: The system MUST define one project-level requirements.txt with comment-based sections for shared dependencies and agent-specific dependencies (RAG, Planner, Teaching).
- **FR-023**: The system MUST support batched image-description calls with batch size controlled by VLM_BATCH_SIZE and process batches within page boundaries while preserving image order.
- **FR-024**: The system MUST support a configurable image-description instruction prompt that combines a general image-analysis directive with the request user_prompt context.
- **FR-025**: The system MUST omit retained_content from extracted_pages in RAGAgentOutput; compiled_material is the only final text artifact returned in the response payload.
- **FR-026**: The system MUST organize imports at the top of each file in grouped blocks with line breaks separating standard-library imports, third-party library imports, and project-local imports.
- **FR-027**: The system MUST define fitz.Document type hints explicitly (e.g., dict[str, fitz.Document]) for document handle storage to ensure type-safety in static analysis and IDE support.
- **FR-028**: The system MUST support remote embedding via LiteLLM API calls as the primary embedding source, replacing local sentence-transformers for consistency with text and vision model configuration patterns.
- **FR-029**: The system MUST provide separate provider environment variables `RAG_TEXT_PROVIDER`, `RAG_VLM_PROVIDER`, and `RAG_EMBEDDING_PROVIDER` in .env.local, each defaulting to `hosted_vllm`.
- **FR-030**: The system MUST include provider values in LiteLLM configuration so model routing uses `<provider>/<model>` composition for text, VLM, and embedding calls.
- **FR-031**: The system MUST provide `RAG_TEXT_MODEL`, `RAG_TEXT_API_BASE`, `RAG_TEXT_API_KEY`, `RAG_VLM_MODEL`, `RAG_VLM_API_BASE`, `RAG_VLM_API_KEY`, `RAG_EMBEDDING_MODEL`, `RAG_EMBEDDING_API_BASE`, `RAG_EMBEDDING_API_KEY`, and `RAG_EMBEDDING_MAX_TOKENS` in .env.local to configure modality-specific LiteLLM endpoints and credentials.

### Key Entities *(include if feature involves data)*

- **RAGAgentInput**: Request contract containing request_id, user_prompt, file_paths, include_tables, include_images, relevance_threshold, and schema_version.
- **RAGAgentOutput**: Response contract containing mirrored metadata, compiled_material, extracted_pages audit list, aggregate counters, errors, and final status.
- **ExtractedPage**: Per-page audit record with source file reference, page number, relevance score, extraction status, OCR usage flag, and page-specific errors; excludes retained page text content in output.
- **PageExtractionStatus**: Enum defining SUCCESS, SKIPPED_IRRELEVANT, and FAILED_EXTRACTION.
- **Retained Page Content (Internal)**: Assembled page-level textual representation (text, table content, image descriptions) used internally for compilation but not returned in extracted_pages.
- **Document Handle (fitz.Document)**: Opened PyMuPDF document instance with explicit fitz.Document type hint for type-safety; stored in dict[str, fitz.Document] and reused across page-level extraction within a single request lifecycle.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid requests return schema-valid output matching the defined RAGAgentOutput contract.
- **SC-002**: For requests with at least one relevant page, compiled_material is non-empty in at least 99% of successful or partial runs.
- **SC-003**: For mixed-validity file lists (at least one valid and one invalid path), status is partial and errors is non-empty in 100% of runs.
- **SC-004**: With relevance_threshold set to 1.0, total_pages_included equals 0 and all processed pages are marked SKIPPED_IRRELEVANT in 100% of runs.
- **SC-005**: Generated study documents follow a consistent Markdown structure with section headings and preserved retained content in 100% of successful runs.
- **SC-006**: Processing of a representative 5-10 page sample PDF completes synchronously within acceptable local development runtime, with no fatal crash on single-page extraction failures.

## Assumptions

- Input files are PDFs and non-PDF formats are out of scope for this feature.
- PDFs are primarily text-based for initial delivery; OCR is not required in this version.
- Empty text on a page is recorded as FAILED_EXTRACTION and does not terminate the request.
- Planner Agent and Teaching Agent behavior, orchestration, and prompt logic are out of scope.
- Output artifact format is always Markdown.
- The current branch remains unchanged for this specification task per user instruction.
- The remote embedding API (configured via RAG_EMBEDDING_API_BASE and RAG_EMBEDDING_API_KEY) is available and operational at runtime; no local fallback model is required.
- LiteLLM provider defaults are `hosted_vllm` for text, VLM, and embedding unless explicitly overridden via modality-specific provider environment variables.
- fitz.Document type is available from the pymupdf package and can be imported directly for type annotations.
