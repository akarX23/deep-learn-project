# Tasks: Kafka Backend Integration Service

**Input**: Design documents from `/specs/003-integrate-kafka-backend/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the specification requires measurable startup behavior, API contract correctness, lifespan lifecycle compliance, structured error handling, and compose bootstrap validation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure repository and backend scaffolding are ready for implementation.

- [X] T001 Create backend package markers in `backend_service/__init__.py`, `backend_service/app/__init__.py`, and `backend_service/app/api/__init__.py`
- [X] T002 Add backend runtime dependencies for FastAPI, Uvicorn, kafka-python, and python-dotenv in `requirements.txt`
- [X] T003 [P] Add backend and compose environment variable examples in `.env.example` and `.env.local.example`
- [X] T004 [P] Add Docker ignore defaults for backend development workflows in `.dockerignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared runtime primitives that all stories depend on.

**CRITICAL**: No user story implementation starts until this phase is complete.

- [X] T005 Implement typed Kafka runtime settings with `.env.local` loading and process-env precedence in `backend_service/app/config.py`
- [X] T006 [P] Implement Kafka admin adapter interfaces (`connect`, `close`, `create_topic`) in `backend_service/app/kafka_admin.py`
- [X] T007 [P] Define shared API schemas (`TopicCreateRequest`, `TopicCreateResponse`, `ApiErrorResponse`) in `backend_service/app/api/topics.py`
- [X] T008 Wire FastAPI app factory, dependency injection shell, and router registration in `backend_service/app/main.py`
- [X] T009 Implement global exception handlers for `RequestValidationError`, `HTTPException`, and unhandled `Exception` in `backend_service/app/main.py`
- [X] T010 Implement FastAPI lifespan startup/shutdown orchestration (no `on_event`) in `backend_service/app/main.py`
- [X] T011 [P] Add foundational tests for env precedence and settings validation in `backend_service/tests/test_startup.py`

**Checkpoint**: Shared runtime, lifecycle model, and error envelope contract are established.

---

## Phase 3: User Story 1 - Initialize Backend Kafka Connectivity (Priority: P1) 🎯 MVP

**Goal**: Backend service initializes Kafka admin connectivity during startup with configured retry behavior.

**Independent Test**: Launch app with mocked Kafka admin outcomes and verify startup success, retry behavior, retry exhaustion failure, and shutdown cleanup.

### Tests for User Story 1

- [X] T012 [P] [US1] Add startup success test for valid Kafka config in `backend_service/tests/test_startup.py`
- [X] T013 [P] [US1] Add retry-then-success startup test using configured retry settings in `backend_service/tests/test_startup.py`
- [X] T014 [US1] Add retry-exhausted startup failure test with explicit diagnostics in `backend_service/tests/test_startup.py`
- [X] T015 [US1] Add lifespan shutdown cleanup invocation test in `backend_service/tests/test_startup.py`

### Implementation for User Story 1

- [X] T016 [US1] Implement startup retry loop using `startup_retry_count` and `startup_retry_timeout_seconds` in `backend_service/app/main.py`
- [X] T017 [P] [US1] Implement startup diagnostics for attempt count and terminal failure in `backend_service/app/main.py`
- [X] T018 [US1] Implement Kafka admin connectivity probe behavior in `backend_service/app/kafka_admin.py`
- [X] T019 [US1] Enforce fail-fast validation for required Kafka settings in `backend_service/app/config.py`

**Checkpoint**: US1 is independently functional and testable.

---

## Phase 4: User Story 2 - Create Kafka Topics via API (Priority: P2)

**Goal**: Provide a single topic-creation endpoint with deterministic outcomes and consistent error envelope behavior.

**Independent Test**: Call topic endpoint for created, already_exists, invalid payload, HTTP exception, and unhandled exception scenarios.

### Tests for User Story 2

- [X] T020 [P] [US2] Add contract test for `POST /api/v1/topics` created response in `backend_service/tests/test_topics_api.py`
- [X] T021 [P] [US2] Add duplicate-topic idempotency test returning `already_exists` in `backend_service/tests/test_topics_api.py`
- [X] T022 [P] [US2] Add invalid payload validation test asserting structured error envelope in `backend_service/tests/test_topics_api.py`
- [X] T023 [US2] Add HTTPException and unhandled exception envelope tests in `backend_service/tests/test_topics_api.py`

### Implementation for User Story 2

- [X] T024 [US2] Implement `POST /api/v1/topics` endpoint request/response binding in `backend_service/app/api/topics.py`
- [X] T025 [US2] Implement topic creation service path and duplicate handling in `backend_service/app/kafka_admin.py`
- [X] T026 [US2] Map route/service runtime failures to stable HTTP exception responses in `backend_service/app/api/topics.py`
- [X] T027 [US2] Restrict backend route registration to topic-creation scope in `backend_service/app/main.py`

**Checkpoint**: US2 is independently functional and testable.

---

## Phase 5: User Story 3 - Provide Local Kafka + Kafka UI Infrastructure Bootstrap (Priority: P3)

