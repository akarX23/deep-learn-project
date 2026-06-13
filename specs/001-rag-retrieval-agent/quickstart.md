# Quickstart: RAG Kafka Worker Simplification

## 1. Install dependencies

From repository root:

```bash
pip install -r requirements.txt
```

## 2. Configure environment

Set Kafka runtime settings in `.env.local`:

```env
BACKEND_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
BACKEND_KAFKA_CLIENT_ID=rag-service
```

Optional secure-cluster settings:

```env
BACKEND_KAFKA_SECURITY_PROTOCOL=
BACKEND_KAFKA_SASL_MECHANISM=
BACKEND_KAFKA_SASL_USERNAME=
BACKEND_KAFKA_SASL_PASSWORD=
BACKEND_KAFKA_SSL_CAFILE=
```

Important:
- No backend topic bootstrap API is used by this worker runtime.
- Topics are assumed to be provisioned externally.

## 3. Start Kafka infrastructure

If using local compose stack:

```bash
docker compose up -d kafka kafka-ui
```

## 4. Run RAG worker process

Run worker entrypoint (thread-based consumer loop runtime):

```bash
python -m rag_agent.worker
```

Expected startup flow:
- worker reads `BACKEND_KAFKA*` config
- worker initializes producer and consumer via `rag_agent/kafka.py`
- worker checks required-topic presence via Kafka metadata query
- if topics are missing, worker logs clear warning and continues startup
- dedicated consumer loop thread starts polling topic `rag`

## 5. Publish test request event

Publish an event to topic `rag`:

```json
{
  "request_id": "demo-001",
  "session_ctx": {"session_id": "s-1"},
  "user_request": "Summarize the uploaded chapter",
  "file_paths": ["rag_agent/tests/inputs/sample.pdf"]
}
```

Expected behavior:
- event consumed and dispatched to `RAGAgent`
- completion event published to `rag-complete`

## 6. Verify completion event shape

Confirm output event includes:
- `session_ctx`
- `user_prompt`
- `compiled_material`
- `status`
- `errors`
- request correlation metadata (`request_id`)

## 7. Verify logs

Ensure lifecycle logs include:
- `startup_topic_check`
- `consumed`
- `processing_started`
- `processing_completed`
- `publish_completed`
- `error` (when applicable)

## 8. Run targeted test suite

```bash
.venv/bin/python -m pytest -q rag_agent/tests/test_request_event.py rag_agent/tests/test_completion_event.py rag_agent/tests/test_logging.py rag_agent/tests/test_kafka_integration.py
```

## 9. Quality checks

```bash
.venv/bin/ruff check project rag_agent
.venv/bin/ruff format --check project rag_agent
.venv/bin/python -m compileall project rag_agent
```

Latest local results:
- `.venv/bin/ruff check project rag_agent` passed.
- `.venv/bin/ruff format --check project rag_agent` reported formatting drift in existing files.
- `.venv/bin/python -m compileall project rag_agent` passed.
- `.venv/bin/python -m pytest -q rag_agent/tests/test_worker_runtime.py rag_agent/tests/test_kafka_integration.py` passed.

## 10. Module structure after simplification

```text
rag_agent/
├── agent.py          # Basic exception handling only; TODOs for inner guards
├── handlers.py       # Dispatch-focused; no StructuredLogger; TODOs for validation/metrics
├── kafka.py          # Kafka transport and metadata checks
├── worker.py         # Consumer loop thread entry point
├── utils/
│   ├── __init__.py
│   ├── helpers.py    # Pure helpers + merged LLM config + call_llm/call_embedding
│   ├── llm_client.py # Simplified basic LLM/embedding wrappers (TODOs for guards)
│   ├── prompts.py    # Prompt templates
│   └── tools.py      # PDF extraction tools
└── tests/
```

Deleted in this phase:
- `rag_agent/service.py` — compatibility shim removed
- `rag_agent/logging.py` — `StructuredLogger` replaced by `logging.getLogger(__name__)`

## 11. Scope reminder

This phase focuses on module simplification, standard logging, `utils/` restructuring, and basic exception handling. Planner logic, advanced handler validation/metrics, and credential guards in LLM calls are deferred as TODOs.
