# Tasks: Kafka Backend Integration Service

**Input**: Design documents from /specs/003-integrate-kafka-backend/
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the specification requires measurable startup behavior, API contract correctness, and error handling guarantees.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new backend service skeleton and baseline configuration artifacts.

- [ ] T001 Create backend service folder layout in backend_service/app/main.py, backend_service/app/api/topics.py, backend_service/app/config.py, backend_service/app/kafka_admin.py
- [ ] T002 Create backend test package scaffolding in backend_service/tests/test_startup.py and backend_service/tests/test_topics_api.py
- [ ] T003 [P] Add backend Python dependencies and test tooling entries in requirements.txt
- [ ] T004 [P] Add backend Kafka environment variable examples in .env.example and .env.local.example

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement core runtime wiring required before user stories.

**CRITICAL**: User story implementation starts only after this phase is complete.

- [ ] T005 Implement typed Kafka runtime settings model with .env.local loading and process-env override precedence in backend_service/app/config.py
- [ ] T006 [P] Implement Kafka admin client factory and connection helper interfaces in backend_service/app/kafka_admin.py
- [ ] T007 [P] Implement shared API response/error schema models in backend_service/app/api/topics.py
- [ ] T008 Wire FastAPI app factory, startup lifecycle hook, and dependency injection shell in backend_service/app/main.py
- [ ] T009 [P] Add foundational unit tests for env precedence and settings validation in backend_service/tests/test_startup.py

**Checkpoint**: Foundational runtime and config components are ready for story work.

---

## Phase 3: User Story 1 - Initialize Backend Kafka Connectivity (Priority: P1) 🎯 MVP

**Goal**: Service starts with Kafka admin initialization and retry behavior controlled by env values.

**Independent Test**: Start service with mocked Kafka availability/unavailability and verify retry + startup outcomes.

### Tests for User Story 1

- [ ] T010 [P] [US1] Add startup success test with valid Kafka config in backend_service/tests/test_startup.py
- [ ] T011 [P] [US1] Add retry-then-success startup test using configured retry count/timeouts in backend_service/tests/test_startup.py
- [ ] T012 [US1] Add retry-exhausted startup failure test with clear diagnostics in backend_service/tests/test_startup.py

### Implementation for User Story 1

- [ ] T013 [US1] Implement Kafka startup retry loop using startup_retry_count and startup_retry_timeout_seconds in backend_service/app/main.py
- [ ] T014 [P] [US1] Implement Kafka admin connectivity probe and exception mapping in backend_service/app/kafka_admin.py
- [ ] T015 [US1] Add startup logging/diagnostic messages for connection attempts and terminal failure in backend_service/app/main.py
- [ ] T016 [US1] Add fail-fast validation for missing required Kafka settings in backend_service/app/config.py

**Checkpoint**: US1 is independently functional and testable.

---

## Phase 4: User Story 2 - Create Kafka Topics via API (Priority: P2)

**Goal**: Provide only one topic-creation API with deterministic success/exists/error outcomes.

**Independent Test**: Call topic endpoint with valid, duplicate, and invalid payloads using mocked Kafka admin operations.

### Tests for User Story 2

- [ ] T017 [P] [US2] Add contract test for POST /api/v1/topics success response in backend_service/tests/test_topics_api.py
- [ ] T018 [P] [US2] Add duplicate-topic idempotency test returning already_exists in backend_service/tests/test_topics_api.py
- [ ] T019 [P] [US2] Add invalid payload validation test for topic endpoint in backend_service/tests/test_topics_api.py
- [ ] T020 [US2] Add runtime error mapping test for Kafka admin exceptions in backend_service/tests/test_topics_api.py

### Implementation for User Story 2

- [ ] T021 [US2] Implement POST /api/v1/topics endpoint request/response schemas in backend_service/app/api/topics.py
- [ ] T022 [US2] Implement topic creation service call path using KafkaAdminClient in backend_service/app/kafka_admin.py
- [ ] T023 [US2] Implement already_exists handling branch for duplicate topics in backend_service/app/api/topics.py
- [ ] T024 [US2] Restrict backend scope to only topic-creation route registration in backend_service/app/main.py

