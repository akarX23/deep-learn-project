# Research: Kafka Backend Integration Service

## Decision 1: Kafka Admin Client Library
- Decision: Use `kafka-python` `KafkaAdminClient` for topic management and broker connectivity checks.
- Rationale: Mature Python client, straightforward admin APIs, and good compatibility with FastAPI sync startup hooks.
- Alternatives considered: `confluent-kafka` admin API (high performance but heavier native dependency requirements), `aiokafka` (async-first, unnecessary for current sync admin scope).

## Decision 2: FastAPI Startup Connectivity Strategy
- Decision: Initialize Kafka admin client in FastAPI startup event and retry connection according to env-driven retry count and retry timeout.
- Rationale: Ensures service readiness semantics are explicit and predictable before serving API calls.
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
- Decision: Provide root-level `docker-compose.yaml` with Kafka and Kafka UI services; use `provectuslabs/kafka-ui:latest` and configure Kafka UI to connect to the Kafka service.
- Rationale: Preserves simple local bootstrap while adding immediate topic/cluster visibility and matching clarified requirement.
- Alternatives considered: Kafka-only compose (insufficient after clarification), include backend service in compose (not requested), include Zookeeper-based topology (extra complexity with modern KRaft support available).

## Decision 6: Topic Creation Idempotency Behavior
- Decision: Treat existing-topic requests as deterministic non-fatal responses (`already_exists`) rather than hard failures.
- Rationale: Improves automation safety for repeated provisioning calls.
- Alternatives considered: Raise error on duplicate topic creation (less user-friendly for internal automation).

## Decision 7: Retry Configuration Model
- Decision: Use explicit environment variables for startup retry count and retry timeout seconds with strict validation.
- Rationale: Makes startup behavior measurable and tunable per environment.
- Alternatives considered: Hardcoded retry values (inflexible), exponential backoff with extra knobs (not required for first version).

## Decision 8: Lifecycle Event Strategy
- Decision: Use FastAPI lifecycle events to perform Kafka admin initialization at startup and connection cleanup at shutdown.
- Rationale: Keeps readiness and teardown behavior explicit and centralized at app boundary.
- Alternatives considered: Lazy connection creation on first request (delayed failures), module-level singleton setup (harder to test and less deterministic teardown).

## Decision 9: Global Exception Handling Strategy
- Decision: Add global FastAPI exception handlers for request validation errors, HTTP exceptions, and unhandled exceptions, returning one structured error envelope.
- Rationale: Provides consistent client-facing error shape and simplifies observability/consumer parsing.
- Alternatives considered: Per-route error shaping only (inconsistent coverage), default framework error bodies (inconsistent contract).

## Final Tradeoffs and Validation Notes

- Implementation keeps a synchronous startup path and synchronous admin API calls to reduce complexity for the first delivery.
- FastAPI `on_event` hooks are used for clear startup/shutdown behavior; migration to lifespan can be scheduled later if deprecation cleanup is prioritized.
- Local baseline from test harness:
	- Startup with one retry and 1s retry timeout: ~1007 ms.
	- Topic creation endpoint p95 (30 requests, mocked admin): ~2.60 ms.
