# Tasks: Backend Kafka Startup Bootstrap + RAG Test-Event API + WebSocket Channel

**Input**: Design documents from `/specs/003-integrate-kafka-backend/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include test tasks by default. Omit tests only when the specification explicitly documents why a test type is not applicable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Shared contract and dependency groundwork for the backend Kafka and WebSocket features

- [ ] T001 [P] Add `python-socketio` to `requirements.txt` so `backend_service` can mount a Socket.IO ASGI server
- [ ] T002 [P] Create `project/events.py` with shared WebSocket event-name constants, including `STREAM_TOKENS`, as a `str` Enum

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core app plumbing that must exist before any story-specific integration work can be completed

**Checkpoint**: The backend app can host optional Socket.IO wiring while preserving the existing Kafka startup lifecycle and API router behavior

- [ ] T003 [P] Add `backend_service/tests/conftest.py` fixtures for reusable FastAPI app, Kafka admin, and Socket.IO test doubles used by later story tests
- [ ] T004 [P] Update `backend_service/app/main.py` application factory to support mounting the Socket.IO ASGI app without changing the existing Kafka startup flow or topics router registration
- [ ] T005 [P] Add `backend_service/app/connection_manager.py` and `backend_service/app/socket.py` scaffolding for later session routing and emit wiring, keeping behavior minimal for now

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Bootstrap Kafka Topics from Project Registry on Startup (Priority: P1) 🎯 MVP

**Goal**: Automatically create all Kafka topics from `project/topics` during backend startup

**Independent Test**: Start the backend service against a reachable Kafka cluster and verify that all topics returned by `project.topics.get_all_topic_names()` exist after startup completes

### Tests for User Story 1

- [ ] T006 [P] [US1] Extend `backend_service/tests/test_startup.py` with bootstrap success coverage for topic creation, idempotent existing-topic handling, and empty-registry behavior
- [ ] T007 [P] [US1] Extend `backend_service/tests/test_startup.py` with startup retry and failure coverage for unreachable Kafka and exhausted retry limits

### Implementation for User Story 1

- [ ] T008 [US1] Extend `backend_service/app/kafka_admin.py` with `bootstrap_topics()` aggregation that records created topics, already-existing topics, and non-fatal errors in `StartupTopicBootstrapResult`
- [ ] T009 [US1] Wire `project.topics.get_all_topic_names()` into `backend_service/app/main.py` lifespan so topic bootstrap runs after Kafka admin connect and before `yield`
- [ ] T010 [US1] Update `backend_service/app/main.py` startup logging and `backend_service/app/kafka_admin.py` warning paths so bootstrap attempts, summaries, and deferred TODO behavior are visible in logs

**Checkpoint**: User Story 1 should now bootstrap Kafka topics on startup and remain independently testable

---

## Phase 4: User Story 2 - Publish RAG Test Events Through Backend API (Priority: P2)

**Goal**: Expose a gated backend API that publishes contract-valid `rag` test events to Kafka with a normalized success envelope

**Independent Test**: With test-event routes enabled, POSTing to `/api/v1/test-events/rag` publishes a valid `RAGRequestEvent` and returns the publish result envelope with Kafka metadata when available

### Tests for User Story 2

- [ ] T011 [P] [US2] Add contract coverage in `backend_service/tests/test_test_events_api.py` for `/api/v1/test-events/rag`, including environment gating, direct RAG request-body validation, and success response shape
- [ ] T012 [P] [US2] Add unit coverage in `backend_service/tests/test_utils.py` for `default_rag_test_event()` returning unique `uuid4`-backed request IDs and representative defaults

### Implementation for User Story 2

- [ ] T013 [US2] Create `backend_service/app/utils.py` with `default_rag_test_event() -> RAGRequestEvent` using `uuid4().hex` for `request_id` and representative defaults for all required fields
- [ ] T014 [US2] Implement the `rag` test-event router in `backend_service/app/api/test_events.py` with direct `RAGRequestEvent` request-body handling and publish validation before publish
- [ ] T015 [US2] Update `backend_service/app/main.py` and `backend_service/app/config.py` so test-event routes are enabled by default in dev/test and require explicit opt-in in production
- [ ] T016 [US2] Map Kafka producer acknowledgements to the normalized inline test-event response payload in `backend_service/app/api/test_events.py`, including optional metadata fields when available from the shared producer

**Checkpoint**: User Story 2 should now publish rag test events through a gated API and remain independently testable

---

## Phase 5: User Story 3 - Real-Time WebSocket Channel for Frontend Session Routing (Priority: P3)

**Goal**: Mount a Socket.IO channel so the frontend can connect and receive Kafka-driven updates routed by `session_id`

**Independent Test**: Connect a Socket.IO client, capture the assigned `sid`, and verify that `emit_event(event, payload, session_id)` delivers only to that session while `project/events.py` exposes the shared `STREAM_TOKENS` constant

### Tests for User Story 3

- [ ] T017 [P] [US3] Add connection-manager coverage in `backend_service/tests/test_connection_manager.py` for minimal get/set behavior keyed by `session_id` and independent sessions
- [ ] T018 [P] [US3] Add Socket.IO coverage in `backend_service/tests/test_socket.py` for connect registration, `emit_event` routing by `session_id`, and `STREAM_TOKENS` constant usage from `project/events.py`

### Implementation for User Story 3

- [ ] T019 [P] [US3] Create `backend_service/app/connection_manager.py` with a minimal `ConnectionManager` class exposing `get` and `set`
- [ ] T020 [P] [US3] Create `backend_service/app/socket.py` with the Socket.IO server, lightweight listeners, and `emit_event(event, payload, session_id)`
- [ ] T021 [US3] Mount the Socket.IO ASGI app in `backend_service/app/main.py` and register the shared connection manager for session routing
- [ ] T022 [US3] Add TODO-marked stubs in `backend_service/app/socket.py` for disconnect cleanup, missing-session handling, auth, and back-pressure edge cases

**Checkpoint**: User Story 3 should now provide the session-routed WebSocket channel and remain independently testable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish, verify, and harden the feature across all user stories

- [ ] T023 [P] Validate the full `backend_service` test suite with `pytest backend_service/tests -q` and confirm all tests including `test_utils.py`, `test_socket.py`, and `test_connection_manager.py` pass
- [ ] T024 [P] Run `ruff check project backend_service` and `ruff format --check project backend_service` to confirm code quality and formatting
- [ ] T025 [P] Run `python -m compileall project backend_service` to confirm syntax integrity
- [ ] T026 [P] Update `specs/003-integrate-kafka-backend/quickstart.md` to reflect the final startup, rag publish, and WebSocket connection/emit flows
- [ ] T027 [P] Review logging and docstrings in `backend_service/app/main.py`, `backend_service/app/api/test_events.py`, `backend_service/app/socket.py`, `backend_service/app/kafka_admin.py`, `backend_service/app/utils.py`, and `project/events.py` for clarity and maintainability

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks user story implementation
- **User Stories (Phase 3+)**: Depend on Foundations being complete
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational phase completion - does not depend on US2 or US3
- **User Story 2 (P2)**: Can start after Foundational phase completion - does not depend on US1 or US3
- **User Story 3 (P3)**: Can start after Foundational phase completion - does not depend on US1 or US2

### Within Each User Story

- Tests should be written before implementation when behavior changes
- Shared contracts and settings before route/service wiring
- Service logic before endpoint wiring
- Core implementation before integration and polish

### Parallel Opportunities

- Setup tasks T001 and T002 can run in parallel
- Foundational tasks T003, T004, and T005 can be staged independently if they touch different files
- US1 tests T006 and T007 can be worked on in parallel if split across files or by separate contributors
- US2 tests T011 and T012 can be worked on in parallel if split across files or by separate contributors
- US2 implementation tasks T013 through T016 touch different files and can be staged independently once shared contracts are in place
- US3 tests T017 and T018 can be worked on in parallel if split across files or by separate contributors
- US3 implementation tasks T019 through T022 touch different files and can be staged independently once shared contracts are in place
- Polish tasks T023 through T027 can be run in parallel where they do not touch the same files

---

## Parallel Example: User Story 1

```bash
Task: "Extend backend_service/tests/test_startup.py with bootstrap success coverage for topic creation, idempotent existing-topic handling, and empty-registry behavior"
Task: "Extend backend_service/tests/test_startup.py with startup retry and failure coverage for unreachable Kafka and exhausted retry limits"
Task: "Extend backend_service/app/kafka_admin.py with bootstrap_topics() aggregation that records created topics, already-existing topics, and non-fatal errors in StartupTopicBootstrapResult"
```

## Parallel Example: User Story 2

```bash
Task: "Add contract coverage in backend_service/tests/test_test_events_api.py for /api/v1/test-events/rag, including environment gating, direct RAG request-body validation, and success response shape"
Task: "Add unit coverage in backend_service/tests/test_utils.py for default_rag_test_event() returning unique uuid4-backed request IDs and representative defaults"
Task: "Create backend_service/app/utils.py with default_rag_test_event() -> RAGRequestEvent"
```

## Parallel Example: User Story 3

```bash
Task: "Add connection-manager coverage in backend_service/tests/test_connection_manager.py for minimal get/set behavior keyed by session_id and independent sessions"
Task: "Add Socket.IO coverage in backend_service/tests/test_socket.py for connect registration, emit_event routing by session_id, and STREAM_TOKENS constant usage from project/events.py"
Task: "Create backend_service/app/connection_manager.py with a minimal ConnectionManager class exposing get and set"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate topic bootstrap behavior independently

### Incremental Delivery

1. Complete Setup + Foundational
2. Deliver User Story 1 and validate startup topic creation
3. Deliver User Story 2 and validate rag test-event publishing
4. Deliver User Story 3 and validate the WebSocket session-routing path
5. Run polish checks and update quickstart/documentation outputs

### Parallel Team Strategy

With multiple developers:

1. One developer can finish User Story 1 while another prepares User Story 2 test coverage
2. Once shared contracts are merged, one developer can wire the rag router while another updates route gating and response mapping
3. A separate developer can deliver the WebSocket channel by implementing connection management, Socket.IO wiring, and emit routing in parallel with the rag API work
4. Finish with shared verification, linting, compile checks, and quickstart validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing behavior changes
- Record evidence for logging clarity and performance validation before completion
- Commit after each logical group when appropriate
- Avoid vague tasks, same-file parallel conflicts, and cross-story dependencies that break independence
