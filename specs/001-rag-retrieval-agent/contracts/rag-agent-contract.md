# Contract: RAG Kafka Worker Integration (Deterministic Parallel Loop Update)

## Purpose

Define contracts for worker-managed Kafka transport and simplified `agent.py` page processing using deterministic parallel loop execution (no LangGraph StateGraph in page flow).

## Environment Contract

Kafka settings:
- `BACKEND_KAFKA_BOOTSTRAP_SERVERS` (required)
- `BACKEND_KAFKA_CLIENT_ID` (optional)
- `BACKEND_KAFKA_SECURITY_PROTOCOL` (optional)
- `BACKEND_KAFKA_SASL_MECHANISM` (optional)
- `BACKEND_KAFKA_SASL_USERNAME` (optional)
- `BACKEND_KAFKA_SASL_PASSWORD` (optional)
- `BACKEND_KAFKA_SSL_CAFILE` (optional)

Agent parallelism:
- `RAG_PAGE_PARALLELISM` (integer, default `4`)

## Topic Contract

- request topic: `rag`
- completion topic: `rag-complete`

## Runtime Flow Contract

1. `worker.py` starts producer/consumer and topic check.
2. poll loop consumes request payloads from `rag`.
3. worker dispatches payload to `agent.py`.
4. `agent.py` builds ordered page pointers and processes pages in bounded parallel execution.
5. `agent.py` reduces results deterministically by pointer order.
6. failed pages are excluded from extracted content and captured in a simple failure list.
7. worker publishes completion payload to `rag-complete`.

## Simplified Agent State Contract

- No StateGraph-managed complex state for page orchestration.
- Final state retains:
  - successful extracted page content
  - simple failed-page list (`page_number`, `reason`)
  - aggregated errors list

## Logging Contract

Agent logs stage events:
- `page_dispatched`
- `page_processed`
- `page_failed`
- `state_reduced`

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

## Failure and Deferred Scope Contract

- page-level failures do not terminate request processing.
- failed pages are ignored from extracted content but tracked in failure list.
- advanced retry, richer validation, and deep exception taxonomy remain TODO scope.