# Contract: RAG Kafka Service Integration

## Purpose
Defines the event and startup contracts for Kafka-integrated RAG service behavior.

## Environment Contract

RAG Kafka runtime must inherit backend Kafka flags:
- `BACKEND_KAFKA_BOOTSTRAP_SERVERS` (required)
- `BACKEND_KAFKA_CLIENT_ID` (optional)
- `BACKEND_KAFKA_SECURITY_PROTOCOL` (optional)
- `BACKEND_KAFKA_SASL_MECHANISM` (optional)
- `BACKEND_KAFKA_SASL_USERNAME` (optional)
- `BACKEND_KAFKA_SASL_PASSWORD` (optional)
- `BACKEND_KAFKA_SSL_CAFILE` (optional)

Additional required startup dependency:
- `BACKEND_API_TOPIC_URL` (required, used to call backend topic-creation API during startup)

## Topic Registry Contract

Topic names are centrally defined in `project/topics.py` using enums.
Minimum required enum values for this feature:
- request topic: `rag`
- completion topic: `rag-complete`

No hardcoded topic string usage is allowed outside the topic registry and Kafka gateway module.

## Kafka Gateway Module Contract

All Kafka interactions must route through `rag_agent/kafka.py`:
- connection/bootstrap logic
- producer initialization
- consumer initialization/subscription
- send functions for outgoing events
- receive/dispatch controller functions for incoming events

No direct producer/consumer calls are permitted in unrelated service modules.

## Incoming Event Contract: Topic `rag`

Required fields:
```json
{
  "request_id": "string",
  "session_ctx": {},
  "user_request": "string",
  "file_paths": ["string"]
}
```

Validation semantics:
- Missing required fields -> event rejected and logged
- Invalid payload shape -> processing skipped, service continues polling
- Valid payload -> dispatch to RAG processing handler

## Processing Contract

For valid events:
1. map `user_request` to RAG `user_prompt`
2. call existing `RAGAgent` pipeline with provided `file_paths`
3. capture processing result (status, compiled material, counters, errors)
4. publish completion event to `rag-complete`

No Planner functionality is implemented inside RAG service.

## Outgoing Event Contract: Topic `rag-complete`

Required fields:
```json
{
  "request_id": "string",
  "session_ctx": {},
  "user_prompt": "string",
  "compiled_material": "string",
  "status": "complete|partial|failed",
  "errors": [],
  "total_pages_processed": 0,
  "total_pages_included": 0,
  "started_at": "timestamp",
  "completed_at": "timestamp",
  "duration_ms": 0
}
```

Completion semantics:
- Success and non-success outcomes both publish completion events when processing reaches terminal state.
- Publish failure must be logged with request correlation and error detail.

## Startup and Runtime Contract

FastAPI startup behavior:
1. initialize service context
2. call `BACKEND_API_TOPIC_URL` to create/ensure required topics
3. initialize Kafka producer/consumer via `rag_agent/kafka.py`
4. start continuous consumer poll loop

Shutdown behavior:
- stop poll loop cleanly
- flush/close Kafka producer
- close Kafka consumer

## Logging and Observability Contract

Required progress stages:
- `consumed`
- `validated`
- `processing_started`
- `processing_completed`
- `publish_completed`
- `error`

Each request-scoped log must include correlation metadata (at minimum `request_id`; include topic/stage details where relevant).

## Failure Handling Contract

- Single-event failures must not terminate service process.
- Validation failures, RAG processing failures, and publish failures are logged with stage context.
- Consumer loop remains active after non-fatal request errors.
