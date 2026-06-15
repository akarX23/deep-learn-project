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

### Session 2026-06-14

- Q: What should the field name be for the source agent in `StreamTokensEventBody`? → A: `from_service` — matches existing `project/events.py` convention, requires no alias, and keeps the schema family consistent.
- Q: Where should `StreamTokensEventBody` be defined, and how does `project/events.py` reference it? → A: Define the single canonical schema in `project/schemas.py`; `project/events.py` imports and re-exports it so any field change is automatically reflected everywhere.
- Q: Which consumer lifecycle model should the backend use for `clarify-user-level` and `stream-tokens`? → A: An `asyncio` background task (`asyncio.create_task`) started inside the FastAPI lifespan — consistent with the existing lifespan pattern and compatible with `python-socketio`.
- Q: Should socket-side event name constants (`clarify-user-level-skt`, `stream-tokens-skt`) be added to the `WebSocketEvents` enum? → A: Yes — add both constants to `WebSocketEvents` in `project/events.py` so frontend and backend share the same names without risk of typos.

### Session 2026-06-13

- Q: Where should the default input factory for the test-event API live? → A: In `backend_service/app/utils.py` — one level above the `api/` package, shared across all app modules.
- Q: What should the `request_id` default value be in the factory? → A: Generate a fresh `uuid4`-based string per call (e.g. `f"test-{uuid4().hex}"`) to guarantee uniqueness.
- Q: Which WebSocket transport should the backend use for frontend connections? → A: Socket.IO via `python-socketio` mounted on the FastAPI ASGI app — native named-event listeners and `emit` match the design.
- Q: How are users and sessions related for event routing? → A: A user may own multiple sessions, but each session is independent; all inbound data carries a `session_id` and is routed independently by it.
- Q: How does the application `session_id` relate to the Socket.IO connection id? → A: They are the same — the `session_id` IS the Socket.IO-generated `sid`.
- Q: What should the shared `project/events.py` define? → A: WebSocket event-name constants and event body schemas; for now include `stream-tokens` with fields `from_service`, `content`, and `metadata`.
- Q: What is the emit function signature? → A: `emit_event(event, payload, session_id)` — routed by `session_id` (== `sid`); `user_id` is not needed for routing.
- Q: Should `project/events.py` also include WebSocket event body schemas? → A: Yes. Define event body schemas there; for now include `stream-tokens` with fields `from_service`, `content`, and `metadata`.
- Q: What additional backend schema should be added to `project/schemas.py`? → A: Add `UserRequest` with fields `user_prompt`, `user_level` (list of strings), and `sid`.
- Q: What validation/error-handling level is required for these new schemas? → A: None for now — no extra exception handling or validation.

- Q: What HTTP endpoint should the user-request ingestion API use? → A: `POST /api/chat/request` for accepting user requests with files from the frontend.
- Q: Should the API enforce file upload limits? → A: Yes, but simply — limit to max 3 files per request and log warnings on overflow; do not reject requests.
- Q: What fields should the planner event schema include? → A: `PlannerRequestEvent` with `user_prompt`, `user_level`, `sid`, and `file_paths` (absolute paths only, no per-file metadata).
- Q: What error response format should the API use? → A: Simple struct: `{error: <message_string>}` with appropriate HTTP status code.
- Q: Should uploaded files be retained or cleaned up? → A: Retain indefinitely in the `./uploads` directory (configurable via env var; cleanup policy deferred to future iteration).
- Q: Should `UserRequest` include a `file_data` field? → A: No. `UserRequest` contains only `user_prompt`, `user_level`, and `sid`; uploaded files are provided via multipart `files` fields and mapped to `PlannerRequestEvent.file_paths`.
- Q: How should the `UserRequest` model be transmitted in the multipart request? → A: As a parsed form model so Swagger exposes separate fields (`user_prompt`, `user_level`, `sid`), plus a separate `files` field for file uploads.

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
4. **Given** a connected session, **When** the backend emits a `stream-tokens` event, **Then** the event name and payload conform to the event constant and body schema defined in `project/events.py`.

---

### User Story 3 - Ingest User Requests with File Uploads and Route to Planner (Priority: P3)

As a frontend user, I need to submit a query along with optional document files to the backend, so that the planner agent can process my request context-aware and generate a structured learning plan.

**Why this priority**: User requests must be routable to the planner agent with uploaded file artifacts. This API bridges the frontend → backend → Kafka path for user-initiated work requests.

**Independent Test**: Can be tested by calling `POST /api/chat/request` with a UserRequest payload and 1–3 file uploads, verifying files are saved to the configured directory, a `PlannerRequestEvent` is published to Kafka with absolute file paths, and the API responds with a confirmation message.

