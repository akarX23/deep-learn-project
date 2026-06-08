# Contract: Backend Kafka Topic API

## Purpose
Defines the backend microservice contract for topic creation and startup readiness assumptions.

## Runtime Configuration Contract

Environment loading precedence:
1. Load `.env.local` when present.
2. Allow already-initialized process environment variables to override loaded values.

Required environment variables:
- `BACKEND_KAFKA_BOOTSTRAP_SERVERS`
- `BACKEND_KAFKA_STARTUP_RETRY_COUNT`
- `BACKEND_KAFKA_STARTUP_RETRY_TIMEOUT_SECONDS`

Optional environment variables:
- `BACKEND_KAFKA_CLIENT_ID`
- `BACKEND_KAFKA_SECURITY_PROTOCOL`
- `BACKEND_KAFKA_SASL_MECHANISM`
- `BACKEND_KAFKA_SASL_USERNAME`
- `BACKEND_KAFKA_SASL_PASSWORD`
- `BACKEND_KAFKA_SSL_CAFILE`

## Endpoint

### POST /api/v1/topics

Create a Kafka topic using initialized Kafka admin client.

Request body:
```json
{
  "topic_name": "agent-events",
  "num_partitions": 3,
  "replication_factor": 1,
  "config": {
    "retention.ms": "86400000"
  }
}
```

Success response (201 Created):
```json
{
  "topic_name": "agent-events",
  "status": "created",
  "message": "Topic created successfully"
}
```

Existing topic response (200 OK):
```json
{
  "topic_name": "agent-events",
  "status": "already_exists",
  "message": "Topic already exists"
}
```

Validation/runtime failure response (4xx/5xx):
```json
{
  "topic_name": null,
  "status": "error",
  "message": "Validation failed: topic_name is required"
}
```

Global exception handling contract:
- Validation exceptions (`422`) MUST return the structured error envelope.
- HTTP exceptions (`4xx/5xx`) MUST return the structured error envelope.
- Unhandled exceptions (`500`) MUST return the structured error envelope.

## Startup Behavior Contract

- Service MUST attempt Kafka admin initialization during startup.
- Service MUST retry on connection failure using configured retry count and timeout.
- Service MUST fail startup if retry limit is exhausted.
- Service SHOULD emit diagnostics per startup connection attempt and final failure reason.
- Service MUST release Kafka admin resources during FastAPI shutdown lifecycle handling.

## Local Infrastructure Contract (Docker Compose)

- Root `docker-compose.yaml` MUST define:
  - Kafka service
  - Kafka UI service
- Kafka UI service MUST use image `provectuslabs/kafka-ui:latest`.
- Kafka UI service MUST be configured to connect to the compose Kafka service.

## Scope Boundary

- No producer/consumer/message relay APIs are exposed.
- Only topic creation endpoint is in scope for this feature.