**Checkpoint**: US2 is independently functional and testable.

---

## Phase 5: User Story 3 - Provide Local Kafka + Kafka UI Infrastructure Bootstrap (Priority: P3)

**Goal**: Root docker-compose starts Kafka and Kafka UI with working UI-to-Kafka connectivity.

**Independent Test**: Bring up compose services and verify Kafka is running and Kafka UI is reachable/configured.

### Tests for User Story 3

- [ ] T025 [P] [US3] Add configuration test for compose service names and kafka-ui image value in backend_service/tests/test_startup.py
- [ ] T026 [US3] Add integration smoke script/assertion for Kafka UI reachability expectations in backend_service/tests/test_startup.py

### Implementation for User Story 3

- [ ] T027 [US3] Create root docker-compose.yaml with kafka and kafka-ui services and required environment variables in docker-compose.yaml
- [ ] T028 [US3] Configure kafka-ui service connection to kafka service in docker-compose.yaml
- [ ] T029 [P] [US3] Add backend/Kafka/Kafka UI local setup documentation in specs/003-integrate-kafka-backend/quickstart.md
- [ ] T030 [US3] Add root environment examples for compose and backend compatibility in .env.example

**Checkpoint**: US3 is independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality, consistency, and performance evidence.

- [ ] T031 [P] Update backend API contract examples and startup behavior details in specs/003-integrate-kafka-backend/contracts/backend-topic-api-contract.md
- [ ] T032 [P] Update design rationale and final tradeoffs in specs/003-integrate-kafka-backend/research.md
- [ ] T033 Enforce import grouping and code cleanup in backend_service/app/main.py, backend_service/app/config.py, backend_service/app/kafka_admin.py, backend_service/app/api/topics.py
- [ ] T034 Run full backend test suite and record evidence in specs/003-integrate-kafka-backend/quickstart.md
- [ ] T035 Validate startup retry and topic-create latency against plan budgets and record baseline in specs/003-integrate-kafka-backend/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1: No dependencies; starts immediately.
- Phase 2: Depends on Phase 1 and blocks all user stories.
- Phase 3 (US1): Depends on Phase 2 completion.
- Phase 4 (US2): Depends on Phase 2 completion; can proceed after or alongside US1 once foundational interfaces stabilize.
- Phase 5 (US3): Depends on Phase 2 completion; can proceed in parallel with US2.
- Phase 6: Depends on completion of targeted user stories.

### User Story Dependencies

- US1 (P1): No dependency on other stories after foundational phase.
- US2 (P2): Depends on foundational wiring but remains independently testable without US3.
- US3 (P3): Depends on foundational settings and compose definitions but remains independently testable without US2 endpoint internals.

### Within Each User Story

- Add story tests first and confirm failure conditions.
- Implement service logic after contract/validation scaffolding.
- Validate each story independently before progressing.

---

## Parallel Opportunities

- Setup: T003 and T004 can run in parallel.
- Foundational: T006, T007, and T009 can run in parallel after T005 starts.
- US1: T010 and T011 can run in parallel; T014 can run in parallel with T013 once interfaces are set.
- US2: T017, T018, and T019 can run in parallel.
- US3: T025 and T029 can run in parallel with T027 once compose skeleton exists.
- Polish: T031 and T032 can run in parallel.

## Parallel Example: User Story 2

- Run T017, T018, and T019 together while preparing endpoint implementation.
- Run T022 and T023 in parallel after T021 defines request/response models.

## Parallel Example: User Story 3

- Run T027 and T029 together after compose structure decisions are fixed.
- Run T025 while T028 finalizes kafka-ui connectivity wiring.

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1).
3. Validate startup connectivity/retry behavior independently.
4. Demo startup readiness as MVP.

### Incremental Delivery

1. Foundation: Phase 1 + Phase 2.
2. Add US1 and validate.
3. Add US2 and validate.
4. Add US3 and validate.
5. Execute Phase 6 polish and performance evidence.

### Parallel Team Strategy

1. Engineer A: startup/config foundations and US1.
2. Engineer B: topic API contract/tests and US2.
3. Engineer C: docker-compose + quickstart and US3.
