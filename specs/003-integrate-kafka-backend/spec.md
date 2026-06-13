# Feature Specification: Backend Kafka Startup Topic Bootstrap

**Feature Branch**: `003-integrate-kafka-backend`  
**Created**: 2026-06-12  
**Status**: Draft  
**Input**: User description: "The backend service should get the topic list from project/topics and create all the topics on start-up. Any additional validation checks can be put as TODOs. The core functionality of creating topics only should be integrated into the start-up function."

## Clarifications

### Session 2026-06-08
- Q: Which FastAPI lifecycle mechanism should be used? → A: Use FastAPI lifespan events only; do not use deprecated lifecycle APIs.

### Session 2026-06-12

- Q: Where should topic names be sourced? → A: Read from `project/topics` module (the centralized topic registry) — not from environment variables or external APIs.
- Q: What happens if a topic already exists? → A: Topic creation should be idempotent — already-existing topics are not treated as errors.
- Q: What level of validation is required now? → A: Only the core topic-creation behavior is required now; advanced validation (result inspection, per-topic error handling, health assertions) is deferred with TODO markers.
- Q: How should the backend test-event API payload for `rag` be supplied? → A: Use the full `RAGRequestEvent` schema as the request body with default values; no separate override wrapper or merge step is needed.
- Q: In which environments should test-event APIs be enabled? → A: Enabled by default in dev/test only; production requires explicit configuration opt-in.
- Q: What should the `rag` test-event API return on publish success? → A: Return a normalized publish-result envelope and include Kafka broker metadata when available.
- Q: Should test-event metadata require new schema models? → A: No. Keep test-event metadata inline in the response payload; do not add additional schema models for metadata.
- Q: Where should the shared producer live? → A: Create the single producer in the Kafka admin layer and expose it there for the test-events API to reuse.

### Session 2026-06-13

- Q: Where should the default input factory for the test-event API live? → A: In `backend_service/app/utils.py` — one level above the `api/` package, shared across all app modules.
- Q: What should the `request_id` default value be in the factory? → A: Generate a fresh `uuid4`-based string per call (e.g. `f"test-{uuid4().hex}"`) to guarantee uniqueness.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bootstrap Kafka Topics from Project Registry on Startup (Priority: P1)

As a platform developer, I need the backend service to automatically create all required Kafka topics on startup by reading them from the shared project topic registry, so that no external provisioning step is needed before agents can communicate.

**Why this priority**: Without the required topics present, agents cannot produce or consume events. Automating topic creation on startup eliminates a manual setup step and makes the system self-provisioning.

**Independent Test**: Can be fully tested by starting the backend service against a connected Kafka cluster and verifying that all topics returned by `project/topics` are present in the cluster after startup completes.

**Acceptance Scenarios**:

1. **Given** a connected Kafka cluster and a populated `project/topics` registry, **When** the backend service starts, **Then** all topics returned by the registry are created before the service becomes ready.
2. **Given** topics that already exist in Kafka, **When** the backend service starts, **Then** the startup topic-creation step completes without errors — existing topics are not treated as failures.
3. **Given** a Kafka cluster that is not reachable, **When** the backend service starts, **Then** Kafka admin connection is retried per configured limits and startup fails with a clear message if the cluster remains unavailable.

---

### Edge Cases