**Acceptance Scenarios**:

1. **Given** a `POST /api/chat/request` request with parsed `UserRequest` form fields (`user_prompt`, `user_level`, `sid`) and 1–3 files in form field `files`, **When** the backend processes the request, **Then** files are saved to the configured uploads directory (default `./uploads`), a `PlannerRequestEvent` is published to Kafka with the absolute file paths, and the API responds with a confirmation message.
2. **Given** files are successfully saved, **When** the API returns, **Then** the response includes a confirmation message indicating the request has been accepted and queued for planner processing.
3. **Given** a request with invalid `UserRequest` data or validation failure, **When** the backend processes the request, **Then** the API returns a 400 error with a simple error message.
4. **Given** files are saved but Kafka publish fails, **When** the API returns, **Then** files remain in the uploads directory (retained indefinitely) and a 500 error is returned with an error message.

---

---

### User Story 4 - Consume Kafka Events and Forward to Frontend Sessions (Priority: P2)

As a frontend client, I need the backend to listen on the `clarify-user-level` and `stream-tokens` Kafka topics and forward their payloads to my active Socket.IO session in real time, so that agent-generated events reach me without polling.

**Why this priority**: Agents publish intermediate results (clarification requests, streamed tokens) to Kafka; the backend is the bridge that translates these Kafka events into Socket.IO emissions routed to the originating session.

**Independent Test**: Can be tested by publishing a `ClarifyUserLevelEvent` to `clarify-user-level` and a `StreamTokensEventBody` to `stream-tokens`, then verifying that the backend consumer emits `clarify-user-level-skt` and `stream-tokens-skt` respectively to the correct Socket.IO session.

**Acceptance Scenarios**:

1. **Given** the backend consumer is running, **When** a `ClarifyUserLevelEvent` arrives on `clarify-user-level`, **Then** the backend validates the payload and emits socket event `clarify-user-level-skt` with the entire object to the session identified by the payload's `sid`.
2. **Given** the backend consumer is running, **When** a `StreamTokensEventBody` arrives on `stream-tokens`, **Then** the backend emits socket event `stream-tokens-skt` with the entire payload to the session identified by the payload's `sid`.
3. **Given** the backend is starting up, **When** the FastAPI lifespan runs, **Then** the `backend-service-consumer` asyncio task is created and begins polling both topics before the service yields.
4. **Given** a `stream-tokens` event is consumed with an unrecognized `sid`, **Then** the emit is silently skipped (TODO: log a warning).

---

### Edge Cases

