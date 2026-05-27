# Data Model: RAG Retrieval Agent

## Entities

### RAGAgentInput
- Description: Request payload received by the RAG agent.
- Fields:
  - request_id: str (UUID string)
  - user_prompt: str
  - file_paths: list[str]
  - include_tables: bool (default true)
  - include_images: bool (default true)
  - relevance_threshold: float (default 0.6)
  - schema_version: str (default "1.0")
- Validation rules:
  - request_id must be a valid UUID string.
  - file_paths must be non-empty.
  - relevance_threshold must be in [0.0, 1.0].
  - schema_version must be non-empty.

### PageExtractionStatus (Enum)
- Description: Per-page extraction outcome.
- Allowed values:
  - SUCCESS
  - SKIPPED_IRRELEVANT
  - FAILED_EXTRACTION

### ExtractedPage
- Description: Audit record for one processed page.
- Fields:
  - file_name: str
  - page_number: int (1-based)
  - relevance_score: float
  - status: PageExtractionStatus
  - ocr_used: bool (always false in v1)
  - errors: list[str]
  - retained_content: str | None
- Validation rules:
  - page_number must be >= 1.
  - relevance_score must be in [0.0, 1.0].
  - retained_content must be present when status is SUCCESS.

### RAGAgentOutput
- Description: Agent response contract returned to Planner.
- Fields:
  - request_id: str (mirrored)
  - user_prompt: str (mirrored)
  - schema_version: str (mirrored)
  - compiled_material: str
  - extracted_pages: list[ExtractedPage]
  - total_pages_processed: int
  - total_pages_included: int
  - errors: list[str]
  - status: str (complete | partial | failed)
- Validation rules:
  - total_pages_processed >= total_pages_included >= 0.
  - status is complete only if no unrecoverable extraction gap and at least one included page.
  - status is partial when mixed success/failure occurs with usable output.
  - status is failed when no usable output can be produced.

## Relationships
- One RAGAgentInput maps to one RAGAgentOutput.
- One RAGAgentOutput contains zero or more ExtractedPage records.
- Each ExtractedPage has exactly one PageExtractionStatus.

## State Transitions

### Request-level state
1. received -> processing_pages
2. processing_pages -> compiling_material (if retained pages > 0)
3. processing_pages -> failed (if no pages can be processed and no usable content)
4. compiling_material -> complete (all target files/pages processed with usable output and no blocking errors)
5. compiling_material -> partial (usable output with non-fatal errors)
6. any state -> failed (fatal exception path)

### Page-level state
1. started -> FAILED_EXTRACTION (if extraction returns empty/invalid content and no recoverable content path)
2. started -> SKIPPED_IRRELEVANT (if relevance score < threshold)
3. started -> SUCCESS (if assembled content is valid and relevance score >= threshold)

## Derived Fields
- total_pages_processed: count of all attempted page records.
- total_pages_included: count of ExtractedPage where status == SUCCESS.
- compiled_material context: built from retained_content across SUCCESS pages only.
