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
- Description: Audit record for one processed page. Does not contain assembled page text; that is internal-only.
- Fields:
  - file_name: str
  - page_number: int (1-based)
  - relevance_score: float
  - status: PageExtractionStatus
  - ocr_used: bool (always false in v1)
  - errors: list[str]
- Validation rules:
  - page_number must be >= 1.
  - relevance_score must be in [0.0, 1.0].

### RetainedPageContent (Internal, not in output)
- Description: Assembled per-page text used internally for final compilation only.
- Fields:
  - file_name: str
  - page_number: int
  - content: str

### ModalityLLMConfig (Runtime Config)
- Description: Modality-specific LiteLLM configuration object used for text, VLM, and embedding calls.
- Fields:
  - provider: str (default `hosted_vllm`)
  - model: str
  - api_base: str | None
  - api_key: str | None
  - temperature: float | None
  - max_tokens: int | None
- Derived field:
  - routed_model: str = `<provider>/<model>`
- Validation rules:
  - provider must be non-empty.
  - model must be non-empty.

### RAGRuntimeConfig
- Description: Aggregated runtime config for all model modalities.
- Fields:
  - text: ModalityLLMConfig
  - vlm: ModalityLLMConfig
  - embedding: ModalityLLMConfig
- Env mapping:
  - text.provider <- RAG_TEXT_PROVIDER (default hosted_vllm)
  - vlm.provider <- RAG_VLM_PROVIDER (default hosted_vllm)
  - embedding.provider <- RAG_EMBEDDING_PROVIDER (default hosted_vllm)

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
  - status is complete when successful extraction/compilation occurs without blocking errors.
  - status is partial when mixed success/failure occurs with usable output.
  - status is failed when no usable output can be produced.

## Relationships
- One RAGAgentInput maps to one RAGAgentOutput.
- One RAGAgentOutput contains zero or more ExtractedPage records.
- Each ExtractedPage has exactly one PageExtractionStatus.
- One request execution uses one RAGRuntimeConfig containing three modality configs.

## State Transitions

### Request-level state
1. received -> processing_pages
2. processing_pages -> compiling_material (if retained pages > 0)
3. processing_pages -> failed (if no usable page content exists)
4. compiling_material -> complete (usable compiled output with no blocking error)
5. compiling_material -> partial (usable output plus non-fatal errors)
6. any state -> failed (fatal exception path)

### Page-level state
1. started -> FAILED_EXTRACTION (missing or unusable extraction)
2. started -> SKIPPED_IRRELEVANT (score < threshold)
3. started -> SUCCESS (score >= threshold and retained content available)

## Derived Fields
- total_pages_processed: count of all attempted pages.
- total_pages_included: count of pages with SUCCESS status.
- compiled_material context: built from internal RetainedPageContent records for SUCCESS pages only.
- routed model IDs:
  - text_routed_model = `<RAG_TEXT_PROVIDER>/<RAG_TEXT_MODEL>`
  - vlm_routed_model = `<RAG_VLM_PROVIDER>/<RAG_VLM_MODEL>`
  - embedding_routed_model = `<RAG_EMBEDDING_PROVIDER>/<RAG_EMBEDDING_MODEL>`
