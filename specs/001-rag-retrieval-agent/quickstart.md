# Quickstart: RAG Agent Parallel Page Processing

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure environment

Set runtime values in `.env.local`:

```env
BACKEND_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
BACKEND_KAFKA_CLIENT_ID=rag-service
BACKEND_KAFKA_SECURITY_PROTOCOL=
BACKEND_KAFKA_SASL_MECHANISM=
BACKEND_KAFKA_SASL_USERNAME=
BACKEND_KAFKA_SASL_PASSWORD=
BACKEND_KAFKA_SSL_CAFILE=
RAG_PAGE_PARALLELISM=4
```

Parallelism behavior:
- missing/invalid `RAG_PAGE_PARALLELISM` -> default `4`
- values below `1` are clamped to `1`

## 3. Start local Kafka (optional)

```bash
docker compose up -d kafka kafka-ui
```

## 4. Start worker runtime

```bash
python -m rag_agent.worker
```

Expected startup sequence:
1. worker initializes Kafka producer and consumer through `kafka.py`
2. worker checks topic presence for required topics
3. missing-topic warnings are logged (startup continues)
4. threaded consumer loop starts polling `rag`

## 5. Request processing flow

For each consumed request event:
1. worker receives payload from `rag`
2. worker dispatches request to `process_request_event`
3. `agent.py` opens documents and builds page pointers
4. LangGraph StateGraph dispatches page processing in bounded parallel mode
5. per-page results are reduced and compiled into final material
6. worker publishes completion event to `rag-complete`

## 6. Smoke-test payload

```json
{
  "request_id": "demo-001",
  "session_ctx": {"session_id": "s-1"},
  "user_request": "Summarize chapter one",
  "file_paths": ["rag_agent/tests/inputs/sample.pdf"]
}
```

## 7. Validate bounded concurrency behavior

- Use a request with multiple pages and verify processing overlaps in logs.
- Confirm in-flight page tasks do not exceed `RAG_PAGE_PARALLELISM`.
- Confirm output status and extracted page semantics match prior behavior.

## 8. Run validation checks

```bash
.venv/bin/python -m pytest -q rag_agent/tests
.venv/bin/ruff check project rag_agent
.venv/bin/ruff format --check project rag_agent
.venv/bin/python -m compileall project rag_agent
```

## 9. Deferred scope reminders

Advanced retry policy tuning, rich metrics instrumentation, and expanded exception taxonomy remain TODO scope.