---
description: "Task list for Feature 003: Backend Kafka Integration + WebSocket Channel"
---

# Tasks: Backend Kafka Startup Bootstrap + RAG Test-Event API + WebSocket Channel

**Feature**: 003-integrate-kafka-backend  
**Branch**: `003-integrate-kafka-backend`  
**Input**: Design documents from `/specs/003-integrate-kafka-backend/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Note**: Tests included as per feature requirements; implementation tasks follow for each user story.
**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize project dependencies and shared modules

- [ ] T001 Install/verify Python 3.11+ and dependencies (kafka-python, python-socketio, etc.) from requirements.txt
- [ ] T002 Verify pytest and ruff are configured in pytest.ini and via requirements.txt
- [ ] T003 [P] Create .gitignore entry for ./uploads directory (file storage for user requests)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required before any user story can start

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Add `StreamTokensEventBody` Pydantic model to project/schemas.py with fields (from_service: str, sid: str, data: dict[str, Any])
- [ ] T005 [P] Add `ClarifyUserLevelEvent` Pydantic model to project/schemas.py with fields (request_id: str, user_prompt: str, sid: str, reason: str | None)
- [ ] T006 [P] Add `UserRequest` Pydantic model to project/schemas.py with fields (user_prompt: str, user_level: list[str], sid: str)
- [ ] T007 [P] Create `WebSocketEvents` enum in project/events.py with constants STREAM_TOKENS, CLARIFY_USER_LEVEL_SKT, STREAM_TOKENS_SKT
- [ ] T008 [P] Add re-export pattern in project/events.py: re-export StreamTokensEventBody and ClarifyUserLevelEvent from project.schemas
- [ ] T009 Update project/topics.py to include Kafka topic registry with all required topics (rag, rag-complete, clarify-user-level, stream-tokens)
- [ ] T010 [P] Create backend_service/app/config.py with UPLOAD_DIR, TEST_ROUTES_ENABLED (env-based), and Kafka bootstrap server settings
- [ ] T011 Add `TestEventPublishResult` Pydantic model to project/schemas.py with fields (request_id: str, topic: str, publish_status: str, metadata: dict[str, int | None] | None)
- [ ] T012 Create backend_service/app/utils.py with factory function `default_rag_test_event()` returning RAGRequestEvent with test defaults

**Checkpoint**: All schemas, enums, and configs defined - ready for user story implementation

---

## Phase 3: User Story 1 - Bootstrap Kafka Topics from Project Registry on Startup (Priority: P1) 🎯

**Goal**: Automatically create required Kafka topics on application startup with idempotent behavior

**Independent Test**: Verify that on startup, all topics from project/topics.py are created or already exist; repeated startups do not error

### Tests for User Story 1

- [ ] T013 [P] [US1] Add test_kafka_admin.py in backend_service/tests/ to verify KafkaAdminService.bootstrap_topics() behavior: topics created on first run, idempotent on second run
- [ ] T014 [P] [US1] Add test_startup.py in backend_service/tests/ to verify FastAPI lifespan startup sequence: admin connect → topic bootstrap → success log output

### Implementation for User Story 1

- [ ] T015 [P] [US1] Extend backend_service/app/kafka_admin.py: add KafkaAdminService class with bootstrap_topics() method that creates topics from project.topics registry using AdminClient.create_topics() with NewTopic descriptors
- [ ] T016 [P] [US1] Implement idempotent topic creation: catch TopicAlreadyExistsError and other recoverable errors, return StartupTopicBootstrapResult with created/already_existed/errors lists
- [ ] T017 [US1] Update backend_service/app/main.py lifespan startup: instantiate KafkaAdminService, call bootstrap_topics(), log results (topic count summaries), store admin reference in app state
- [ ] T018 [US1] Add logging to bootstrap_topics() with request correlation and per-topic debug output (created vs. already exists)

**Checkpoint**: Topic bootstrap runs on startup and logs outcome; all required topics exist after first run

---

## Phase 4: User Story 2 - Real-Time WebSocket Channel for Frontend Session Routing (Priority: P2)

**Goal**: Establish WebSocket connectivity with Socket.IO and per-session routing capability

**Independent Test**: Verify frontend can connect via Socket.IO, server assigns and stores session ID, emit_event routes messages to correct session only

### Tests for User Story 2

- [ ] T019 [P] [US2] Add test_connection_manager.py in backend_service/tests/ to verify ConnectionManager.set/get behavior: store and retrieve connections by session_id, return None for unknown session_id
- [ ] T020 [P] [US2] Add test_socket.py in backend_service/tests/ to verify Socket.IO server instantiation and emit_event function: emit to known session succeeds, emit to unknown session is skipped

### Implementation for User Story 2

- [ ] T021 [P] [US2] Create backend_service/app/connection_manager.py with ConnectionManager class: methods set(session_id, connection) and get(session_id) using dict storage
- [ ] T022 [P] [US2] Create backend_service/app/socket.py with Socket.IO server instantiation (`socketio.AsyncServer` with async_mode='asgi')
- [ ] T023 [P] [US2] Implement connect listener in socket.py: register sid in ConnectionManager (TODO: full listener body)
- [ ] T024 [P] [US2] Implement disconnect listener in socket.py: lightweight stub (TODO: cleanup deferred)
- [ ] T025 [US2] Implement emit_event(event, payload, session_id) function in socket.py: retrieve connection from manager, call sio.emit(event, payload, skip_sid=None, to=session_id)
- [ ] T026 [US2] Mount Socket.IO app onto FastAPI in backend_service/app/main.py via app.add_asgi_middleware or equivalent ASGI integration
- [ ] T027 [US2] Add logging to emit_event for session dispatch (debug: sent to session_id, skip: unknown session)

**Checkpoint**: Socket.IO mounted, connections registered by session, emit_event routes to correct session

---

## Phase 5: User Story 3 - Ingest User Requests with File Uploads and Route to Planner (Priority: P3)

**Goal**: Accept user requests with file uploads via HTTP multipart form and publish to planner Kafka topic

**Independent Test**: Verify POST /api/chat/request accepts multipart form data, validates UserRequest fields, publishes to planner topic, returns request_id correlation

### Tests for User Story 3

- [ ] T028 [P] [US3] Add test_chat_api.py in backend_service/tests/ to verify POST /api/chat/request contract: accepts multipart form fields (user_prompt, user_level, sid), files parameter, validates UserRequest schema
- [ ] T029 [P] [US3] Add integration test for /api/chat/request: publish to Kafka, verify PlannerRequestEvent on planner topic with correct fields and request_id correlation

### Implementation for User Story 3

- [ ] T030 [P] [US3] Create backend_service/app/api/chat.py with POST /api/chat/request endpoint
- [ ] T031 [US3] Implement multipart form parsing in chat.py endpoint: extract user_prompt (str), user_level (list[str] as comma-separated or JSON), sid (str) from form; extract files parameter
- [ ] T032 [US3] Validate UserRequest fields in chat.py: non-empty user_prompt, non-empty user_level list, non-empty sid; return 400 on validation failure
- [ ] T033 [P] [US3] Create PlannerRequestEvent Pydantic model in project/schemas.py with fields (request_id: str, user_prompt: str, user_level: list[str], sid: str, file_paths: list[str], created_at: str | None)
- [ ] T034 [US3] Implement file storage and path tracking in chat.py: save uploaded files to UPLOAD_DIR, build file_paths list, pass to PlannerRequestEvent
- [ ] T035 [US3] Publish PlannerRequestEvent to planner-init-request Kafka topic with request_id as key (enables per-request routing)
- [ ] T036 [US3] Return 201 Created response from chat.py with request_id in response body for client correlation
- [ ] T037 [US3] Add logging to chat.py with request_id prefix for all events (received, validation, publish, response)

**Checkpoint**: User requests can be submitted with files and published to planner; frontend receives request_id for tracking

---

## Phase 6: User Story 4 - Consume Kafka Events and Forward to Frontend Sessions (Priority: P2)

**Goal**: Run background asyncio consumer task to route Kafka events to Socket.IO sessions based on session_id field

**Independent Test**: Verify consumer starts on app startup, polls clarify-user-level and stream-tokens topics, emits correct Socket.IO events to matching session_id

### Tests for User Story 4

- [ ] T038 [P] [US4] Add test_consumer.py in backend_service/tests/ to verify consumer task initialization and message routing: consume from clarify-user-level topic, validate ClarifyUserLevelEvent, route to socket emit
- [ ] T039 [P] [US4] Add test_consumer.py continuation: consume from stream-tokens topic, validate StreamTokensEventBody, route to socket emit with STREAM_TOKENS_SKT event name

### Implementation for User Story 4

- [ ] T040 [US4] Extend backend_service/app/socket.py with `run_consumer(app)` async function that creates KafkaConsumer for topics (clarify-user-level, stream-tokens)
- [ ] T041 [US4] Implement consumer polling loop in run_consumer: poll consumer, route by topic name, validate payload schema, extract sid field
- [ ] T042 [US4] Add to run_consumer: For clarify-user-level topic, validate as ClarifyUserLevelEvent, call emit_event(WebSocketEvents.CLARIFY_USER_LEVEL_SKT, payload, sid)
- [ ] T043 [US4] Add to run_consumer: For stream-tokens topic, validate as StreamTokensEventBody, call emit_event(WebSocketEvents.STREAM_TOKENS_SKT, payload, sid)
- [ ] T044 [US4] Add error handling in run_consumer: catch validation errors (log), catch unknown sid (log and skip), continue polling (BLE001 override)
- [ ] T045 [US4] Integrate consumer startup into FastAPI lifespan: call `asyncio.create_task(run_consumer(app))` in startup before yield
- [ ] T046 [US4] Add logging to consumer loop with message topic, session_id, and event name at debug level

**Checkpoint**: Consumer task started on app startup, routes Kafka events to matching Socket.IO sessions

---

## Phase 7: Feature 001 - RAG Test-Event API (Bonus: Re-integrate existing test-event route)

**Goal**: Add test-event API for rag topic to enable manual testing

**Independent Test**: Verify POST /api/v1/test-events/rag publishes RAGRequestEvent with default values, returns TestEventPublishResult with metadata

### Tests for User Story (Bonus)

- [ ] T047 [P] Add test_test_events_api.py in backend_service/tests/ to verify POST /api/v1/test-events/rag endpoint contract: publish with default_rag_test_event(), return TestEventPublishResult

### Implementation

- [ ] T048 [P] Create/update backend_service/app/api/test_events.py with POST /api/v1/test-events/rag endpoint (gated by TEST_ROUTES_ENABLED from config)
- [ ] T049 Implement endpoint: call default_rag_test_event(), publish to rag topic via shared producer, return TestEventPublishResult with metadata
- [ ] T050 Add logging to test_events.py with request correlation and publish outcome

**Checkpoint**: Test-event API available for manual Kafka testing in dev/test environments

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements, validation, and final quality checks

- [ ] T051 [P] Run ruff check and ruff format on project/ and backend_service/ to verify code quality gates pass
- [ ] T052 [P] Run python -m compileall project backend_service -q to verify bytecode compilation (no syntax errors)
- [ ] T053 [P] Run pytest backend_service/tests -q to verify all tests pass
- [ ] T054 Review and verify all TODO markers in socket.py and kafka.py are documented (defer cleanup, missing sid handling, auth)
- [ ] T055 Update .github/copilot-instructions.md to reference specs/003-integrate-kafka-backend/plan.md for speckit context
- [ ] T056 [P] Run quickstart.md validation: start Kafka, start backend, verify topic bootstrap log output, publish test event, verify response in Kafka UI
- [ ] T057 Add docstrings to all new functions/classes in backend_service/app/ and project/ (brief one-liners sufficient)
- [ ] T058 Verify project/schemas.py and project/events.py have no circular import issues (test via `python -c "from project.events import *; from project.schemas import *"`)

**Checkpoint**: All code quality gates pass, all tests pass, quickstart validated, ready for integration with feature 001/002



---

## Dependencies & Execution Strategy

### Phase Dependencies

| Phase | Depends On | Status |
|-------|-----------|--------|
| Phase 1 (Setup) | — | Ready immediately |
| Phase 2 (Foundational) | Phase 1 | BLOCKS all user stories |
| Phase 3 (US1 - Bootstrap) | Phase 2 | Ready after Phase 2 |
| Phase 4 (US2 - WebSocket) | Phase 2 | Ready after Phase 2 |
| Phase 5 (US3 - User Requests) | Phase 2 | Ready after Phase 2 |
| Phase 6 (US4 - Consumer) | Phase 2, Phase 4 | Requires WebSocket (Phase 4) for emit routing |
| Phase 7 (Bonus - Test-Event) | Phase 2 | Ready after Phase 2 |
| Phase 8 (Polish) | All phases | Final validation after all implementation |

### Parallel Opportunities

**After Phase 2 Completes**:
- Phase 3 (US1 - Bootstrap), Phase 4 (US2 - WebSocket), Phase 5 (US3 - User Requests), Phase 7 (Test-Event) can run in parallel
- Phase 6 (US4 - Consumer) requires Phase 4 to be mostly complete (socket.py structure)
- Phase 8 (Polish) runs after all feature phases

**Within Each Phase**:
- All tasks marked `[P]` can run in parallel (e.g., T013-T014, T019-T020, T028-T029, T038-T039 are all independent)
- Schema/config definitions (T004-T012) are all independent in Phase 2

### Suggested Execution Order

1. **Phase 1** (Setup): T001-T003 (1 person, ~15 min)
2. **Phase 2** (Foundational): T004-T012 in parallel, then T009 (serial after T004-T008) (~60 min)
3. **Parallel Group A** (Phase 3): T013-T018 (bootstrap feature) (~90 min)
4. **Parallel Group B** (Phase 4): T019-T027 (WebSocket feature) (~120 min)
5. **Parallel Group C** (Phase 5): T028-T037 (user request API) (~120 min)
6. **Phase 6** (Phase 4 must complete first): T038-T046 (consumer integration) (~90 min)
7. **Phase 7** (Bonus): T047-T050 (test-event API) (~60 min)
8. **Phase 8** (Polish): T051-T058 (quality gates + validation) (~45 min)

**Total Estimated Effort**: ~600-660 minutes (~10-11 hours) for single developer; highly parallelizable for team

---

## Independent Test Criteria (Per User Story)

### User Story 1 - Bootstrap (P1)

**Test Scope**: 
- [ ] Topic bootstrap on startup succeeds and logs results
- [ ] Second startup is idempotent (no errors, no duplicate creates)
- [ ] Topics appear in Kafka UI after bootstrap

**Validation**:
```bash
python -m backend_service.app.main
# Expected: "INFO Topic bootstrap complete: X created, Y already existed, Z errors"
curl http://localhost:8080  # Kafka UI - confirm topics present
```

### User Story 2 - WebSocket (P2)

**Test Scope**:
- [ ] Frontend Socket.IO client can connect and receive `sid`
- [ ] Multiple concurrent sessions are routed independently
- [ ] emit_event successfully sends payload to matching session only
- [ ] Unknown session_id is skipped without error

**Validation**:
```bash
pytest backend_service/tests/test_socket.py::test_emit_event_routes_to_correct_session -v
pytest backend_service/tests/test_connection_manager.py -v
```

### User Story 3 - User Requests (P3)

**Test Scope**:
- [ ] POST /api/chat/request accepts multipart form data with user_prompt, user_level, sid
- [ ] Files are stored in UPLOAD_DIR with trackable paths
- [ ] PlannerRequestEvent published to Kafka with correct fields and request_id key
- [ ] Response includes request_id for client correlation

**Validation**:
```bash
curl -s -X POST http://localhost:8001/api/chat/request \
  -F "user_prompt=Test" -F "user_level=beginner" -F "sid=test-sid-123" \
  -F "files=@sample.pdf" | jq .request_id
