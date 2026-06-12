# Contract: Backend Kafka Topic and Test-Event APIs

## Purpose
Defines backend API contracts for Kafka topic operations and topic-scoped test-event publishing.

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

### POST /api/v1/test-events/rag

Publish a contract-valid `RAGRequestEvent` to Kafka topic `rag` for integration testing.

Request body:
```json
{
  "overrides": {
    "user_request": "Summarize gradient descent",
    "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
    "session_ctx": {"mode": "quick"}
  }
}
```

Request semantics:
- Backend creates a default payload first.
- Optional `overrides` are merged onto defaults.
- Merged payload MUST validate against `project.schemas.RAGRequestEvent` before publish.
- API MUST only publish to Kafka; it MUST NOT invoke agent runtime services directly.

Success response (200 OK):
```json
{
  "request_id": "test-req-123",
  "topic": "rag",
  "publish_status": "published",
  "metadata": {
    "partition": 0,
    "offset": 42,
    "timestamp": 1781234567890
  }
}
```

Success response with partial metadata (200 OK):
```json
{
  "request_id": "test-req-123",
  "topic": "rag",
  "publish_status": "published",
  "metadata": {
    "partition": 0,
    "offset": 42,
    "timestamp": null
  }
}
```

Validation/runtime failure response (4xx/5xx):
```json
{
  "topic_name": null,
  "status": "error",
  "message": "Validation failed"
}
```

## Startup Behavior Contract

- Service MUST attempt Kafka admin initialization during lifespan startup.
- Service MUST retry on connection failure using configured retry count and timeout.
- Service MUST fail startup if retry limit is exhausted.
- Service SHOULD emit diagnostics per startup connection attempt and final failure reason.
- Service MUST release Kafka admin resources during lifespan shutdown handling.
- Service MUST use FastAPI lifespan events and MUST NOT use deprecated lifecycle handlers such as `on_event`.

## Test-Event Route Enablement Contract

- In `dev` and `test` environments, test-event routes MUST be enabled by default.
- In `prod`, test-event routes MUST remain disabled unless explicit opt-in is configured.
- Route enablement SHOULD be decided during app creation to avoid per-request policy branching.

## Local Infrastructure Contract (Docker Compose)

- Root `docker-compose.yaml` MUST define:
  - Kafka service
  - Kafka UI service
- Kafka service MUST use image `apache/kafka:4.2.1`.
- Kafka UI service MUST use image `provectuslabs/kafka-ui:latest`.
- Kafka UI service MUST be configured to connect to the compose Kafka service.
- Kafka service SHOULD use KRaft-style Apache Kafka environment configuration compatible with
  official container guidance (node id, process roles, listeners, controller quorum voters).

## Scope Boundary

- In-scope APIs: topic creation endpoint and `rag` test-event publish endpoint.
- Out-of-scope: direct invocation of planner/rag agent processing from backend API layer.
