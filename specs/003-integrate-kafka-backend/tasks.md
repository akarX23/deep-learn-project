# Tasks: Backend Kafka Startup Topic Bootstrap

**Input**: Design documents from `/specs/003-integrate-kafka-backend/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Included — unit tests required per Constitution II. Test-driven approach: write tests that fail before implementation.

**Organization**: Single user story (P1) — all implementation tasks flow from one coherent feature.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Which user story this task belongs to (US1 for this feature)
- Paths shown below are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing project structure and add type model for bootstrap results

- [ ] T001 Confirm `project/topics.py` module exists and contains `PlannerTopics` and `RAGTopics` enums
- [ ] T002 [P] Add `StartupTopicBootstrapResult` dataclass to `project/schemas.py` with `created`, `already_existed`, and `errors` fields per data-model.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add aggregator function to topic registry

**⚠️ CRITICAL**: US1 implementation depends on this phase

- [ ] T003 Add `get_all_topic_names() -> list[str]` aggregator function to `project/topics.py` that returns union of `PlannerTopics.RAG` and `RAGTopics.RAG_COMPLETE`

**Checkpoint**: Topic registry aggregator ready; US1 implementation can now proceed

---

## Phase 3: User Story 1 - Bootstrap Kafka Topics from Project Registry on Startup (Priority: P1) 🎯 MVP

**Goal**: Backend service automatically creates all required Kafka topics on startup by reading from the shared registry, eliminating external provisioning steps.

**Independent Test**: Start backend service against connected Kafka cluster and verify all topics from `project/topics` are present in cluster after startup completes.

### Tests for User Story 1 (REQUIRED — write tests FIRST, ensure they FAIL before implementation)

- [ ] T004 [P] [US1] Add unit test `test_bootstrap_topics_creates_new_topics()` in `backend_service/tests/test_startup.py` covering scenario where all topics are created (use mock Kafka admin)
- [ ] T005 [P] [US1] Add unit test `test_bootstrap_topics_idempotent_with_existing()` in `backend_service/tests/test_startup.py` covering scenario where all topics already exist (returns "already_exists")
- [ ] T006 [P] [US1] Add unit test `test_bootstrap_topics_mixed_new_and_existing()` in `backend_service/tests/test_startup.py` covering mixed scenario with some topics new, some existing
- [ ] T007 [P] [US1] Add unit test `test_bootstrap_topics_empty_registry()` in `backend_service/tests/test_startup.py` covering scenario where registry returns empty topic list
- [ ] T008 [P] [US1] Add unit test `test_bootstrap_topics_transient_error_continues()` in `backend_service/tests/test_startup.py` covering non-fatal KafkaError on one topic — verifies remaining topics are still created and error is logged

### Implementation for User Story 1

- [ ] T009 [US1] Add `bootstrap_topics(self, topic_names: list[str]) -> StartupTopicBootstrapResult` method to `KafkaAdminService` class in `backend_service/app/kafka_admin.py`
  - Loop through each topic name
  - Call existing `create_topic(topic_name, num_partitions=1, replication_factor=1)`
  - Append "created" results to `result.created` list
  - Append "already_exists" results to `result.already_existed` list
  - Catch `RuntimeError` for transient broker errors, log WARNING, append to `result.errors` list, continue
  - Return `StartupTopicBootstrapResult` with all three lists populated
- [ ] T010 [US1] Import `get_all_topic_names()` from `project.topics` in `backend_service/app/main.py`
- [ ] T011 [US1] Extend FastAPI lifespan startup sequence in `backend_service/app/main.py`:
  - After `app.state.kafka_admin.connect()` succeeds
  - Call `topic_names = get_all_topic_names()`
  - Log INFO: `"Bootstrapping Kafka topics: %s"` with topic list
  - Call `result = app.state.kafka_admin.bootstrap_topics(topic_names)`
  - Log INFO: `"Topic bootstrap complete: %d created, %d already existed, %d errors"` with result counts
- [ ] T012 [US1] Add structured logging within `bootstrap_topics()` method:
  - Log DEBUG for each topic created: `"Topic created: %s"`
  - Log DEBUG for each topic already existed: `"Topic already exists: %s"`
  - Log WARNING for each error: `"Failed to bootstrap topic '%s': %s"` with topic name and error message
- [ ] T013 [US1] Add inline TODO comments in `bootstrap_topics()` method documenting deferred validation/health-check concerns per FR-006

**Checkpoint**: User Story 1 is fully functional and independently testable

---

## Phase 4: Integration & Contract Validation

**Purpose**: Verify integration with existing startup flow and validate startup contract

- [ ] T014 [P] Verify existing startup tests in `backend_service/tests/test_startup.py` (e.g., `test_startup_retry_then_success`, `test_shutdown_lifecycle_invokes_admin_close`) still pass without modification — regression gate
- [ ] T015 [US1] Add integration test `test_lifespan_includes_topic_bootstrap()` in `backend_service/tests/test_startup.py` that:
  - Creates a test FastAPI app with mocked Kafka admin
  - Verifies lifespan calls `bootstrap_topics()` after `connect()`
  - Verifies startup completes and service is ready
- [ ] T016 [US1] Validate startup contract from `backend-topic-bootstrap-contract.md`:
  - Startup logs include "Bootstrapping Kafka topics:" at INFO level
  - Startup logs include "Topic bootstrap complete:" at INFO level
  - All guaranteed behaviors (idempotency, error continuation, etc.) are honored
  - Record contract validation evidence in `specs/003-integrate-kafka-backend/quickstart.md`

**Checkpoint**: US1 integration with existing startup flow is validated

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Code quality, performance validation, documentation finalization

- [ ] T017 [P] Run quality checks and record results:
  - `.venv/bin/ruff check project backend_service` — must pass
  - `.venv/bin/ruff format --check project backend_service` — must pass
  - `.venv/bin/python -m compileall project backend_service` — must pass
  - Record output in `specs/003-integrate-kafka-backend/quickstart.md`
- [ ] T018 [P] Run full test suite:
  - `.venv/bin/python -m pytest backend_service/tests/ -q`
  - All tests must pass including new T004-T008 tests and regression tests
  - Record test evidence in `specs/003-integrate-kafka-backend/quickstart.md`
- [ ] T019 [US1] Measure and validate performance against SC-003:
  - Add timing measurement in unit test for `bootstrap_topics()` with mock admin (measure O(n) loop overhead)
  - Measure wall-clock startup time with 2-topic bootstrap against local Kafka cluster
  - Confirm ≤5 seconds per SC-003
  - Record benchmark result in `specs/003-integrate-kafka-backend/quickstart.md`
- [ ] T020 [US1] Test manual end-to-end startup flow:
  - Start local Kafka via docker compose: `docker compose up -d kafka kafka-ui`
  - Run backend service: `python -m backend_service.app.main`
  - Verify startup logs show successful bootstrap
  - Restart service and verify topics already-exist scenario
  - Verify Kafka UI shows topics created
  - Record E2E validation results in `specs/003-integrate-kafka-backend/quickstart.md`
- [ ] T021 [P] Add code comments documenting non-obvious decisions from research.md:
  - Idempotency via `TopicAlreadyExistsError` catch in existing `create_topic()`
  - Non-fatal error handling (log-and-continue) per edge case in spec
  - Why `get_all_topic_names()` is an aggregator (avoids caller coupling to enums)
- [ ] T022 Finalize `specs/003-integrate-kafka-backend/quickstart.md` with:
  - Expected startup output examples (both first run and idempotent run)
  - Performance timing measurements from T019
  - End-to-end validation evidence from T020
  - Quality check results from T017
  - Test results from T018
- [ ] T023 Update `CLAUDE.md` if backend service documentation needs to reference new startup behavior (optional based on team preferences)

**Checkpoint**: Feature is production-ready with full evidence trail

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion — BLOCKS US1
- **Phase 3 (US1 Implementation)**: Depends on Phase 2 completion
- **Phase 4 (Integration)**: Depends on Phase 3 completion
- **Phase 5 (Polish)**: Depends on Phases 3 & 4 completion

### Within Phase 3

1. **Write tests FIRST** (T004-T008): Ensure they fail before implementation
2. **Implement method** (T009): Add `bootstrap_topics()` to `KafkaAdminService`
3. **Integrate with lifespan** (T010-T011): Import and call in startup
4. **Add logging** (T012): Structured logs at each step
5. **Mark TODOs** (T013): Document deferred concerns per FR-006

### Parallel Opportunities

- **Phase 1**: T001 and T002 can run in parallel
- **Phase 3 Tests**: T004, T005, T006, T007, T008 can all be written in parallel before implementation starts
- **Phase 5 Quality**: T017 and T018 can run together; T019 and T020 can run in parallel

---

## Parallel Example: Phase 3 Test Writing

```
Task: "Add unit test test_bootstrap_topics_creates_new_topics() in backend_service/tests/test_startup.py"
Task: "Add unit test test_bootstrap_topics_idempotent_with_existing() in backend_service/tests/test_startup.py"
Task: "Add unit test test_bootstrap_topics_mixed_new_and_existing() in backend_service/tests/test_startup.py"
Task: "Add unit test test_bootstrap_topics_empty_registry() in backend_service/tests/test_startup.py"
Task: "Add unit test test_bootstrap_topics_transient_error_continues() in backend_service/tests/test_startup.py"

