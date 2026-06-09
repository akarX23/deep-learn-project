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

Confirm compose image expectations:

```bash
docker compose config | grep -E "apache/kafka:4.2.1|provectuslabs/kafka-ui:latest"
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
- Kafka admin client initializes during lifespan startup.
- On transient failures, startup retries follow configured retry count and timeout.
- Startup exits with explicit failure if retry budget is exhausted.
- On service shutdown, Kafka admin resources are closed via lifespan shutdown handling.

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
- `13 passed` in `backend_service/tests`.
- Covers startup success, retry-then-success, retry exhaustion, shutdown cleanup, env precedence, API success, duplicate handling, payload validation, HTTP exception envelope, unhandled exception envelope, and runtime error mapping.
- Covers compose contract checks for Kafka image pin (`apache/kafka:4.2.1`), Kafka UI image wiring, and KRaft environment key presence.

## 6. Run quality checks

```bash
ruff check backend_service
ruff format --check backend_service
python -m compileall backend_service
```

Latest local evidence:
- `ruff check` passed.
- `ruff format --check` passed.
- `python -m compileall backend_service` completed successfully.

## 7. Performance baseline (local)

Measured with `fastapi.testclient.TestClient` and mocked Kafka admin calls:
- Startup with one retry (configured timeout = 1s): `~1006.53 ms` total startup time.
- Topic create API p95 latency across 30 calls: `~2.24 ms`.

Interpretation:
- Topic create latency is comfortably within the plan budget (`<= 2s` p95 local).
- Startup behavior aligns with retry budget (`retry_count + 1` attempts with configured delay).

## 8. Compose startup-time validation

Target:
- Bring up local Kafka + Kafka UI in under 2 minutes.

Current environment result:
- `docker compose` command is available, but startup validation is blocked by Docker daemon permission:
  - `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock`

Validation command to run in a compose-capable environment:

```bash
start=$(date +%s)
docker compose up -d kafka kafka-ui
end=$(date +%s)
echo $((end-start))
```

## 9. Scope reminder

This backend service is limited to Kafka admin startup connectivity and topic creation API.
No inter-service messaging proxy behavior is included in this feature.
