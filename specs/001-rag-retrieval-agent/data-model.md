# Data Model: RAG Agent Deterministic Parallel Loop Simplification

## Entities

### RAGRequestEvent
- Description: Incoming Kafka payload from topic `rag`.
- Fields:
  - `request_id`: str
  - `session_ctx`: dict[str, object]
  - `user_request`: str
  - `file_paths`: list[str]

### PagePointer
- Description: Deterministic pointer to one source page.
- Fields:
  - `file_path`: str
  - `file_name`: str
  - `page_number`: int
  - `pointer_order`: int

### ExtractedPageContent
- Description: Successful page extraction unit retained in final state.
- Fields:
  - `file_name`: str
  - `page_number`: int
  - `relevance_score`: float
  - `content`: str

### FailedPage
- Description: Simple failure record for pages excluded from extracted content.
- Fields:
  - `file_name`: str
  - `page_number`: int
  - `reason`: str

### AgentFinalState
- Description: Minimal agent output assembly state.
- Fields:
  - `extracted_content`: list[`ExtractedPageContent`]
  - `failed_pages`: list[`FailedPage`]
  - `errors`: list[str]

### RAGCompletionEvent
- Description: Outgoing Kafka payload to `rag-complete`.
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

## Relationships

- One `RAGRequestEvent` expands to ordered `PagePointer` items.
- Each `PagePointer` yields either one `ExtractedPageContent` or one `FailedPage`.
- `AgentFinalState` feeds compilation and completion payload assembly.

## State Transitions

### Agent runtime
1. `pointers_built`
2. `pages_dispatched`
3. `pages_processed`
4. `state_reduced`
5. `compiled`

### Failure handling
1. page task exception occurs
2. failed page entry appended (`file_name`, `page_number`, `reason`)
3. page excluded from extracted content