# Should print request_id UUID
```

### User Story 4 - Consumer (P2)

**Test Scope**:
- [ ] Consumer task starts on app startup
- [ ] clarify-user-level messages are validated and routed via Socket.IO
- [ ] stream-tokens messages are validated and routed via Socket.IO
- [ ] Consumer recovers from validation errors and continues polling
- [ ] Unknown session_id messages are logged and skipped

**Validation**:
```bash
pytest backend_service/tests/test_consumer.py -v
# Observe debug logs for each message route decision
```

---

## MVP Scope (Recommended for Initial Release)

**Deliver**:
1. ✅ Phase 1 (Setup)
2. ✅ Phase 2 (Foundational - all schemas/configs)
3. ✅ Phase 3 (US1 - Bootstrap) - enables Kafka infrastructure
4. ✅ Phase 4 (US2 - WebSocket) - enables frontend connectivity
5. ✅ Phase 6 (US4 - Consumer) - enables backend-to-frontend routing
6. ⏭️ Phase 5 (US3 - User Requests) - defer to Phase 2 release if timeline tight
7. ⏭️ Phase 7 (Bonus - Test-Event API) - defer to Phase 2 if timeline tight
8. ✅ Phase 8 (Polish - quality gates)

**MVP Duration**: ~480-540 minutes (~8-9 hours) with Phases 1-4, 6, 8

**Phase 2 Backlog**: Phases 5, 7

---

## Notes on Task Implementation Strategy

**Simplicity First** (Per User Guidance):
- Keep validation basic (non-empty checks, type validation via Pydantic)
- Defer edge cases (disconnect cleanup, auth, back-pressure) via explicit TODO markers
- Use Pydantic for all schema validation (no custom validators)
- Minimal error handling: log exceptions, continue loop (Kafka consumer)

**Schema Organization**:
- All schemas centralized in project/schemas.py (single source of truth)
- project/events.py re-exports schemas and defines event-name constants
- No local schema duplication across backend_service/ modules

**Testing Approach**:
- Test contracts first (input/output shapes)
- Test routing logic (correct message delivery)
- Test recovery from errors (consumer continues on bad message)
- Integration tests verify end-to-end flows (publish → consume → emit)

**Logging Pattern**:
- All Kafka operations logged with request_id or message_id prefix
- Socket.IO routing logged at debug level (session_id, event name, outcome)
- Errors logged but not raised (consumer resilience)
