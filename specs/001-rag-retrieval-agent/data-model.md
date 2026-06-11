# Data Model: RAG Kafka Event Integration

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
  - request_id must be non-empty and correlation-safe.
  - session_ctx must be present and JSON-serializable.
  - user_request must be non-empty.
  - file_paths must be non-empty.

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
  - request_id, session_ctx, user_prompt, and status are required.
  - compiled_material may be empty only when status is `failed`.
  - duration_ms must be >= 0.

### TopicRegistry
- Description: Enum-based topic registry in `project/topics.py` for all agents/services.
- Fields:
  - planner.rag_request_topic: str (`rag`)
  - rag.rag_complete_topic: str (`rag-complete`)
  - additional service topic enums as needed by repository conventions.
- Validation rules:
  - topic names must be non-empty and unique across enum values.

### KafkaRuntimeConfig
- Description: Runtime configuration inherited from backend Kafka flags.
- Fields:
  - bootstrap_servers: str (`BACKEND_KAFKA_BOOTSTRAP_SERVERS`)
  - client_id: str (`BACKEND_KAFKA_CLIENT_ID` or service default)
  - security_protocol: str | None (`BACKEND_KAFKA_SECURITY_PROTOCOL`)
  - sasl_mechanism: str | None (`BACKEND_KAFKA_SASL_MECHANISM`)
  - sasl_username: str | None (`BACKEND_KAFKA_SASL_USERNAME`)
  - sasl_password: str | None (`BACKEND_KAFKA_SASL_PASSWORD`)
  - ssl_cafile: str | None (`BACKEND_KAFKA_SSL_CAFILE`)
  - backend_api_topic_url: str (`BACKEND_API_TOPIC_URL`)
- Validation rules:
  - bootstrap_servers and backend_api_topic_url must be non-empty.

### ConsumerLifecycleState
- Description: Service runtime state for continuous polling and graceful operation.
- Fields:
  - running: bool
  - last_poll_at: str | None
  - last_success_request_id: str | None
  - consecutive_failures: int
- Validation rules:
  - consecutive_failures must be >= 0.

### RequestLifecycleLogEntry
- Description: Structured observability record for each stage in the request lifecycle.
- Fields:
  - request_id: str
  - stage: str (`consumed` | `validated` | `processing_started` | `processing_completed` | `publish_completed` | `error`)
  - level: str
  - message: str
  - timestamp: str
  - metadata: dict[str, object]
- Validation rules:
  - stage and request_id are required for all request-scoped entries.

## Relationships
- One `RAGRequestEvent` maps to one `RAGCompletionEvent`.
- `KafkaRuntimeConfig` governs producer and consumer initialization in `rag_agent/kafka.py`.
- `TopicRegistry` provides topic names used by consumer subscription and completion publishing.
- `ConsumerLifecycleState` tracks runtime polling state across many `RAGRequestEvent` instances.
- Multiple `RequestLifecycleLogEntry` records are emitted for each request lifecycle.

## State Transitions

### Request-level lifecycle
1. consumed -> validated
2. validated -> processing_started
3. processing_started -> processing_completed
4. processing_completed -> publish_completed
5. any stage -> error (non-fatal, service keeps running)

### Service-level consumer state
1. stopped -> running (FastAPI startup)
2. running -> running (continuous poll loop)
3. running -> stopped (FastAPI shutdown)

## Derived Fields
- `duration_ms` = `completed_at - started_at` (milliseconds)
- `status` derives from RAG processing result semantics:
  - `complete` for successful output without blocking failures
  - `partial` for mixed outcomes with usable output
  - `failed` for no usable output
