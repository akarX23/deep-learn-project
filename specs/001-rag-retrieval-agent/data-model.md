# Data Model: RAG Kafka Worker Simplification

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
- Validation rules:
  - Baseline schema validation remains in shared schemas.
  - Additional semantic validation is deferred as TODO scope.

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

### TopicPresenceCheckResult
- Description: Startup check result based on Kafka metadata query.
- Fields:
  - `required_topics`: list[str]
  - `existing_topics`: list[str]
  - `missing_topics`: list[str]
  - `warning_message`: str | None
- Validation rules:
  - Missing topics generate warnings but do not block worker startup.

### WorkerRuntimeState
- Description: Process-level runtime state for threaded consumer operation.
- Fields:
  - `running`: bool
  - `stop_event_set`: bool
  - `consumer_thread_alive`: bool
  - `startup_check_complete`: bool

### KafkaRuntimeGateway
- Description: Function-level boundary in `rag_agent/kafka.py` for env-based connector setup, producer/consumer creation, poll, and publish operations.
- Responsibilities:
  - Read Kafka env values directly
  - Create consumer and producer objects
  - Expose consume/publish helper functions for other modules

### HelpersEnvValues
- Description: Values returned by simple env extraction helper functions in `helpers.py`.
- Model note:
  - No config classes and no validators in `helpers.py` for this phase.

## Relationships
- One `RAGRequestEvent` maps to one `RAGCompletionEvent` per terminal processing attempt.
- `worker.py` orchestrates startup check and threaded loop.
- `kafka.py` owns Kafka transport functions used by worker.
- `agent.py` remains Kafka-agnostic and returns processing output only.

## State Transitions

### Worker lifecycle
1. `starting` -> `checking_topics`
2. `checking_topics` -> `running` (ready or warning message)
3. `running` -> `stopping`
4. `stopping` -> `stopped`

### Request lifecycle
1. `consumed` -> `processing_started`
2. `processing_started` -> `processing_completed`
3. `processing_completed` -> `publish_completed`
4. any state -> `error` (non-fatal for worker runtime)
