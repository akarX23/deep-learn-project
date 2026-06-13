# Quickstart: RAG Kafka Worker Simplification

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure Kafka environment

Set Kafka connection values in `.env.local`:

```env
BACKEND_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
BACKEND_KAFKA_CLIENT_ID=rag-service
BACKEND_KAFKA_SECURITY_PROTOCOL=
BACKEND_KAFKA_SASL_MECHANISM=
BACKEND_KAFKA_SASL_USERNAME=
BACKEND_KAFKA_SASL_PASSWORD=
BACKEND_KAFKA_SSL_CAFILE=
```

Notes:
- `kafka.py` reads these values directly.
- No backend topic-creation API call is used in this flow.

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

## 5. Event processing flow

For each consumed request event:
1. consumer loop receives payload from `rag`
2. consumer loop calls `agent.py` directly
3. `agent.py` returns output only (no Kafka publishing)
4. consumer loop publishes completion event to `rag-complete` via `kafka.py`

## 6. Smoke-test payload

Example request payload on `rag`:

```json
{
  "request_id": "demo-001",
  "session_ctx": {"session_id": "s-1"},
  "user_request": "Summarize chapter one",
  "file_paths": ["rag_agent/tests/inputs/sample.pdf"]
}
```

## 7. Verify logs

Check lifecycle stages:
- `startup_topic_check`
- `consumed`
- `processing_started`
- `processing_completed`
- `publish_completed`
- `error`

## 8. Run validation checks

```bash
.venv/bin/python -m pytest -q rag_agent/tests
.venv/bin/ruff check project rag_agent
.venv/bin/ruff format --check project rag_agent
.venv/bin/python -m compileall project rag_agent
```

## 9. Deferred scope reminders

Advanced validation, richer edge-case handling, and deeper exception taxonomy are intentionally deferred and should be tracked as TODO implementation tasks.
