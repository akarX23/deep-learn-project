# Contract: RAG Kafka Worker Integration

## Purpose

Define runtime and event contracts for the simplified worker architecture where `worker.py` orchestrates consume/process/publish directly, `kafka.py` owns Kafka transport functions, and `agent.py` remains Kafka-agnostic.

## Environment Contract

`kafka.py` reads Kafka settings from environment values directly:
- `BACKEND_KAFKA_BOOTSTRAP_SERVERS` (required)
- `BACKEND_KAFKA_CLIENT_ID` (optional)
- `BACKEND_KAFKA_SECURITY_PROTOCOL` (optional)
- `BACKEND_KAFKA_SASL_MECHANISM` (optional)
- `BACKEND_KAFKA_SASL_USERNAME` (optional)
- `BACKEND_KAFKA_SASL_PASSWORD` (optional)
- `BACKEND_KAFKA_SSL_CAFILE` (optional)

Removed from active contract:
- backend topic bootstrap API URL dependencies
- startup topic creation flow

## Topic Contract

Topic names come from centralized registry in `project/topics.py`:
- request topic: `rag`
- completion topic: `rag-complete`

## Runtime Flow Contract

Primary flow:
1. `worker.py` starts
2. `worker.py` invokes `kafka.py` env/config + producer/consumer setup helpers
3. `worker.py` runs startup topic presence check via `kafka.py`
4. worker logs warning and continues if topics are missing
5. threaded consumer loop polls events from `rag`
6. consumer loop calls `agent.py` directly
7. consumer loop publishes completion to `rag-complete` via `kafka.py`

## Module Ownership Contract

- `worker.py`: startup orchestration, thread lifecycle, and consume/process/publish loop control
- `kafka.py`: Kafka connector init, producer/consumer objects, and helper functions for consume/publish/check
- `agent.py`: processing logic only; returns output payload data and does not publish to Kafka
- `helpers.py`: environment extraction helper functions only; no classes and no validators in this phase

## Incoming Event Contract (`rag`)

Baseline request payload:

```json
{
  "request_id": "string",
  "session_ctx": {},
  "user_request": "string",
  "file_paths": ["string"]
}
```

## Outgoing Event Contract (`rag-complete`)

Baseline completion payload:

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

Public function boundaries in `worker.py`, `kafka.py`, `agent.py`, and helper modules use explicit type annotations and avoid untyped placeholders where practical.

## Failure and Deferred Scope Contract

- Per-event failures are non-fatal; loop continues.
- Missing topics at startup are warning-level only.
- Advanced validation, edge-case hardening, and deep exception handling are deferred and represented by TODO tasks in implementation.
