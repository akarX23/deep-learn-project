# Tasks: Kafka Backend Integration Service

**Input**: Design documents from /specs/003-integrate-kafka-backend/
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the specification requires measurable startup behavior, API contract correctness, and global exception/error-envelope guarantees.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the backend package layout and shared project configuration artifacts.

- [ ] T001 Create backend package markers in backend_service/__init__.py, backend_service/app/__init__.py, and backend_service/app/api/__init__.py
- [ ] T002 Add backend runtime dependency entries for FastAPI/Uvicorn/Kafka in requirements.txt
- [ ] T003 [P] Add backend Kafka and compose variable examples in .env.example and .env.local.example
- [ ] T004 [P] Add container ignore defaults for local compose/dev workflows in .dockerignore

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared runtime primitives required by all user stories.

**CRITICAL**: User story implementation starts only after this phase is complete.

- [ ] T005 Implement typed Kafka settings with .env.local loading and process-env precedence in backend_service/app/config.py
- [ ] T006 [P] Implement Kafka admin adapter interfaces (connect, close, create_topic) in backend_service/app/kafka_admin.py
- [ ] T007 [P] Define shared TopicCreate and ApiErrorResponse schemas in backend_service/app/api/topics.py
- [ ] T008 Wire FastAPI app factory and dependency injection shell in backend_service/app/main.py
- [ ] T009 Implement global FastAPI exception handlers for 422, HTTPException, and unhandled exceptions in backend_service/app/main.py
- [ ] T010 Implement FastAPI lifecycle startup/shutdown hooks for Kafka connect/cleanup in backend_service/app/main.py
- [ ] T011 [P] Add foundational tests for env precedence and settings validation in backend_service/tests/test_startup.py

**Checkpoint**: Foundational runtime and cross-cutting behavior are ready.

---

## Phase 3: User Story 1 - Initialize Backend Kafka Connectivity (Priority: P1) 🎯 MVP

**Goal**: Service starts with Kafka admin initialization and retry behavior controlled by environment settings.

**Independent Test**: Launch app with mocked Kafka admin outcomes and verify startup success, retry flow, retry exhaustion failure, and shutdown cleanup independently.

### Tests for User Story 1

- [ ] T012 [P] [US1] Add startup success test for valid Kafka configuration in backend_service/tests/test_startup.py
- [ ] T013 [P] [US1] Add retry-then-success startup test using configured retry count/timeout in backend_service/tests/test_startup.py
- [ ] T014 [US1] Add retry-exhausted startup failure test with explicit diagnostics in backend_service/tests/test_startup.py
- [ ] T015 [US1] Add shutdown lifecycle cleanup invocation test in backend_service/tests/test_startup.py

### Implementation for User Story 1

- [ ] T016 [US1] Implement startup retry loop using startup_retry_count and startup_retry_timeout_seconds in backend_service/app/main.py
- [ ] T017 [P] [US1] Implement startup diagnostic logging for attempts and terminal failure in backend_service/app/main.py
- [ ] T018 [US1] Implement Kafka admin connectivity probe behavior in backend_service/app/kafka_admin.py
- [ ] T019 [US1] Enforce fail-fast validation for required Kafka settings in backend_service/app/config.py

**Checkpoint**: US1 is independently functional and testable.

---

## Phase 4: User Story 2 - Create Kafka Topics via API (Priority: P2)

**Goal**: Provide the single topic-creation endpoint with deterministic success/exists/error outcomes and uniform error envelopes.

**Independent Test**: Call the topic endpoint with valid, duplicate, invalid, and failing runtime scenarios using mocked admin behavior.

### Tests for User Story 2

- [ ] T020 [P] [US2] Add contract test for POST /api/v1/topics created response in backend_service/tests/test_topics_api.py
- [ ] T021 [P] [US2] Add duplicate-topic idempotency test returning already_exists in backend_service/tests/test_topics_api.py
- [ ] T022 [P] [US2] Add invalid payload test asserting structured validation error envelope in backend_service/tests/test_topics_api.py
- [ ] T023 [US2] Add HTTPException and unhandled exception envelope tests in backend_service/tests/test_topics_api.py

### Implementation for User Story 2

