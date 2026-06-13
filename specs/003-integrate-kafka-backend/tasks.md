# Tasks: Backend Kafka Startup Bootstrap + RAG Test-Event API + WebSocket Channel + User-Request API

**Input**: Design documents from `/specs/003-integrate-kafka-backend/`
**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Include test tasks by default (constitution requires testing evidence).

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure shared dependencies and contracts are present for all stories.

- [x] T001 [P] Add/verify Socket.IO and multipart dependencies in `requirements.txt`
- [x] T002 [P] Add/verify shared WebSocket contracts in `project/events.py`
- [x] T003 [P] Add/verify `UserRequest` and `PlannerRequestEvent` schemas in `project/schemas.py`
- [x] T004 [P] Add/verify Kafka topic registry entries in `project/topics.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core wiring that must be complete before implementing user stories.

**Critical**: No user story work starts before this phase is complete.

- [x] T005 [P] Add/verify test-event route policy config in `backend_service/app/config.py`
- [x] T006 [P] Add/verify startup bootstrap and shared producer support in `backend_service/app/kafka_admin.py`
- [x] T007 Add/verify app startup route wiring and lifecycle setup in `backend_service/app/main.py`
- [x] T008 [P] Add/verify reusable defaults factory in `backend_service/app/utils.py`
- [x] T009 [P] Add/verify baseline backend fixtures in `backend_service/tests/conftest.py`

**Checkpoint**: Foundational runtime is ready; user stories can be developed independently.

---

## Phase 3: User Story 1 - Bootstrap Kafka Topics from Project Registry on Startup (Priority: P1) 🎯 MVP

**Goal**: Create all topics from `project/topics` during startup with idempotent behavior.

**Independent Test**: Start backend against Kafka and verify all registry topics exist after startup; repeat with existing topics and verify no failure.

### Tests for User Story 1

- [x] T010 [P] [US1] Add startup bootstrap success/idempotency tests in `backend_service/tests/test_startup.py`
- [x] T011 [P] [US1] Add startup Kafka retry/failure tests in `backend_service/tests/test_startup.py`
- [x] T012 [P] [US1] Add topic bootstrap API contract tests in `backend_service/tests/test_topics_api.py`

### Implementation for User Story 1

- [x] T013 [US1] Implement/verify topic bootstrap orchestration in `backend_service/app/main.py`
- [x] T014 [US1] Implement/verify per-topic create/idempotent handling in `backend_service/app/kafka_admin.py`
- [x] T015 [US1] Add/verify startup bootstrap summary logging and TODO markers in `backend_service/app/main.py`

**Checkpoint**: User Story 1 is complete and independently testable.

---

## Phase 4: User Story 2 - Real-Time WebSocket Channel for Frontend Session Routing (Priority: P2)

**Goal**: Provide Socket.IO channel and per-session event routing via `sid`.

**Independent Test**: Connect Socket.IO client, capture `sid`, emit event to that `sid`, verify only that session receives it.

### Tests for User Story 2

- [x] T016 [P] [US2] Add connection manager get/set mapping tests in `backend_service/tests/test_connection_manager.py`
- [x] T017 [P] [US2] Add Socket.IO emit routing tests in `backend_service/tests/test_socket.py`
- [x] T018 [P] [US2] Add stream-tokens schema contract tests in `backend_service/tests/test_socket.py`
- [x] T019 [P] [US2] Add `UserRequest` schema regression tests in `backend_service/tests/test_utils.py`

### Implementation for User Story 2

- [x] T020 [P] [US2] Implement/verify minimal `ConnectionManager` in `backend_service/app/connection_manager.py`
- [x] T021 [P] [US2] Implement/verify Socket.IO listeners and `emit_event` in `backend_service/app/socket.py`
- [x] T022 [US2] Implement/verify Socket.IO mounting and session wiring in `backend_service/app/main.py`
- [x] T023 [US2] Add TODO markers for deferred disconnect/missing-session handling in `backend_service/app/socket.py`
- [x] T024 [US2] Implement/verify rag test-event publish endpoint in `backend_service/app/api/test_events.py`

**Checkpoint**: User Story 2 is complete and independently testable.

---

## Phase 5: User Story 3 - Ingest User Requests with File Uploads and Route to Planner (Priority: P3)

**Goal**: Accept parsed `UserRequest` form fields and files, save files, publish `PlannerRequestEvent` to `init-planner`.

**Independent Test**: Call `POST /api/chat/request` with form fields (`user_prompt`, `user_level`, `sid`) and 1-3 files, verify file persistence, Kafka publish payload, and success/error responses.

### Tests for User Story 3

- [x] T025 [P] [US3] Add parsed form-field request validation tests for `/api/chat/request` in `backend_service/tests/test_chat_request_api.py`
- [x] T026 [P] [US3] Add file upload/save path tests (absolute path assertions) in `backend_service/tests/test_chat_request_api.py`
- [x] T027 [P] [US3] Add publish success/failure tests for `init-planner` in `backend_service/tests/test_chat_request_api.py`
- [x] T028 [P] [US3] Add max-files warning/non-rejection tests in `backend_service/tests/test_chat_request_api.py`
- [x] T029 [P] [US3] Add 400/500 error envelope tests (`{error: ...}`) in `backend_service/tests/test_chat_request_api.py`

### Implementation for User Story 3

- [x] T030 [US3] Add/verify `UPLOAD_DIR` configuration with default `./uploads` in `backend_service/app/config.py`
- [x] T031 [US3] Add/verify uploads ignore rules in `.gitignore`
- [x] T032 [US3] Implement/verify `/api/chat/request` endpoint with parsed form-model fields in `backend_service/app/api/chat_request.py`
- [x] T033 [US3] Implement/verify repeated multipart `files` upload parsing in `backend_service/app/api/chat_request.py`
- [x] T034 [US3] Implement/verify file persistence and absolute path collection in `backend_service/app/api/chat_request.py`
- [x] T035 [US3] Implement/verify max-3 file warning behavior (no reject) in `backend_service/app/api/chat_request.py`
- [x] T036 [US3] Implement/verify `PlannerRequestEvent` publish to `init-planner` in `backend_service/app/api/chat_request.py`
- [x] T037 [US3] Implement/verify success response message and error envelopes in `backend_service/app/api/chat_request.py`
- [x] T038 [P] [US3] Add TODO markers for deferred file validation/cleanup/retry handling in `backend_service/app/api/chat_request.py`

**Checkpoint**: User Story 3 is complete and independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate quality gates and finalize docs/contracts.

- [x] T039 [P] Run backend test suite and confirm story coverage in `backend_service/tests/`
- [x] T040 [P] Run lint/format checks (`ruff check`, `ruff format --check`) for `project/` and `backend_service/`
- [x] T041 [P] Run bytecode compile validation in `project/` and `backend_service/`
- [x] T042 [P] Verify quickstart request examples for parsed form-fields in `specs/003-integrate-kafka-backend/quickstart.md`
- [x] T043 [P] Verify user-request API contract examples in `specs/003-integrate-kafka-backend/contracts/backend-user-request-api-contract.md`
- [x] T044 [P] Verify cross-artifact consistency across `spec.md`, `plan.md`, `research.md`, and `data-model.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3+ (User Stories)**: Depend on Phase 2 completion.
- **Phase 6 (Polish)**: Depends on completion of all targeted stories.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; no dependency on US2/US3.
- **US2 (P2)**: Starts after Phase 2; no hard dependency on US1/US3.
- **US3 (P3)**: Starts after Phase 2; no hard dependency on US1/US2.

