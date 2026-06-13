# Data Model: RAG Kafka Worker Simplification

## Entities

### RAGRequestEvent
- Description: Incoming Kafka event consumed from topic `rag`.
- Fields:
  - request_id: str
  - session_ctx: dict[str, object]
  - user_request: str
  - file_paths: list[str]
  - created_at: str | None
  - source: str | None
- Validation rules:
  - Required-field and payload-shape hardening beyond baseline schema checks is deferred in this phase (tracked as TODO in handler module).

### RAGCompletionEvent
- Description: Outgoing Kafka event published to topic `rag-complete`.
- Fields:
  - request_id: str
  - session_ctx: dict[str, object]
  - user_prompt: str
  - compiled_material: str
  - status: str (`complete` | `partial` | `failed`)
  - errors: list[str]
  - total_pages_processed: int
  - total_pages_included: int
  - started_at: str
  - completed_at: str
  - duration_ms: int
  - source: str
- Validation rules:
  - Completion payload preserves request correlation and status semantics for downstream handling.

### TopicRegistry
- Description: Enum-based topic registry in `project/topics.py`.
- Fields:
  - planner.rag_request_topic: str (`rag`)
  - rag.rag_complete_topic: str (`rag-complete`)
- Validation rules:
  - Topic names remain non-empty and stable in centralized registry.

### KafkaRuntimeConfig
- Description: Runtime configuration inherited from `BACKEND_KAFKA*` flags only.
- Fields:
  - bootstrap_servers: str (`BACKEND_KAFKA_BOOTSTRAP_SERVERS`)
  - client_id: str (`BACKEND_KAFKA_CLIENT_ID` or service default)
  - security_protocol: str | None (`BACKEND_KAFKA_SECURITY_PROTOCOL`)
  - sasl_mechanism: str | None (`BACKEND_KAFKA_SASL_MECHANISM`)
  - sasl_username: str | None (`BACKEND_KAFKA_SASL_USERNAME`)
  - sasl_password: str | None (`BACKEND_KAFKA_SASL_PASSWORD`)
  - ssl_cafile: str | None (`BACKEND_KAFKA_SSL_CAFILE`)
  - consumer_group_id: str
  - poll_timeout_ms: int
- Validation rules:
  - `BACKEND_KAFKA_BOOTSTRAP_SERVERS` must be non-empty.
  - No backend topic API URL is included in this model.

### WorkerRuntimeState
- Description: Process-level state for standalone worker lifecycle.
- Fields:
  - running: bool
  - stop_event_set: bool
  - poll_thread_alive: bool
  - startup_topic_check_complete: bool
  - startup_topic_check_warnings: list[str]
- Validation rules:
  - Worker continues running after non-fatal startup warnings.

### TopicPresenceCheckResult
- Description: Startup metadata check output for required topics.
- Fields:
  - required_topics: list[str]
  - existing_topics: list[str]
  - missing_topics: list[str]
  - warning_message: str | None
- Validation rules:
  - Missing topics produce warning message but do not block worker startup.

### RequestLifecycleLogEntry
- Description: Structured observability record for startup and request lifecycle stages.
- Fields:
  - request_id: str
  - stage: str (`startup_topic_check` | `consumed` | `processing_started` | `processing_completed` | `publish_completed` | `error`)
  - level: str
  - message: str
  - timestamp: str
  - metadata: dict[str, object]
- Validation rules:
  - Startup warnings and per-request failures must be represented with stage-scoped entries.

## Relationships
- One `RAGRequestEvent` maps to one `RAGCompletionEvent` per terminal processing attempt.
- `KafkaRuntimeConfig` governs producer/consumer creation and metadata checks in `rag_agent/kafka.py`.
- `TopicRegistry` defines the required-topic set checked at startup and used during runtime publish/consume.
- `WorkerRuntimeState` controls thread lifecycle and startup-check outcomes.
- `TopicPresenceCheckResult` is produced at startup and emitted through structured logs.

## State Transitions

### Worker lifecycle
1. starting -> checking_topics
2. checking_topics -> running (with ready log or warning log)
3. running -> stopping (shutdown signal)
4. stopping -> stopped (poll thread joined, Kafka resources closed)

### Request-level lifecycle
1. consumed -> processing_started
2. processing_started -> processing_completed
3. processing_completed -> publish_completed
4. any stage -> error (non-fatal, worker remains running)

## Module Structure Model (New — Simplification Phase)

### `rag_agent/utils/` Package

- **Purpose**: Contains all helper-oriented support modules moved from the `rag_agent/` root.
- **Contents**:
  - `helpers.py` — Pure utility functions (`cosine_similarity`, `serialize_table_to_markdown`, `assemble_page_content`, `build_compilation_context`) + merged LLM/config responsibilities (`LLMConfig`, `EmbeddingConfig`, `KafkaRuntimeConfig`, `get_text_llm_config()`, `get_vlm_config()`, `get_embedding_config()`, `call_llm()`, `call_embedding()`).
  - `llm_client.py` — Simplified LLM/embedding wrappers (basic calls only, deferred validation via TODOs).
  - `prompts.py` — Prompt templates (`IMAGE_DESCRIPTION_PROMPT`, `MATERIAL_COMPILATION_PROMPT`). Unchanged.
  - `tools.py` — Stateless PDF extraction functions. Unchanged.
- **Consumers**: `agent.py`, `handlers.py`, `worker.py` import from `rag_agent.utils.*`.

### Deleted Modules

- `rag_agent/service.py` — Removed. Was a compatibility re-export shim for `worker.py`.
- `rag_agent/logging.py` — Removed. `StructuredLogger` class deleted; replaced by standard `logging.getLogger(__name__)` pattern across all modules.

## Derived Fields
- `duration_ms` = `completed_at - started_at` (milliseconds)
- `missing_topics` = `required_topics - existing_topics`
- `status` is derived from `RAGAgent` result semantics (`complete` | `partial` | `failed`)
