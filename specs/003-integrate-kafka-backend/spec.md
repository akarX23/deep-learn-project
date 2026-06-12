# Feature Specification: Backend Kafka Startup Topic Bootstrap

**Feature Branch**: `001-build-rag-retrieval-agent`  
**Created**: 2026-06-12  
**Status**: Draft  
**Input**: User description: "The backend service should get the topic list from project/topics and create all the topics on start-up. Any additional validation checks can be put as TODOs. The core functionality of creating topics only should be integrated into the start-up function."

## Clarifications

### Session 2026-06-08

- Q: How should Kafka environment variables be loaded at runtime? → A: Load from `.env.local` when present, then allow already-initialized process environment variables to override.
- Q: Which FastAPI lifecycle mechanism should be used? → A: Use FastAPI lifespan events only; do not use deprecated lifecycle APIs.

### Session 2026-06-12

- Q: Where should topic names be sourced? → A: Read from `project/topics` module (the centralized topic registry) — not from environment variables or external APIs.
- Q: What happens if a topic already exists? → A: Topic creation should be idempotent — already-existing topics are not treated as errors.
- Q: What level of validation is required now? → A: Only the core topic-creation behavior is required now; advanced validation (result inspection, per-topic error handling, health assertions) is deferred with TODO markers.

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

### Key Entities

- **TopicRegistry**: The `project/topics` module providing the list of topic names the system requires; the backend service reads from it at startup without modification.
- **StartupTopicBootstrapResult**: The outcome of the startup topic-creation pass — topics created, topics already existing, and any errors encountered.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of backend service startups with a reachable Kafka cluster result in all topics from `project/topics` being present in the cluster after startup completes.
- **SC-002**: 100% of backend service startups where all required topics already exist complete the topic bootstrap step without errors or service interruption.
- **SC-003**: The topic bootstrap step completes within 5 seconds in a local development environment with a connected Kafka cluster.
- **SC-004**: Startup logs always include a record of the topic bootstrap attempt and its outcome.

## Assumptions

- The `project/topics` registry returns a stable, deterministic list of topic names; the backend service treats this list as authoritative and does not filter or transform it.
- Topic partition count and replication factor use safe defaults appropriate for local and development environments; production tuning is out of scope.
- The Kafka admin connectivity and retry behavior from the prior feature iteration remain unchanged; this spec only adds the topic bootstrap step on top.
- Authentication/TLS settings for Kafka are already handled in environment configuration and do not require changes in this scope.
- This feature covers topic creation at startup only; topic deletion, listing, and runtime topic management APIs are out of scope.
