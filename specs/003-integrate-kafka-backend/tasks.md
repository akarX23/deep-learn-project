# Tasks: Backend Kafka Startup Bootstrap + RAG Test-Event API + WebSocket Channel

**Input**: Design documents from /specs/003-integrate-kafka-backend/
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include test tasks by default.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: [ID] [P?] [Story] Description

- [P]: Can run in parallel (different files, no dependencies)
- [Story]: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies and define shared schema contracts used across backend and frontend.

- [x] T001 [P] Add python-socketio dependency in requirements.txt
- [x] T002 [P] Define WebSocketEvents enum and StreamTokensEventBody schema in project/events.py
- [x] T003 [P] Add UserRequest schema in project/schemas.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core runtime wiring that must exist before user-story implementation.

**Checkpoint**: Backend runtime supports Kafka admin bootstrap, test-event route gating, shared producer reuse, and Socket.IO mount points.

- [x] T004 [P] Add test-event route policy parsing in backend_service/app/config.py
- [x] T005 [P] Ensure shared producer lifecycle and bootstrap result usage in backend_service/app/kafka_admin.py
- [x] T006 Wire startup sequence and optional route registration in backend_service/app/main.py
- [x] T007 [P] Mount Socket.IO ASGI app and attach connection manager state in backend_service/app/main.py
- [x] T008 [P] Add baseline reusable fixtures for admin and app state in backend_service/tests/conftest.py

**Checkpoint**: Foundation ready - user stories can be implemented and tested independently.

---

## Phase 3: User Story 1 - Bootstrap Kafka Topics from Project Registry on Startup (Priority: P1) 🎯 MVP

**Goal**: Backend auto-creates all required topics at startup from project/topics with idempotent behavior.

**Independent Test**: Start backend with reachable Kafka and verify all topics from project/topics exist after startup; repeat startup with pre-existing topics and verify no failure.

### Tests for User Story 1

- [x] T009 [P] [US1] Add startup bootstrap success and idempotency tests in backend_service/tests/test_startup.py
- [x] T010 [P] [US1] Add startup retry/failure path tests for unreachable Kafka in backend_service/tests/test_startup.py
- [x] T011 [P] [US1] Add topic bootstrap API contract assertions in backend_service/tests/test_topics_api.py

### Implementation for User Story 1

- [x] T012 [US1] Implement topic aggregation bootstrap workflow in backend_service/app/kafka_admin.py
- [x] T013 [US1] Read project topic registry and invoke bootstrap in backend_service/app/main.py
- [x] T014 [US1] Add startup bootstrap logging and TODO-marked non-fatal error handling in backend_service/app/main.py

**Checkpoint**: User Story 1 independently works and is testable.

---

## Phase 4: User Story 2 - Real-Time WebSocket Channel for Frontend Session Routing (Priority: P2)

**Goal**: Frontend connects via Socket.IO, events are routed per sid, and shared event/request schemas are available with minimal boilerplate.

**Independent Test**: Connect Socket.IO client, capture sid, emit stream-tokens with StreamTokensEventBody payload to that sid only, and verify UserRequest schema can be instantiated and used by backend-facing code.

### Tests for User Story 2

- [x] T015 [P] [US2] Add stream-tokens event schema tests for required fields in backend_service/tests/test_socket.py
- [x] T016 [P] [US2] Add connection manager sid mapping tests in backend_service/tests/test_connection_manager.py
- [x] T017 [P] [US2] Add per-session emit routing tests for emit_event in backend_service/tests/test_socket.py
- [x] T018 [P] [US2] Add UserRequest schema tests in backend_service/tests/test_utils.py

### Implementation for User Story 2

- [x] T019 [P] [US2] Implement minimal get/set ConnectionManager in backend_service/app/connection_manager.py
- [x] T020 [P] [US2] Implement lightweight Socket.IO listeners and emit_event in backend_service/app/socket.py
- [x] T021 [US2] Use StreamTokensEventBody contract in backend_service/app/socket.py for stream-tokens emission path
- [x] T022 [US2] Add TODO-marked stubs for disconnect cleanup and missing session handling in backend_service/app/socket.py
- [x] T023 [US2] Implement rag test-event publish route with normalized response in backend_service/app/api/test_events.py
- [x] T024 [US2] Implement default_rag_test_event factory in backend_service/app/utils.py

**Checkpoint**: User Story 2 independently works and is testable.

---

## Phase 5: Polish and Cross-Cutting Concerns

**Purpose**: Validate quality gates and update docs for release readiness.

- [x] T025 [P] Run full backend test suite and verify schema coverage in backend_service/tests/test_startup.py and backend_service/tests/test_socket.py
- [x] T026 [P] Run ruff check and ruff format checks for project/schemas.py and backend_service/app/main.py
- [x] T027 [P] Run compileall validation for project/schemas.py and backend_service/app/socket.py
- [x] T028 [P] Update quickstart usage for stream-tokens schema and UserRequest in specs/003-integrate-kafka-backend/quickstart.md
- [x] T029 [P] Update websocket contract details for schema mapping in specs/003-integrate-kafka-backend/contracts/backend-websocket-contract.md

---

## Dependencies and Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies.
- Foundational (Phase 2): Depends on Setup and blocks all user stories.
- User Stories (Phase 3+): Depend on Foundational completion.
- Polish (Phase 5): Depends on desired user stories complete.

### User Story Dependencies

- User Story 1 (P1): Starts after Foundational; no dependency on User Story 2.
- User Story 2 (P2): Starts after Foundational; no dependency on User Story 1.

### Within Each User Story

- Tests before implementation.
- Shared contracts before runtime integration.
- Runtime integration before polish.

### Parallel Opportunities

- Phase 1 tasks T001 to T003 can run in parallel.
- Phase 2 tasks T004, T005, T007, and T008 can run in parallel after initial wiring plan is set.
- User Story 1 test tasks T009 to T011 can run in parallel.
- User Story 2 test tasks T015 to T018 can run in parallel.
- User Story 2 implementation tasks T019, T020, and T024 can run in parallel.
- Polish tasks T025 to T029 can run in parallel where file overlap is avoided.

---

## Parallel Example: User Story 1

```bash
Task: Add startup bootstrap success and idempotency tests in backend_service/tests/test_startup.py
Task: Add startup retry/failure path tests for unreachable Kafka in backend_service/tests/test_startup.py
Task: Implement topic aggregation bootstrap workflow in backend_service/app/kafka_admin.py
```

## Parallel Example: User Story 2

```bash
Task: Add stream-tokens event schema tests for required fields in backend_service/tests/test_socket.py
Task: Add UserRequest schema tests in backend_service/tests/test_utils.py
Task: Implement minimal get/set ConnectionManager in backend_service/app/connection_manager.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete User Story 1.
3. Validate User Story 1 independently.

### Incremental Delivery

1. Deliver User Story 1 and validate.
2. Deliver User Story 2 and validate.
3. Run polish and release checks.

### Parallel Team Strategy

1. Team finishes Setup and Foundational together.
2. One developer handles User Story 1 while another handles User Story 2.
3. Converge for polish and verification.

---

## Notes

- Keep tasks small and file-specific.
- Preserve TODO markers where edge cases are explicitly deferred.
- Keep schema handling minimal with no extra custom validation logic in this iteration.