- `clarify-user-level` consumed but the `sid` in the payload is not present in the connection manager — emit is skipped; handling deferred as a TODO.
- `stream-tokens` consumed but the target session has disconnected — emit is skipped; handling deferred as a TODO.
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
- **FR-021**: Shared WebSocket event contracts MUST be defined in `project/events.py`, importable by both frontend and backend; this module MUST include event-name constants and corresponding event body schemas.
- **FR-022**: `project/events.py` MUST define a `stream-tokens` event constant and re-export the `StreamTokensEventBody` schema from `project/schemas.py`; the schema contains `from_service` (str), `sid` (str), and `data` (dict) — emission logic for prior TODOs is now partially fulfilled by US4.
- **FR-023**: The backend service MUST provide a simple connection manager class that maintains a mapping of `session_id` to connection, exposing minimal `get` and `set` functions; complex exception handling and lifecycle logic are deferred as TODOs.
- **FR-024**: The connection manager MUST key connections by `session_id`, where the `session_id` IS the Socket.IO-generated `sid`. Sessions MUST be treated independently even when a single user owns multiple sessions.
- **FR-025**: WebSocket event listeners MUST be placed in a dedicated `socket.py` file as lightweight listeners; their full behavior is to be implemented later (TODO).
- **FR-026**: `socket.py` MUST provide an `emit_event(event, payload, session_id)` function that emits the given event with the payload to the connection identified by `session_id`.
- **FR-027**: The WebSocket integration MUST favor the simplest approach with minimum boilerplate; advanced exceptional handling and edge cases MUST be deferred via TODO markers.
- **FR-028**: The backend service MUST define a `UserRequest` schema in `project/schemas.py` with fields `user_prompt` (string), `user_level` (list of strings), and `sid` (string).
- **FR-029**: For `stream-tokens` event body schema and `UserRequest`, no additional exception handling or custom validation logic is required in this iteration.
- **FR-030**: The backend service MUST expose a `POST /api/chat/request` endpoint that accepts multipart/form-data with parsed `UserRequest` form fields (`user_prompt`, `user_level`, `sid`) and optional file uploads in form field `files` (max 3 files per request).
- **FR-031**: The user-request API MUST validate the `UserRequest` schema before proceeding; if validation fails, MUST return a 400 response with error message.
- **FR-032**: The user-request API MUST save uploaded files to a directory path configurable via the `UPLOAD_DIR` environment variable, defaulting to `./uploads`.
- **FR-033**: The `./uploads` directory path MUST be added to `.gitignore` to prevent accidental commit of user-uploaded files.
- **FR-034**: The user-request API MUST check that no more than 3 files are included in a single request; if this limit is exceeded, the API logs a warning but does not reject the request (simple check, no validation failure).
- **FR-035**: After successfully saving files, the user-request API MUST publish a `PlannerRequestEvent` to the Kafka `planner` topic with fields `user_prompt`, `user_level`, `sid`, and `file_paths` (absolute paths).
- **FR-036**: The user-request API MUST respond with a confirmation message on successful request acceptance (status 200) or an error message (status 400/500) with structure `{error: <message>}`.
- **FR-037**: The `PlannerRequestEvent` schema MUST be defined in `project/schemas.py` under the planner agent section with fields `user_prompt`, `user_level` (list of strings), `sid`, and `file_paths` (list of absolute paths).
- **FR-038**: The user-request API implementation MUST use simple, minimal code with TODO markers for future enhancements (e.g., file validation, cleanup policies, advanced error handling).
- **FR-039**: No advanced exception handling or validation is required for file uploads in this iteration — focus on core save-and-publish flow.
- **FR-040**: The backend service MUST initialize a Kafka consumer named `backend-service-consumer` subscribed to both the `clarify-user-level` and `stream-tokens` topics.
- **FR-041**: The `backend-service-consumer` MUST run as an `asyncio` background task created via `asyncio.create_task` inside the FastAPI lifespan startup block, before the service yields.
- **FR-042**: On consuming a message from `clarify-user-level`, the backend MUST validate the payload against `ClarifyUserLevelEvent` and emit socket event `clarify-user-level-skt` with the entire validated payload to the session identified by the payload's `sid`.
- **FR-043**: On consuming a message from `stream-tokens`, the backend MUST validate the payload against `StreamTokensEventBody` and emit socket event `stream-tokens-skt` with the entire payload to the session identified by the payload's `sid`.
- **FR-044**: The socket event name constants `CLARIFY_USER_LEVEL_SKT = "clarify-user-level-skt"` and `STREAM_TOKENS_SKT = "stream-tokens-skt"` MUST be added to the `WebSocketEvents` enum in `project/events.py`.
- **FR-045**: `StreamTokensEventBody` MUST be defined in `project/schemas.py` with fields `from_service` (str), `sid` (str), and `data` (dict); `project/events.py` MUST import and re-export it so that any schema change in `schemas.py` is automatically reflected for all importers of `events.py`.
- **FR-046**: The `data` field in `StreamTokensEventBody` MUST be a plain `dict` to accommodate agent-specific payload shapes without requiring per-agent schema variants.

### Key Entities