### Within Each User Story

- Tests first, then implementation.
- Schemas/contracts before runtime wiring.
- Endpoint behavior before polish/documentation checks.

---

## Parallel Opportunities

- Setup tasks T001-T004 can run in parallel.
- Foundational tasks T005, T006, T008, T009 can run in parallel.
- US1 tests T010-T012 can run in parallel.
- US2 tests T016-T019 can run in parallel.
- US2 implementation tasks T020 and T021 can run in parallel.
- US3 tests T025-T029 can run in parallel.
- US3 implementation tasks T032 and T033 can run in parallel; T034-T037 follow.
- Polish tasks T039-T044 can run in parallel where file overlap is avoided.

---

## Parallel Example: User Story 3

```bash
# Write/execute US3 tests together
Task: "Add parsed form-field request validation tests for /api/chat/request in backend_service/tests/test_chat_request_api.py"
Task: "Add file upload/save path tests (absolute path assertions) in backend_service/tests/test_chat_request_api.py"
Task: "Add publish success/failure tests for init-planner in backend_service/tests/test_chat_request_api.py"

# Implement non-conflicting US3 tasks together
Task: "Add/verify UPLOAD_DIR configuration with default ./uploads in backend_service/app/config.py"
Task: "Add/verify uploads ignore rules in .gitignore"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1 and Phase 2.
2. Deliver US1 (startup bootstrap).
3. Validate startup behavior independently before adding other stories.

### Incremental Delivery

1. Deliver US1 (Kafka bootstrap).
2. Deliver US2 (WebSocket routing).
3. Deliver US3 (chat request ingestion with parsed form fields + uploads).
4. Run Phase 6 quality/documentation gates.

### Parallel Team Strategy

1. Team completes Setup + Foundational together.
2. Then parallelize by story:
   - Dev A: US1
   - Dev B: US2
   - Dev C: US3
3. Converge for polish and release checks.

---

## Notes

- `[P]` tasks target different files and no unmet dependencies.
- User story labels map directly to spec priorities (`US1`, `US2`, `US3`).
- Keep implementation minimal and preserve TODO markers where spec defers edge-case handling.
- Parsed form-model requirement for `/api/chat/request` must remain consistent across code, tests, and contracts.
