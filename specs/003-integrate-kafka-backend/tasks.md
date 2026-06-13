# Tasks: Backend Kafka Startup Bootstrap + RAG Test-Event API

**Input**: Design documents from `/specs/003-integrate-kafka-backend/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include test tasks by default. Omit tests only when the specification explicitly documents why a test type is not applicable.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Shared contract and configuration groundwork for the feature

- [X] T001 [P] Add test-event route enablement settings and boolean env parsing in backend_service/app/config.py for `APP_ENV` and `BACKEND_ENABLE_TEST_EVENT_APIS`
- [X] T002 [P] Add a shared producer handle to backend_service/app/kafka_admin.py so the test-events API can reuse the single producer instance owned by the Kafka layer

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core app plumbing that must be ready before story-specific implementation starts

**Checkpoint**: Backend app can accept optional route bundles while preserving the existing startup lifecycle

- [X] T003 Refactor backend_service/app/main.py to support conditional router registration for optional API bundles without changing the existing topics route behavior
- [X] T004 [P] Update backend_service/tests/test_startup.py fixtures and admin doubles so startup/lifespan tests can assert both topic bootstrap and future optional route wiring cleanly

---

## Phase 3: User Story 1 - Bootstrap Kafka Topics from Project Registry on Startup (Priority: P1) 🎯 MVP

**Goal**: Automatically create all Kafka topics from `project/topics` during backend startup

**Independent Test**: Start the backend service against a reachable Kafka cluster and verify that all topics returned by `project/topics.get_all_topic_names()` exist after startup completes

### Tests for User Story 1

- [X] T005 [US1] Extend backend_service/tests/test_startup.py with bootstrap success coverage for topic creation, idempotent existing-topic handling, and empty-registry behavior
- [X] T006 [US1] Extend backend_service/tests/test_startup.py with startup retry and failure coverage for unreachable Kafka and exhausted retry limits

### Implementation for User Story 1

- [X] T007 [US1] Extend backend_service/app/kafka_admin.py with `bootstrap_topics()` aggregation that records created topics, already-existing topics, and non-fatal errors in `StartupTopicBootstrapResult`
- [X] T008 [US1] Wire `project/topics.get_all_topic_names()` into backend_service/app/main.py lifespan so topic bootstrap runs after Kafka admin connect and before `yield`
- [X] T009 [US1] Update backend_service/app/main.py startup logging and backend_service/app/kafka_admin.py warning paths so bootstrap attempts, summaries, and deferred TODO behavior are visible in logs

**Checkpoint**: User Story 1 should now bootstrap Kafka topics on startup and remain independently testable

---

## Phase 4: User Story 2 - Publish RAG Test Events Through Backend API (Priority: P2)

**Goal**: Expose a gated backend API that publishes contract-valid `rag` test events to Kafka with a normalized success envelope

**Independent Test**: With test-event routes enabled, POSTing to `/api/v1/test-events/rag` publishes a valid `RAGRequestEvent` and returns the publish result envelope with Kafka metadata when available

### Tests for User Story 2

- [X] T010 [US2] Add contract coverage in backend_service/tests/test_test_events_api.py for `/api/v1/test-events/rag`, including environment gating, direct RAG request-body validation, and success response shape
- [X] T011 [US2] Add integration coverage in backend_service/tests/test_test_events_api.py for publish success, inline metadata handling, and Kafka failure/error-envelope behavior

### Implementation for User Story 2

- [X] T012 [US2] Implement the `rag` test-event router in backend_service/app/api/test_events.py with direct `RAGRequestEvent` request-body handling and publish validation before publish
- [X] T013 [US2] Add the optional test-events router to backend_service/app/main.py so routes are enabled by default in dev/test and require explicit opt-in in production
- [X] T014 [US2] Map Kafka producer acknowledgements to the normalized inline test-event response payload in backend_service/app/api/test_events.py, including optional metadata fields when available from the shared producer
- [X] T015 [US2] Extend backend_service/app/config.py policy handling so app creation can decide whether test-event routes are registered without per-request checks

**Checkpoint**: User Story 2 should now publish rag test events through a gated API and remain independently testable

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Finish, verify, and harden the feature across both user stories

- [X] T016 [P] Validate the full backend_service test suite with `pytest backend_service/tests -q` and repair any regressions introduced by the feature
- [ ] T017 [P] Run `ruff check project backend_service`, `ruff format --check project backend_service`, and `python -m compileall project backend_service` to confirm code quality and syntax integrity
- [ ] T018 [P] Validate `specs/003-integrate-kafka-backend/quickstart.md` against the implemented startup and rag test-event flows, and update any command/output examples that drifted
- [ ] T019 [P] Review logging and docstrings in backend_service/app/main.py, backend_service/app/kafka_admin.py, backend_service/app/api/test_events.py, and project/schemas.py for clarity and maintainability

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks user story implementation
- **User Stories (Phase 3+)**: Depend on Foundations being complete
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational phase completion - does not depend on US2
- **User Story 2 (P2)**: Can start after Foundational phase completion - does not depend on US1 for its core API behavior

### Within Each User Story

- Tests should be written before implementation when behavior changes
- Shared contracts and settings before route/service wiring
- Service logic before endpoint wiring
- Core implementation before integration and polish

### Parallel Opportunities

- Setup tasks T001 and T002 can run in parallel
- Foundational task T004 can run in parallel with T003 once test doubles are needed
- US1 tests T005 and T006 can be worked on in parallel if split across files or by separate contributors
- US2 tests T010 and T011 can be worked on in parallel if split across files or by separate contributors
- US2 implementation tasks T012, T013, T014, and T015 touch different files and can be staged independently once contracts are in place
- Polish tasks T016 through T019 can be run in parallel where they do not touch the same files

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
Task: "Add integration coverage in backend_service/tests/test_test_events_api.py for publish success, inline metadata handling, and Kafka failure/error-envelope behavior"
Task: "Implement the rag test-event router in backend_service/app/api/test_events.py with direct RAGRequestEvent request-body handling and publish validation before publish"
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
4. Run polish checks and update quickstart/documentation outputs

### Parallel Team Strategy

With multiple developers:

1. One developer can finish User Story 1 while another prepares User Story 2 test coverage
2. Once shared contracts are merged, one developer can wire the rag router while another updates route gating and response mapping
3. Finish with shared verification, linting, compile checks, and quickstart validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing behavior changes
- Record evidence for logging clarity and performance validation before completion
- Commit after each logical group when appropriate
- Avoid vague tasks, same-file parallel conflicts, and cross-story dependencies that break independence
