# Data Model: RAG Agent Parallel Page Processing

## Entities

### RAGRequestEvent
- Description: Incoming Kafka payload consumed from topic `rag`.
- Fields:
  - `request_id`: str
  - `session_ctx`: dict[str, object]
  - `user_request`: str
  - `file_paths`: list[str]
  - `created_at`: str | None
  - `source`: str | None

### PagePointer
- Description: Unit of per-page work derived from input documents.
- Fields:
  - `file_path`: str
  - `file_name`: str
  - `page_number`: int (1-based)
- Validation rules:
  - `page_number >= 1`
  - Derived only from opened document page counts.

### PageTaskResult
- Description: Per-page output produced by independent page processing.
- Fields:
  - `page`: `ExtractedPage`
  - `retained_payload`: dict[str, object] | None
  - `errors`: list[str]
  - `pointer_order`: int
- Validation rules:
  - `pointer_order` maps to original pointer sequence for deterministic reduce.

### ParallelExecutionConfig
- Description: Runtime page-concurrency settings resolved from environment.
- Fields:
  - `page_parallelism`: int
  - `raw_env_value`: str | None
  - `used_default`: bool
- Validation rules:
  - Missing/invalid env -> `page_parallelism = 4`
  - Effective minimum -> `max(1, page_parallelism)`

### AgentState (LangGraph)
- Description: State payload passed through LangGraph nodes.
- Fields:
  - `request`: `RAGAgentInput`
  - `pointers`: list[`PagePointer`]
  - `page_results`: list[`PageTaskResult`]
  - `retained_pages`: list[dict[str, object]]
  - `extracted_pages`: list[`ExtractedPage`]
  - `errors`: list[str]
  - `parallelism`: int

### RAGCompletionEvent
- Description: Outgoing Kafka payload produced to topic `rag-complete`.
- Fields:
  - `request_id`: str
  - `session_ctx`: dict[str, object]
  - `user_prompt`: str
  - `compiled_material`: str
  - `status`: str (`complete` | `partial` | `failed`)
  - `errors`: list[str]
  - `total_pages_processed`: int
  - `total_pages_included`: int
  - `started_at`: str
  - `completed_at`: str
  - `duration_ms`: int
  - `source`: str

## Relationships

- One `RAGRequestEvent` expands to many `PagePointer` items.
- Each `PagePointer` yields one `PageTaskResult`.
- Reduced `PageTaskResult` collection produces final `RAGCompletionEvent` content.

## State Transitions

### Agent execution
1. `initialized` -> `documents_opened`
2. `documents_opened` -> `pointers_built`
3. `pointers_built` -> `pages_dispatched_parallel`
4. `pages_dispatched_parallel` -> `results_reduced`
5. `results_reduced` -> `material_compiled`
6. `material_compiled` -> `completed`

### Parallel dispatch lifecycle
1. pointer emitted for processing
2. page extraction/relevance task runs independently
3. task result emitted to reducer
4. reducer merges in deterministic pointer order