- One or more topics from the registry already exist in Kafka — creation must be idempotent.
- The project topic registry returns an empty list — startup proceeds without creating any topics.
- Kafka admin connection is established but topic creation encounters a transient broker error — current behavior logs and continues; full error-handling strategy is deferred as a TODO.
- Topics registry grows: new entries added in future must be created automatically on next startup without code changes beyond registry updates.
- `rag` test-event publish succeeds but broker metadata is partially unavailable — API still returns normalized success with nullable metadata fields.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend service MUST read the full list of required Kafka topics from the shared `project/topics` registry module on startup.
- **FR-002**: The backend service MUST create all topics returned by `project/topics` using the Kafka admin client during the startup lifecycle function.
- **FR-003**: The topic creation step MUST be idempotent — topics that already exist MUST NOT cause startup to fail.
- **FR-004**: The topic creation step MUST be integrated into the existing FastAPI lifespan startup function, after Kafka admin connectivity is established.
- **FR-005**: The backend service MUST use FastAPI lifespan events (non-deprecated API) to manage the startup sequence: admin connect → topic bootstrap → yield → admin close.
- **FR-006**: Topic-creation logic MUST NOT include advanced per-topic validation, result assertion, or health-check behavior in this iteration — these concerns MUST be marked as TODO for later implementation.
- **FR-007**: The backend service MUST log a clear message for the topic bootstrap step at startup, including the list of topics attempted.
- **FR-008**: The backend service MUST continue startup even if topic bootstrap encounters non-fatal errors, and MUST log any such errors clearly.
- **FR-009**: The backend service MUST expose a test-event API route for topic `rag` that publishes events to Kafka using the `RAGRequestEvent` contract from `project/schemas.py`.
- **FR-010**: The `rag` test-event API MUST accept the full `RAGRequestEvent` schema as the request body, using default field values where applicable, with no separate override wrapper or merge step.
- **FR-011**: The `rag` test-event API MUST validate the request body against `RAGRequestEvent` before publish.
- **FR-012**: The backend service MUST NOT call agent services directly from this API; it only publishes contract-valid test events to Kafka topics.
- **FR-013**: Test-event APIs MUST be enabled by default in development and test environments.
- **FR-014**: In production environments, test-event APIs MUST require explicit configuration opt-in before routes are enabled.
- **FR-015**: On successful `rag` test-event publish, the backend service MUST return a normalized response envelope that includes request correlation and publish status.
- **FR-016**: The successful `rag` test-event response MUST include Kafka publish metadata (for example partition/offset/timestamp) when available from the producer result.
- **FR-017**: The backend service MUST use a single shared producer owned by the Kafka admin layer; the test-events API MUST reuse that producer rather than constructing a separate one in main.py.
- **FR-018**: A per-topic default input factory function MUST be provided in `backend_service/app/utils.py`; each factory returns a fully initialized, type-safe instance of the topic's input schema with sensible default values and no validators or exception handling.
- **FR-019**: The `rag` default factory in `backend_service/app/utils.py` MUST return a `RAGRequestEvent` with a dynamically generated `request_id` (using `uuid4`) and all other required fields set to representative default values.

### Key Entities

- **TopicRegistry**: The `project/topics` module providing the list of topic names the system requires; the backend service reads from it at startup without modification.
- **StartupTopicBootstrapResult**: The outcome of the startup topic-creation pass — topics created, topics already existing, and any errors encountered.
- **RAGRequestEvent**: Kafka request payload schema used by the backend test-event API for publishing to topic `rag`; this schema is also used as the request body with defaults applied.
- **TestEventPublishResult**: API response payload containing request identifier, target topic, publish status, and an inline optional Kafka metadata object; no dedicated metadata schema is introduced.
- **KafkaProducerHandle**: Shared producer instance exposed by the Kafka admin layer and reused by the test-events API.
- **TestEventDefaultFactory**: Pure functions in `backend_service/app/utils.py`, one per topic, that return a fully initialized default instance of each topic's input schema. No validators, no exception handling — type-safe initialized values only. The `rag` factory returns `RAGRequestEvent` with a fresh `uuid4`-based `request_id` on every call.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of backend service startups with a reachable Kafka cluster result in all topics from `project/topics` being present in the cluster after startup completes.
- **SC-002**: 100% of backend service startups where all required topics already exist complete the topic bootstrap step without errors or service interruption.
- **SC-003**: The topic bootstrap step completes within 5 seconds in a local development environment with a connected Kafka cluster.
- **SC-004**: Startup logs always include a record of the topic bootstrap attempt and its outcome.
- **SC-005**: 100% of successful `rag` test-event API calls return a normalized publish-result envelope with request_id, topic, and publish_status.
- **SC-006**: For successful `rag` test-event API calls, Kafka broker metadata fields are returned whenever the producer result exposes them.

## Assumptions

- The `project/topics` registry returns a stable, deterministic list of topic names; the backend service treats this list as authoritative and does not filter or transform it.
- Topic partition count and replication factor use safe defaults appropriate for local and development environments; production tuning is out of scope.
- The Kafka admin connectivity and retry behavior from the prior feature iteration remain unchanged; this spec only adds the topic bootstrap step on top.
- Authentication/TLS settings for Kafka are already handled in environment configuration and do not require changes in this scope.
- This feature covers topic creation at startup only; topic deletion, listing, and runtime topic management APIs are out of scope.
