# Contract: RAG Kafka Worker Integration (Parallel Page Update)

## Purpose

Define runtime and event contracts for worker-managed Kafka flow and LangGraph-managed parallel page processing inside `agent.py`.

## Environment Contract

Kafka runtime settings (existing):
- `BACKEND_KAFKA_BOOTSTRAP_SERVERS` (required)
- `BACKEND_KAFKA_CLIENT_ID` (optional)
- `BACKEND_KAFKA_SECURITY_PROTOCOL` (optional)
- `BACKEND_KAFKA_SASL_MECHANISM` (optional)
- `BACKEND_KAFKA_SASL_USERNAME` (optional)
- `BACKEND_KAFKA_SASL_PASSWORD` (optional)
- `BACKEND_KAFKA_SSL_CAFILE` (optional)

Agent parallelism setting (new):
- `RAG_PAGE_PARALLELISM` (optional)
  - missing/invalid -> default `4`
  - effective value clamped to minimum `1`

## Topic Contract

Topic names from `project/topics.py`:
- request topic: `rag`
- completion topic: `rag-complete`

## Runtime Flow Contract

1. `worker.py` starts and initializes Kafka producer/consumer.
2. startup topic presence check runs; missing topics emit warning but do not block startup.
3. worker poll loop consumes from `rag`.
4. worker dispatches request to `agent.py`.
5. `agent.py` uses LangGraph StateGraph to process pages in bounded parallel fashion.
6. `agent.py` returns output payload only (Kafka-agnostic).
7. worker publishes completion event to `rag-complete`.

## Parallel Page Processing Contract

- Pages are processed independently and may execute concurrently.
- Maximum in-flight page processing is bounded by configured parallelism.
- No separate page-batching orchestration layer is introduced in agent logic.
- Per-page extraction/relevance/status logic remains behaviorally equivalent to prior sequential implementation.
- Reduction stage must preserve deterministic result ordering for stable outputs.

## Module Ownership Contract

- `worker.py`: startup orchestration, thread lifecycle, consume/process/publish control.
- `kafka.py`: Kafka connector setup, producer/consumer creation, topic checks, completion publishing.
- `agent.py`: page extraction orchestration and material compilation; no Kafka publishing.
- `helpers.py`: environment extraction helpers, including page-parallelism extraction policy.

## Incoming Event Contract (`rag`)

```json
{
  "request_id": "string",
  "session_ctx": {},
  "user_request": "string",
  "file_paths": ["string"]
}
```

## Outgoing Event Contract (`rag-complete`)

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

## Type Safety Contract

Public boundaries remain explicitly typed. Kafka boundaries use concrete `KafkaConsumer` and `KafkaProducer` types. Agent state and page task structures remain typed for predictable merge behavior.

## Failure and Deferred Scope Contract

- Per-event processing failures are non-fatal for worker runtime.
- Startup missing topics are warning-level only.
- Advanced retries/metrics and richer exception taxonomies remain deferred TODO scope.