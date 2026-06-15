# Quickstart: RAG Agent Deterministic Parallel Loop Simplification

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

## 3. Start local Kafka (optional)

```bash
docker compose up -d kafka kafka-ui
```

## 4. Start worker runtime

```bash
python -m rag_agent.worker
```

## 5. Request processing flow

For each request event:
1. worker consumes payload from `rag`
2. worker dispatches to `process_request_event`
3. `agent.py` builds deterministic page pointer order
4. page tasks run in parallel with max workers from `RAG_PAGE_PARALLELISM`
5. successful extracted content is reduced in pointer order
6. failed pages are excluded from extracted content and tracked separately
7. worker publishes completion payload to `rag-complete`

## 6. Verify logs

Check for stage logs:
- `page_dispatched`
- `page_processed`
- `page_failed`
- `state_reduced`

## 7. Run validation checks

```bash
.venv/bin/python -m pytest -q rag_agent/tests
.venv/bin/ruff check project rag_agent
.venv/bin/ruff format --check project rag_agent
.venv/bin/python -m compileall project rag_agent
```

## 8. Deferred scope reminders

Advanced retries, rich validation, and expanded exception taxonomy remain deferred TODO scope.