**Goal**: Root docker-compose boots Kafka and Kafka UI with Apache Kafka `4.2.1`, KRaft-compatible env wiring, and documented usage.

**Independent Test**: Start compose services, verify expected image/config values, and confirm Kafka UI reachability.

### Tests for User Story 3

- [X] T028 [P] [US3] Add compose configuration test for service names and Kafka image `apache/kafka:4.2.1` in `backend_service/tests/test_startup.py`
- [X] T029 [P] [US3] Add compose configuration test for Kafka UI image and bootstrap server wiring in `backend_service/tests/test_startup.py`
- [X] T030 [US3] Add KRaft env-key presence test for compose Kafka service in `backend_service/tests/test_startup.py`
- [X] T031 [US3] Add Kafka UI reachability expectation smoke assertion in `backend_service/tests/test_startup.py`

### Implementation for User Story 3

- [X] T032 [US3] Create root compose services for `kafka` and `kafka-ui` with Kafka image `apache/kafka:4.2.1` in `docker-compose.yaml`
- [X] T033 [US3] Configure Kafka KRaft-oriented environment values for Apache Kafka container in `docker-compose.yaml`
- [X] T034 [US3] Configure Kafka UI bootstrap connection to Kafka service in `docker-compose.yaml`
- [X] T035 [P] [US3] Document local bootstrap and endpoint usage workflow in `specs/003-integrate-kafka-backend/quickstart.md`
- [X] T036 [US3] Align backend and compose env examples in `.env.example` and `.env.local.example`

**Checkpoint**: US3 is independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality gates, consistency, and verification evidence.

- [X] T037 [P] Update contract clauses for lifespan-only lifecycle, global error envelope, and Apache Kafka image pin in `specs/003-integrate-kafka-backend/contracts/backend-topic-api-contract.md`
- [X] T038 [P] Update rationale/tradeoffs for Apache Kafka image pin and KRaft strategy in `specs/003-integrate-kafka-backend/research.md`
- [X] T039 [P] Update compose entity and validation notes for fixed Kafka image in `specs/003-integrate-kafka-backend/data-model.md`
- [X] T040 Run backend test suite and record results in `specs/003-integrate-kafka-backend/quickstart.md`
- [X] T041 Validate startup retry and topic-create latency budgets and capture baseline in `specs/003-integrate-kafka-backend/quickstart.md`
- [X] T042 Run lint/format/static analysis checks and record evidence in `specs/003-integrate-kafka-backend/quickstart.md`
- [ ] T043 Validate local compose startup-time target (under 2 minutes) and record measurement in `specs/003-integrate-kafka-backend/quickstart.md`
- [ ] T044 Enforce import grouping and code cleanup in `backend_service/app/main.py`, `backend_service/app/config.py`, `backend_service/app/kafka_admin.py`, and `backend_service/app/api/topics.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1: No dependencies; starts immediately.
- Phase 2: Depends on Phase 1 and blocks all user story phases.
- Phase 3 (US1): Depends on Phase 2 completion.
- Phase 4 (US2): Depends on Phase 2 completion and can proceed after US1 interface baselines are stable.
- Phase 5 (US3): Depends on Phase 2 completion and can proceed in parallel with US2.
- Phase 6: Depends on completion of targeted user stories.

### User Story Dependencies

- US1 (P1): Independent after foundational phase.
- US2 (P2): Independent after foundational phase and does not require US3 internals.
- US3 (P3): Independent after foundational phase and does not require US2 internals.

### Within Each User Story

- Add story tests first and confirm expected safety/failure conditions.
- Implement schema/models and service logic before endpoint integration.
- Validate each story independently before moving forward.

---

## Parallel Opportunities

- Setup: T003 and T004 can run in parallel.
- Foundational: T006, T007, and T011 can run in parallel after T005 starts.
- US1: T012 and T013 can run in parallel; T017 can run in parallel with T016.
- US2: T020, T021, and T022 can run in parallel.
- US3: T028 and T029 can run in parallel; T035 can run in parallel with compose wiring tasks after topology decisions are fixed.
- Polish: T037, T038, and T039 can run in parallel.

## Parallel Example: User Story 2

- Run T020, T021, and T022 together while endpoint behavior is being implemented.
- Run T025 and T026 in parallel after T024 defines API contract binding.

## Parallel Example: User Story 3

- Run T028 and T029 together while compose tests are being finalized.
- Run T033 and T034 in parallel after T032 sets compose service skeleton.

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1).
3. Validate lifespan startup/shutdown behavior and retry semantics independently.
4. Demo startup readiness as MVP.

### Incremental Delivery

1. Foundation: Phase 1 + Phase 2.
2. Add US1 and validate.
3. Add US2 and validate.
4. Add US3 and validate.
5. Execute Phase 6 polish and evidence capture.

### Parallel Team Strategy

1. Engineer A: Config/lifecycle foundations and US1.
2. Engineer B: Topic API and error-envelope behavior (US2).
3. Engineer C: Compose/bootstrap and documentation (US3).
