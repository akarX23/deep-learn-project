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

## 5. Run tests

```bash
pytest backend_service/tests -q
```

## 6. Scope reminder

This backend service is limited to Kafka admin startup connectivity and topic creation API.
No inter-service messaging proxy behavior is included in this feature.
