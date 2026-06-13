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
- Q: Which WebSocket transport should the backend use for frontend connections? → A: Socket.IO via `python-socketio` mounted on the FastAPI ASGI app — native named-event listeners and `emit` match the design.
- Q: How are users and sessions related for event routing? → A: A user may own multiple sessions, but each session is independent; all inbound data carries a `session_id` and is routed independently by it.
- Q: How does the application `session_id` relate to the Socket.IO connection id? → A: They are the same — the `session_id` IS the Socket.IO-generated `sid`.
- Q: What should the shared `project/events.py` define? → A: Event-name string constants only (a `str` Enum of event names such as `stream-tokens`); payload shapes stay in `schemas.py`.
- Q: What is the emit function signature? → A: `emit_event(event, payload, session_id)` — routed by `session_id` (== `sid`); `user_id` is not needed for routing.

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

### User Story 2 - Real-Time WebSocket Channel for Frontend Session Routing (Priority: P2)

As a frontend client, I need to connect to the backend over a WebSocket so that asynchronous results produced from Kafka events can be streamed back to my specific session in real time, without polling.

**Why this priority**: User requests are asynchronous and processed via Kafka; results must be routed back to the originating session. A WebSocket channel with per-session routing is the delivery mechanism that makes async agent responses usable by the frontend.

**Independent Test**: Can be tested by connecting a Socket.IO client to the backend, capturing the assigned `session_id` (`sid`), and verifying that a payload emitted via `emit_event` with that `session_id` is delivered only to that connection.

**Acceptance Scenarios**:

1. **Given** the backend service is running, **When** a frontend client opens a Socket.IO connection, **Then** the connection is registered in the connection manager keyed by the Socket.IO-generated `session_id` (`sid`).
2. **Given** an active session is registered, **When** the backend calls `emit_event(event, payload, session_id)`, **Then** the payload is emitted to that session only and not to other connected sessions.
3. **Given** a single user has opened multiple independent sessions, **When** an event is emitted for one `session_id`, **Then** only that session receives it — sessions are handled independently.
4. **Given** a connected session, **When** the backend emits a `stream-tokens` event, **Then** the event name and payload match the constant defined in `project/events.py`.

---

### Edge Cases

- One or more topics from the registry already exist in Kafka — creation must be idempotent.
- The project topic registry returns an empty list — startup proceeds without creating any topics.
- Kafka admin connection is established but topic creation encounters a transient broker error — current behavior logs and continues; full error-handling strategy is deferred as a TODO.
- Topics registry grows: new entries added in future must be created automatically on next startup without code changes beyond registry updates.
- `rag` test-event publish succeeds but broker metadata is partially unavailable — API still returns normalized success with nullable metadata fields.
- A `session_id` is not present in the connection manager when `emit_event` is called — handling deferred as a TODO (simplest approach for now).
- A client disconnects mid-stream — cleanup/removal from the connection manager deferred as a TODO.
- Concurrent emits to the same session — ordering/back-pressure concerns deferred as a TODO.
- Authentication/authorization of WebSocket connections — deferred as a TODO.

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
- **FR-020**: The backend service MUST expose a WebSocket interface using Socket.IO (`python-socketio`) mounted on the FastAPI ASGI app, to which the frontend connects.
- **FR-021**: All shared WebSocket event names MUST be defined in a `project/events.py` module as a string Enum of event-name constants, importable by both frontend and backend; payload shapes MUST NOT be added to this module.
- **FR-022**: `project/events.py` MUST define a `stream-tokens` event constant; its emission logic is to be implemented later (TODO).
- **FR-023**: The backend service MUST provide a simple connection manager class that maintains a mapping of `session_id` to connection, exposing minimal `get` and `set` functions; complex exception handling and lifecycle logic are deferred as TODOs.
- **FR-024**: The connection manager MUST key connections by `session_id`, where the `session_id` IS the Socket.IO-generated `sid`. Sessions MUST be treated independently even when a single user owns multiple sessions.
- **FR-025**: WebSocket event listeners MUST be placed in a dedicated `socket.py` file as lightweight listeners; their full behavior is to be implemented later (TODO).
- **FR-026**: `socket.py` MUST provide an `emit_event(event, payload, session_id)` function that emits the given event with the payload to the connection identified by `session_id`.
- **FR-027**: The WebSocket integration MUST favor the simplest approach with minimum boilerplate; advanced exceptional handling and edge cases MUST be deferred via TODO markers.

### Key Entities

- **TopicRegistry**: The `project/topics` module providing the list of topic names the system requires; the backend service reads from it at startup without modification.
- **StartupTopicBootstrapResult**: The outcome of the startup topic-creation pass — topics created, topics already existing, and any errors encountered.
- **RAGRequestEvent**: Kafka request payload schema used by the backend test-event API for publishing to topic `rag`; this schema is also used as the request body with defaults applied.
- **TestEventPublishResult**: API response payload containing request identifier, target topic, publish status, and an inline optional Kafka metadata object; no dedicated metadata schema is introduced.
- **KafkaProducerHandle**: Shared producer instance exposed by the Kafka admin layer and reused by the test-events API.
- **TestEventDefaultFactory**: Pure functions in `backend_service/app/utils.py`, one per topic, that return a fully initialized default instance of each topic's input schema. No validators, no exception handling — type-safe initialized values only. The `rag` factory returns `RAGRequestEvent` with a fresh `uuid4`-based `request_id` on every call.
- **WebSocketEvents**: The shared `project/events.py` module — a string Enum of WebSocket event-name constants (including `stream-tokens`) importable by both frontend and backend. Contains names only, no payload models.
- **ConnectionManager**: A simple class mapping `session_id` (== Socket.IO `sid`) to its connection, with minimal `get`/`set` functions and no complex logic. Sessions are independent even when owned by the same user.
- **SocketModule**: The dedicated `socket.py` file holding lightweight Socket.IO event listeners (implemented later) and the `emit_event(event, payload, session_id)` function that routes a payload to a session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of backend service startups with a reachable Kafka cluster result in all topics from `project/topics` being present in the cluster after startup completes.
- **SC-002**: 100% of backend service startups where all required topics already exist complete the topic bootstrap step without errors or service interruption.
- **SC-003**: The topic bootstrap step completes within 5 seconds in a local development environment with a connected Kafka cluster.
- **SC-004**: Startup logs always include a record of the topic bootstrap attempt and its outcome.
- **SC-005**: 100% of successful `rag` test-event API calls return a normalized publish-result envelope with request_id, topic, and publish_status.
- **SC-006**: For successful `rag` test-event API calls, Kafka broker metadata fields are returned whenever the producer result exposes them.
- **SC-007**: A frontend Socket.IO client can establish a WebSocket connection to the backend and be registered in the connection manager keyed by its `session_id` (`sid`).
- **SC-008**: A payload emitted via `emit_event(event, payload, session_id)` is delivered only to the connection mapped to that `session_id` and to no other session.
- **SC-009**: The shared `project/events.py` defines the `stream-tokens` event constant and is importable by both frontend and backend without backend-only dependencies.

## Assumptions

- The `project/topics` registry returns a stable, deterministic list of topic names; the backend service treats this list as authoritative and does not filter or transform it.
- Topic partition count and replication factor use safe defaults appropriate for local and development environments; production tuning is out of scope.
- The Kafka admin connectivity and retry behavior from the prior feature iteration remain unchanged; this spec only adds the topic bootstrap step on top.
- Authentication/TLS settings for Kafka are already handled in environment configuration and do not require changes in this scope.
- This feature covers topic creation at startup only; topic deletion, listing, and runtime topic management APIs are out of scope.