- **TopicRegistry**: The `project/topics` module providing the list of topic names the system requires; the backend service reads from it at startup without modification.
- **StartupTopicBootstrapResult**: The outcome of the startup topic-creation pass — topics created, topics already existing, and any errors encountered.
- **RAGRequestEvent**: Kafka request payload schema used by the backend test-event API for publishing to topic `rag`; this schema is also used as the request body with defaults applied.
- **TestEventPublishResult**: API response payload containing request identifier, target topic, publish status, and an inline optional Kafka metadata object; no dedicated metadata schema is introduced.
- **KafkaProducerHandle**: Shared producer instance exposed by the Kafka admin layer and reused by the test-events API.
- **TestEventDefaultFactory**: Pure functions in `backend_service/app/utils.py`, one per topic, that return a fully initialized default instance of each topic's input schema. No validators, no exception handling — type-safe initialized values only. The `rag` factory returns `RAGRequestEvent` with a fresh `uuid4`-based `request_id` on every call.
- **WebSocketEvents**: The `WebSocketEvents` enum in `project/events.py` containing all socket event-name constants shared by frontend and backend. Includes: `STREAM_TOKENS = "stream-tokens"`, `CLARIFY_USER_LEVEL_SKT = "clarify-user-level-skt"`, and `STREAM_TOKENS_SKT = "stream-tokens-skt"`. Body schemas are defined in `project/schemas.py` and re-exported from `project/events.py`.
- **StreamTokensEventBody**: Kafka and WebSocket payload schema defined in `project/schemas.py` with fields `from_service` (str — the producing agent), `sid` (str — target session), and `data` (dict — agent-specific payload). Re-exported from `project/events.py`. All agents publishing to the `stream-tokens` Kafka topic MUST conform to this schema.
- **BackendServiceConsumer**: The `asyncio` background task started in the FastAPI lifespan, subscribing to `clarify-user-level` and `stream-tokens` topics under consumer group/client-id `backend-service-consumer`. Routes each consumed message to the matching Socket.IO session via `emit_event`.
- **UserRequest**: Backend request schema in `project/schemas.py` with fields `user_prompt` (string), `user_level` (`list[str]`), and `sid` (string); implemented without additional custom validation or exception handling in this iteration. In the multipart request, this schema is parsed from separate form fields: `user_prompt`, `user_level`, and `sid`.
- **ConnectionManager**: A simple class mapping `session_id` (== Socket.IO `sid`) to its connection, with minimal `get`/`set` functions and no complex logic. Sessions are independent even when owned by the same user.
- **SocketModule**: The dedicated `socket.py` file holding lightweight Socket.IO event listeners (implemented later) and the `emit_event(event, payload, session_id)` function that routes a payload to a session.
- **PlannerRequestEvent**: Kafka event schema for user requests destined for the planner agent, defined in `project/schemas.py` with fields `user_prompt`, `user_level` (`list[str]`), `sid`, and `file_paths` (`list[str]` — absolute paths). No per-file metadata included.
- **UserRequestAPI**: The `POST /api/chat/request` endpoint that accepts multipart/form-data with parsed `UserRequest` form fields (`user_prompt`, `user_level`, `sid`) and form field `files` (1–3 file uploads). Files are saved to the configured `UPLOAD_DIR`, their absolute paths are mapped to `file_paths`, and a `PlannerRequestEvent` is published to Kafka. Responses use simple error struct `{error: <message>}`.
- **UploadDirectory**: The server-side directory for persisting uploaded user files, configurable via the `UPLOAD_DIR` environment variable (default `./uploads`), added to `.gitignore`.

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
- **SC-009**: `project/events.py` defines the `stream-tokens`, `clarify-user-level-skt`, and `stream-tokens-skt` event constants and is importable by both frontend and backend without backend-only dependencies.
- **SC-010**: `project/schemas.py` defines `StreamTokensEventBody` with fields `from_service` (str), `sid` (str), and `data` (dict); `project/events.py` re-exports it via a plain import.
- **SC-017**: On consuming a `clarify-user-level` Kafka message, the backend emits `clarify-user-level-skt` to the Socket.IO session matching the payload's `sid` with the entire `ClarifyUserLevelEvent` payload.
- **SC-018**: On consuming a `stream-tokens` Kafka message, the backend emits `stream-tokens-skt` to the Socket.IO session matching the payload's `sid` with the entire `StreamTokensEventBody` payload.
- **SC-019**: The `backend-service-consumer` asyncio task is created and begins consuming before the FastAPI lifespan yields (i.e., before the service becomes ready).
- **SC-011**: `project/schemas.py` defines `UserRequest` with fields `user_prompt`, `user_level` (`list[str]`), and `sid`.
- **SC-012**: A `POST /api/chat/request` call with valid `UserRequest` provided via parsed form fields (`user_prompt`, `user_level`, `sid`) and 1–3 file uploads (in form field `files`) succeeds: files are saved to the configured directory, a `PlannerRequestEvent` is published to Kafka, and the API responds with a confirmation message.
- **SC-013**: A `POST /api/chat/request` call with invalid `UserRequest` data returns a 400 error with a simple error message.
- **SC-014**: Uploaded files are persisted to the path configured via `UPLOAD_DIR` environment variable (default `./uploads`) and remain accessible for planner processing.
- **SC-015**: The `./uploads` directory is listed in `.gitignore` to prevent accidental version-control commits of uploaded files.
- **SC-016**: The `PlannerRequestEvent` schema is defined in `project/schemas.py` with fields `user_prompt`, `user_level` (`list[str]`), `sid`, and `file_paths` (list of absolute paths).

## Assumptions

- The `project/topics` registry returns a stable, deterministic list of topic names; the backend service treats this list as authoritative and does not filter or transform it.
- Topic partition count and replication factor use safe defaults appropriate for local and development environments; production tuning is out of scope.
- The Kafka admin connectivity and retry behavior from the prior feature iteration remain unchanged; this spec only adds the topic bootstrap step on top.
- Authentication/TLS settings for Kafka are already handled in environment configuration and do not require changes in this scope.
- This feature covers topic creation at startup only; topic deletion, listing, and runtime topic management APIs are out of scope.
- Uploaded files will remain in the `./uploads` directory indefinitely in this iteration; cleanup policies and retention strategies are deferred to future iterations.
- File uploads are limited to a simple count-based check (max 3 per request); advanced file validation (type, size) is deferred.
