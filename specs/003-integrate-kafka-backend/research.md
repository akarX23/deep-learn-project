# Research: Kafka Backend Integration Service

## Decision 1: Kafka Admin Client Library
- Decision: Use `kafka-python` `KafkaAdminClient` for topic management and broker connectivity checks.
- Rationale: Mature Python client, straightforward admin APIs, and good compatibility with FastAPI sync startup hooks.
- Alternatives considered: `confluent-kafka` admin API (high performance but heavier native dependency requirements), `aiokafka` (async-first, unnecessary for current sync admin scope).

## Decision 2: FastAPI Startup Connectivity Strategy
- Decision: Initialize Kafka admin client during FastAPI lifespan startup and retry connection according to env-driven retry count and retry timeout.
- Rationale: Ensures service readiness semantics are explicit and predictable before serving API calls while staying on non-deprecated framework APIs.
- Alternatives considered: Lazy-initialize on first API call (delays failure and harms reliability), background retry after startup (unclear readiness state).

## Decision 3: Environment Loading Precedence
- Decision: Load `.env.local` when present, then allow already-initialized process environment variables to override file values.
- Rationale: Supports local defaults while preserving container/orchestrator-injected runtime configuration.
- Alternatives considered: `.env.local` only (breaks deployment injection), process env only (worse local developer ergonomics).

## Decision 4: API Scope Boundary
- Decision: Expose only one topic-creation API in this feature; no message relay, producer, or consumer endpoints.
- Rationale: Keeps service responsibility minimal and aligned to requested admin/provisioning use case.
- Alternatives considered: Broader Kafka management API set (out of scope), inter-service proxy capabilities (explicitly rejected).

## Decision 5: Docker Compose Topology
- Decision: Provide root-level `docker-compose.yaml` with Kafka and Kafka UI services; pin Kafka to `apache/kafka:4.2.1`, keep Kafka UI on `provectuslabs/kafka-ui:latest`, and wire Kafka UI to `kafka:9092`.
- Rationale: Satisfies clarified requirement for Apache Kafka image usage while retaining deterministic local reproducibility and immediate observability.
- Alternatives considered: Bitnami Kafka image (rejected to avoid image-family drift from clarified requirement), `apache/kafka:latest` (rejected to avoid non-deterministic upgrades), Kafka-only compose (insufficient after Kafka UI clarification).

## Decision 6: Apache Kafka KRaft Compose Environment
- Decision: Use KRaft-oriented environment keys aligned with Apache Kafka container guidance (`KAFKA_NODE_ID`, `KAFKA_PROCESS_ROLES`, listeners, quorum voters, replication-factor defaults).
- Rationale: Keeps compose bootstrap self-contained without ZooKeeper, consistent with modern Kafka single-node local development setup.
- Alternatives considered: ZooKeeper-based setup (unnecessary complexity for current scope), vendor-specific env key families not matching Apache Kafka docs.

## Decision 7: Topic Creation Idempotency Behavior
- Decision: Treat existing-topic requests as deterministic non-fatal responses (`already_exists`) rather than hard failures.
- Rationale: Improves automation safety for repeated provisioning calls.
- Alternatives considered: Raise error on duplicate topic creation (less user-friendly for internal automation).

## Decision 8: Retry Configuration Model
- Decision: Use explicit environment variables for startup retry count and retry timeout seconds with strict validation.
- Rationale: Makes startup behavior measurable and tunable per environment.
- Alternatives considered: Hardcoded retry values (inflexible), exponential backoff with extra knobs (not required for first version).

## Decision 9: Lifecycle Event Strategy
- Decision: Use FastAPI lifespan events to perform Kafka admin initialization at startup and connection cleanup at shutdown; avoid deprecated `on_event` handlers.
- Rationale: Keeps readiness and teardown behavior explicit, centralized at app boundary, and aligned with current framework guidance.
- Alternatives considered: Deprecated `on_event` lifecycle handlers (rejected due to deprecation), lazy connection creation on first request (delayed failures), module-level singleton setup (harder to test and less deterministic teardown).

## Decision 10: Global Exception Handling Strategy
- Decision: Add global FastAPI exception handlers for request validation errors, HTTP exceptions, and unhandled exceptions, returning one structured error envelope.
- Rationale: Provides consistent client-facing error shape and simplifies observability/consumer parsing.
- Alternatives considered: Per-route error shaping only (inconsistent coverage), default framework error bodies (inconsistent contract).

## Final Tradeoffs and Validation Notes

- Implementation keeps a synchronous startup path and synchronous admin API calls to reduce complexity for the first delivery.
- Lifecycle management uses FastAPI lifespan events to avoid deprecated APIs and keep startup/shutdown orchestration in one place.
- Local baseline from test harness:
	- Startup with one retry and 1s retry timeout: ~1007 ms.
	- Topic creation endpoint p95 (30 requests, mocked admin): ~2.60 ms.