- [ ] T024 [US2] Implement POST /api/v1/topics route and schema binding in backend_service/app/api/topics.py
- [ ] T025 [US2] Implement topic creation call path and already_exists handling in backend_service/app/kafka_admin.py
- [ ] T026 [US2] Map route/service failures to stable HTTP exception messages in backend_service/app/api/topics.py
- [ ] T027 [US2] Restrict route registration to topic-creation scope in backend_service/app/main.py

**Checkpoint**: US2 is independently functional and testable.

---

## Phase 5: User Story 3 - Provide Local Kafka + Kafka UI Infrastructure Bootstrap (Priority: P3)

**Goal**: Root docker-compose starts Kafka and Kafka UI with documented connectivity and quick local verification.

**Independent Test**: Bring up compose services, verify Kafka UI is reachable, and validate config expectations through tests/docs.

### Tests for User Story 3

- [ ] T028 [P] [US3] Add compose configuration test for service names and kafka-ui image in backend_service/tests/test_startup.py
- [ ] T029 [US3] Add Kafka UI reachability expectation smoke assertion in backend_service/tests/test_startup.py

### Implementation for User Story 3

- [ ] T030 [US3] Create root compose services for kafka and kafka-ui in docker-compose.yaml
- [ ] T031 [US3] Configure kafka-ui connection environment to kafka service in docker-compose.yaml
- [ ] T032 [P] [US3] Document local bootstrap and endpoint usage workflow in specs/003-integrate-kafka-backend/quickstart.md
- [ ] T033 [US3] Align compose/backend environment examples in .env.example and .env.local.example

**Checkpoint**: US3 is independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, documentation alignment, and verification evidence.

- [ ] T034 [P] Update API contract lifecycle and global exception-envelope clauses in specs/003-integrate-kafka-backend/contracts/backend-topic-api-contract.md
- [ ] T035 [P] Update rationale/tradeoffs for lifecycle and exception strategy in specs/003-integrate-kafka-backend/research.md
- [ ] T036 Run backend test suite and record results in specs/003-integrate-kafka-backend/quickstart.md
- [ ] T037 Validate startup retry and topic-create latency budgets and capture baseline in specs/003-integrate-kafka-backend/quickstart.md
- [ ] T038 Enforce import grouping and cleanup in backend_service/app/main.py, backend_service/app/config.py, backend_service/app/kafka_admin.py, and backend_service/app/api/topics.py

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1: No dependencies; starts immediately.
- Phase 2: Depends on Phase 1 and blocks all user stories.
- Phase 3 (US1): Depends on Phase 2 completion.
- Phase 4 (US2): Depends on Phase 2 completion; may run after US1 interfaces stabilize.
- Phase 5 (US3): Depends on Phase 2 completion; can run in parallel with US2.
- Phase 6: Depends on completion of targeted user stories.

### User Story Dependencies

- US1 (P1): Independent after foundational phase.
- US2 (P2): Independent after foundational phase; no functional dependency on US3.
- US3 (P3): Independent after foundational phase; no functional dependency on US2 internals.

### Within Each User Story

- Write/expand story tests first and verify expected failure/safety behavior.
- Implement service and API logic after schema/contract scaffolding is in place.
- Validate each story independently before proceeding.

---

## Parallel Opportunities

- Setup: T003 and T004 can run in parallel.
- Foundational: T006, T007, and T011 can run in parallel after T005 starts.
- US1: T012 and T013 can run in parallel; T017 can run in parallel with T016.
- US2: T020, T021, and T022 can run in parallel.
- US3: T028 and T032 can run in parallel after compose skeleton is defined.
- Polish: T034 and T035 can run in parallel.

## Parallel Example: User Story 2

- Run T020, T021, and T022 together while endpoint behavior is being implemented.
- Run T025 and T026 in parallel after T024 defines route contracts.

## Parallel Example: User Story 3

- Run T030 and T032 together once compose topology is fixed.
- Run T028 while T031 finalizes kafka-ui connectivity wiring.

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1).
3. Validate startup lifecycle behavior and retry semantics independently.
4. Demo startup readiness as MVP.

### Incremental Delivery

1. Foundation: Phase 1 + Phase 2.
2. Add US1 and validate.
3. Add US2 and validate.
4. Add US3 and validate.
5. Execute Phase 6 polish and final evidence capture.

### Parallel Team Strategy

1. Engineer A: config/startup lifecycle and US1.
2. Engineer B: topic API and global error-envelope behavior (US2).
3. Engineer C: docker-compose/bootstrap docs and US3.
