# Quickstart: RAG Kafka Event Integration

## 1. Install dependencies

From repository root:

```bash
pip install -r requirements.txt
```

## 2. Configure environment

Set Kafka and startup API settings in `.env.local`:

```env
BACKEND_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
BACKEND_KAFKA_CLIENT_ID=rag-service
BACKEND_API_TOPIC_URL=http://localhost:8001/api/v1/topics
```

Optional secure-cluster settings (inherited from backend contract):

```env
BACKEND_KAFKA_SECURITY_PROTOCOL=
BACKEND_KAFKA_SASL_MECHANISM=
BACKEND_KAFKA_SASL_USERNAME=
BACKEND_KAFKA_SASL_PASSWORD=
BACKEND_KAFKA_SSL_CAFILE=
```

## 3. Ensure backend topic API is running

Start backend service so RAG startup can call topic creation endpoint:

```bash
python -m backend_service.app.main
```

## 4. Start Kafka infrastructure

If using local compose stack:

```bash
docker compose up -d kafka kafka-ui
```

## 5. Run RAG FastAPI service

Run lightweight service entrypoint (planned module):

```bash
python -m rag_agent.service
```

Expected startup flow:
- service reads `BACKEND_KAFKA*` config
- service calls `BACKEND_API_TOPIC_URL` to ensure required topics
- service initializes producer and consumer via `rag_agent/kafka.py`
- consumer loop starts continuous polling on topic `rag`

## 6. Publish test request event

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
- event consumed and validated
- `RAGAgent` pipeline executed
- completion event published to `rag-complete`

## 7. Verify completion event shape

Confirm output event includes:
- `session_ctx`
- `user_prompt`
- `compiled_material`
- `status`
- `errors`
- request correlation metadata (`request_id`)

## 8. Verify logs

Ensure structured progress logs include stages:
- consumed
- validated
- processing_started
- processing_completed
- publish_completed
- error (when applicable)

## 9. Run test suite

Run RAG and integration-facing tests:

```bash
pytest rag_agent/tests -q
```

## 10. Scope reminder

This feature only integrates RAG service consume/process/publish behavior.
Planner agent functionality is explicitly out of scope.
