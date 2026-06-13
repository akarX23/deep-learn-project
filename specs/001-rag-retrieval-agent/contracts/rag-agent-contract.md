# Contract: RAG Kafka Worker Integration

## Purpose

Defines event, startup, typing, and runtime contracts for the standalone Kafka worker-based RAG integration.

## Environment Contract

RAG worker runtime inherits backend Kafka transport flags only:
- `BACKEND_KAFKA_BOOTSTRAP_SERVERS` (required)
- `BACKEND_KAFKA_CLIENT_ID` (optional)
- `BACKEND_KAFKA_SECURITY_PROTOCOL` (optional)
- `BACKEND_KAFKA_SASL_MECHANISM` (optional)
- `BACKEND_KAFKA_SASL_USERNAME` (optional)
- `BACKEND_KAFKA_SASL_PASSWORD` (optional)
- `BACKEND_KAFKA_SSL_CAFILE` (optional)

Explicit removals for this feature phase:
- No `BACKEND_API_TOPIC_URL`
- No backend topic-creation API call at startup

## Topic Registry Contract

Topic names are centralized in `project/topics.py`:
- request topic: `rag`
- completion topic: `rag-complete`

Hardcoded topic strings outside topic registry and Kafka gateway are disallowed.

## Module Structure Contract (Updated — Simplification Phase)

After simplification the active module layout is:

```text
rag_agent/
├── agent.py       # Orchestration — basic exception handling only
├── handlers.py    # Ingest/dispatch — basic exception handling only
├── kafka.py       # Kafka transport and metadata checks
├── worker.py      # Consumer loop thread entry point
└── utils/
    ├── __init__.py
    ├── helpers.py    # Pure helpers + merged LLM config + call_llm/call_embedding
    ├── llm_client.py # Simplified LLM/embedding wrappers (TODOs for guards)
    ├── prompts.py    # Prompt templates
    └── tools.py      # PDF extraction tools
```

Deleted modules (contract obligations discharged):
- `rag_agent/service.py` — removed
- `rag_agent/logging.py` — `StructuredLogger` replaced by standard `logging.getLogger(__name__)`

## Logging Module Contract

All modules MUST use:
```python
import logging
logger = logging.getLogger(__name__)
```

Entry point (`worker.py`) calls `logging.basicConfig(...)` once at startup. No custom logger class is permitted.

## Kafka Gateway Module Contract

All Kafka interactions route through `rag_agent/kafka.py`:
- producer and consumer initialization
- consumer subscription and polling wrappers
- completion publish wrappers
- startup metadata query wrappers for topic presence checks

No direct Kafka client calls in unrelated modules.

## Startup Contract (Worker Runtime)

Worker startup behavior:
1. load Kafka runtime config
2. initialize producer/consumer via `rag_agent/kafka.py`
3. check required-topic presence via Kafka metadata query
4. if topics are missing, log clear warning and continue startup
5. start dedicated consumer loop thread

Worker shutdown behavior:
- signal loop stop
- join consumer thread
- close consumer and producer resources

## Incoming Event Contract: Topic `rag`

Baseline event shape:
```json
{
  "request_id": "string",
  "session_ctx": {},
  "user_request": "string",
  "file_paths": ["string"]
}
```

Handler semantics in this phase:
- prioritize ingest + dispatch path
- strict validation hardening beyond schema baseline is deferred (TODO)
- malformed payload handling remains non-fatal and logged

## Processing Contract

For consumed request events:
1. map `user_request` to RAG `user_prompt`
2. invoke existing `RAGAgent` pipeline with `file_paths`
3. map output into completion payload
4. publish completion event to `rag-complete`

Planner behavior is out of scope and must not be implemented here.

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

Completion emission semantics:
- publish for terminal processing attempts
- on publish failure, log request-scoped error and continue worker operation

## Type Safety Contract

Public function signatures in `rag_agent/kafka.py`, `rag_agent/worker.py`, and `rag_agent/handlers.py` must:
- provide explicit typed inputs and outputs
- avoid broad untyped placeholder use wherever practical
- keep TODO markers explicit where behavior is intentionally deferred

## Logging and Observability Contract

Required stages:
- `startup_topic_check`
- `consumed`
- `processing_started`
- `processing_completed`
- `publish_completed`
- `error`

Each request-scoped log includes correlation metadata (`request_id` at minimum).

## Failure Handling Contract

- single-event failures are non-fatal
- startup missing-topic detection is warning-level, not startup-blocking
- worker loop stays active after non-fatal request errors
