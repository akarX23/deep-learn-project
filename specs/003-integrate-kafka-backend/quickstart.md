# Quickstart: Kafka Backend Integration Service

## 1. Configure environment

Create/update `.env.local` in project root with backend Kafka settings:

```env
BACKEND_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
BACKEND_KAFKA_STARTUP_RETRY_COUNT=5
BACKEND_KAFKA_STARTUP_RETRY_TIMEOUT_SECONDS=2
BACKEND_KAFKA_CLIENT_ID=backend-service
```

Environment loading behavior:
- `.env.local` is loaded when present.
- Process environment variables override `.env.local` values.

## 2. Start Kafka and Kafka UI locally

From project root:

```bash
docker compose up -d kafka kafka-ui
```

Validate containers are running:

```bash
docker compose ps
```

Verify Kafka UI is reachable (default):

```bash
curl -I http://localhost:8080
```

## 3. Run backend service

Example run command (exact path may differ after implementation):

```bash
python -m backend_service.app.main
```

Expected startup behavior:
- Kafka admin client initializes during startup.
- On transient failures, startup retries follow configured retry count and timeout.
- Startup exits with explicit failure if retry budget is exhausted.
- On service shutdown, Kafka admin resources are closed via lifecycle hooks.

## 4. Create a topic

Example request:

```bash
curl -X POST http://localhost:8001/api/v1/topics \
  -H "Content-Type: application/json" \
  -d '{"topic_name":"agent-events","num_partitions":1,"replication_factor":1}'
```

Expected responses:
- `201` with `status=created` for new topic.
- `200` with `status=already_exists` if topic exists.
- `4xx/5xx` with `status=error` for invalid input/runtime failures.

Structured error response shape (for validation/HTTP/unhandled failures):

```json
{
  "topic_name": null,
  "status": "error",
  "message": "..."
}
```

## 5. Run tests

```bash
pytest backend_service/tests -q
```

Latest local evidence:
- `8 passed` in `backend_service/tests`.
- Covers startup success, retry-then-success, retry exhaustion, env precedence, API success, duplicate handling, payload validation, and runtime error mapping.

## 6. Performance baseline (local)

Measured with `fastapi.testclient.TestClient` and mocked Kafka admin calls:
- Startup with one retry (configured timeout = 1s): `~1007 ms` total startup time.
- Topic create API p95 latency across 30 calls: `~2.60 ms`.

Interpretation:
- Topic create latency is comfortably within the plan budget (`<= 2s` p95 local).
- Startup behavior aligns with retry budget (`retry_count + 1` attempts with configured delay).

## 7. Scope reminder

This backend service is limited to Kafka admin startup connectivity and topic creation API.
No inter-service messaging proxy behavior is included in this feature.