→ All can be written in parallel; all should FAIL before T009 implementation
```

---

## Implementation Strategy

### MVP Only (Recommended)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational — Critical gate
3. Complete Phase 3: US1 Implementation (write tests first, then code)
4. **STOP and VALIDATE** at Phase 4 checkpoint: Verify US1 is independently functional
5. Deploy to staging

### With Full Polish (if time permits)

1. Phases 1-4 above
2. Phase 5: Polish, testing, performance validation, documentation

### Expected Timeline

- Phase 1: ~15 min (verify existing structure)
- Phase 2: ~30 min (add aggregator function)
- Phase 3 Tests: ~1 hour (5 test scenarios, mock Kafka admin)
- Phase 3 Implementation: ~1 hour (bootstrap method, lifespan integration, logging)
- Phase 4: ~45 min (integration tests, contract validation)
- Phase 5: ~1.5 hours (quality checks, perf measurement, E2E test, finalization)

**Total MVP scope (Phases 1-4)**: ~3 hours  
**Total with Polish (Phases 1-5)**: ~4.5 hours

---

## Notes

- All T00X tasks are sequential within their phase for clarity; [P] markers indicate which can run in parallel
- [US1] label applies to all US1-specific work; general infrastructure (T001-T003) has no story label
- Test-driven approach: all tests (T004-T008) must be written and FAIL before implementation (T009-T013)
- Regression gate (T014): existing startup tests must continue to pass
- Performance validation (T019) uses mock Kafka for repeatability; E2E test (T020) validates against real local cluster
- Avoid: merging T009-T013 without passing T004-T008; skipping T019 performance measurement; incomplete T022 quickstart
- Stop at Phase 4 checkpoint to demonstrate independent US1 functionality before Polish phase
- Record all evidence (test results, timings, E2E output) in quickstart.md per constitution Principle V (observability)
