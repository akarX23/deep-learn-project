# Tasks: RAG Kafka Worker Simplification

**Input**: Design documents from `/specs/001-rag-retrieval-agent/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Include tests by default per constitution requirements and feature acceptance criteria.

**Organization**: Tasks are grouped by user story so each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no unfinished dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Include exact file paths in every task

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish baseline scaffolding for the simplified worker-first runtime.

- [ ] T001 [P] Normalize module-level logging setup in `rag_agent/worker.py`, `rag_agent/kafka.py`, `rag_agent/agent.py`, and `rag_agent/handlers.py` to use standard `logging.getLogger(__name__)`
- [ ] T002 [P] Remove stale backend topic bootstrap configuration references from `rag_agent/utils/helpers.py` and related env-read paths used by the worker startup flow
- [ ] T003 [P] Add explicit topic constants usage from `project/topics.py` in `rag_agent/kafka.py` for `rag` and `rag-complete` paths

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build core runtime boundaries required by all user stories.

**Checkpoint**: Worker can initialize Kafka objects and run startup checks without FastAPI or handler/factory orchestration.

- [ ] T004 Implement env-direct Kafka connector initialization and producer/consumer creation functions in `rag_agent/kafka.py`
- [ ] T005 Implement typed startup topic-presence metadata check function in `rag_agent/kafka.py` that returns missing-topic information without creating topics
- [ ] T006 Simplify `helpers.py` to env extraction helper functions only in `rag_agent/utils/helpers.py` (no config classes, no validators)
- [ ] T007 Refactor worker bootstrap in `rag_agent/worker.py` to initialize threaded consumer loop and call Kafka startup checks before entering steady-state polling

---

## Phase 3: User Story 1 - Run RAG as a Kafka Worker Process (Priority: P1) 🎯 MVP

**Goal**: Run as a standalone worker with a dedicated consumer loop and clean shutdown behavior.

**Independent Test**: Start the worker and verify polling starts without HTTP runtime and shutdown closes resources cleanly.

### Tests for User Story 1

- [ ] T008 [P] [US1] Update runtime lifecycle coverage in `rag_agent/tests/test_worker_runtime.py` for thread startup, idle polling continuity, and shutdown resource cleanup
- [ ] T009 [P] [US1] Update logging-stage assertions in `rag_agent/tests/test_logging.py` for worker lifecycle stages using standard logging

### Implementation for User Story 1

- [ ] T010 [US1] Implement worker main loop orchestration in `rag_agent/worker.py` to consume continuously from Kafka in a dedicated thread
- [ ] T011 [US1] Ensure worker shutdown path in `rag_agent/worker.py` stops loop thread and closes producer/consumer through `rag_agent/kafka.py` helpers

**Checkpoint**: User Story 1 is independently testable and no FastAPI runtime is required.

---

## Phase 4: User Story 2 - Verify Topic Presence Without Topic Creation (Priority: P2)

**Goal**: Perform startup topic presence checks with warning-only behavior when topics are missing.

**Independent Test**: Run startup against missing topics and verify warning logs with continued runtime startup.

### Tests for User Story 2

- [ ] T012 [P] [US2] Add startup topic-check test coverage in `rag_agent/tests/test_kafka_integration.py` for all-topics-present and missing-topic warning scenarios
- [ ] T013 [P] [US2] Add test coverage in `rag_agent/tests/test_kafka_integration.py` to assert no topic creation API or backend bootstrap path is invoked

### Implementation for User Story 2

- [ ] T014 [US2] Implement warn-and-continue startup topic presence behavior in `rag_agent/worker.py` using results from `rag_agent/kafka.py`
- [ ] T015 [US2] Remove topic creation behavior and backend API startup call paths from `rag_agent/kafka.py` and `rag_agent/worker.py`

**Checkpoint**: User Story 2 is independently testable with startup checks and no topic creation side effects.

---

## Phase 5: User Story 3 - Direct Consumer-to-Agent Flow Without Handler Abstraction (Priority: P3)

**Goal**: Consumer loop calls `agent.py` directly and publishes output via `kafka.py`; `agent.py` remains Kafka-agnostic.

**Independent Test**: Consume a request event, call `agent.py` directly, and publish completion to `rag-complete` without handler/factory indirection.

### Tests for User Story 3

- [ ] T016 [P] [US3] Update dispatch flow tests in `rag_agent/tests/test_request_event.py` to validate direct worker-to-agent invocation behavior
- [ ] T017 [P] [US3] Update completion publish path tests in `rag_agent/tests/test_completion_event.py` to validate publish from worker via `rag_agent/kafka.py`

### Implementation for User Story 3

- [ ] T018 [US3] Remove handler/factory orchestration from active consumer flow in `rag_agent/worker.py` and `rag_agent/handlers.py`
- [ ] T019 [US3] Ensure `rag_agent/agent.py` returns processing output only and contains no Kafka publish operations
- [ ] T020 [US3] Implement worker-side completion publish call path in `rag_agent/worker.py` using `rag_agent/kafka.py` producer functions
- [ ] T021 [US3] Add explicit TODO markers for deferred validation, edge-case handling, and exception-hardening in `rag_agent/worker.py`, `rag_agent/kafka.py`, `rag_agent/agent.py`, and `rag_agent/utils/helpers.py`

**Checkpoint**: User Story 3 is independently testable with direct consumer -> agent -> publish flow.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify end-to-end quality gates and documentation alignment.

- [ ] T022 [P] Run full `rag_agent` test suite with `pytest rag_agent/tests -q` and fix regressions
- [ ] T023 [P] Run quality checks `ruff check project rag_agent`, `ruff format --check project rag_agent`, and `python -m compileall project rag_agent`
- [ ] T024 [P] Validate `specs/001-rag-retrieval-agent/quickstart.md` against implemented startup/check/consume/publish flow and update drifted commands or expectations
- [ ] T025 [P] Review exported function signatures in `rag_agent/worker.py`, `rag_agent/kafka.py`, `rag_agent/agent.py`, and `rag_agent/utils/helpers.py` to remove unnecessary `Any` usage and keep explicit types

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1 completion
- **Phase 3 (US1)**: Depends on Phase 2 completion
- **Phase 4 (US2)**: Depends on Phase 2 completion
- **Phase 5 (US3)**: Depends on Phase 2 completion
- **Phase 6 (Polish)**: Depends on completion of US1, US2, and US3

### User Story Dependencies

- **US1 (P1)**: Foundational prerequisite for worker runtime; recommended MVP start
- **US2 (P2)**: Independent of US3 once foundational Kafka startup checks exist
- **US3 (P3)**: Independent of US2 once foundational consume/publish helpers exist

### Within Each User Story

- Write tests first for changed behavior
- Implement runtime path changes
- Validate with story-specific tests before moving on

### Parallel Opportunities

- T001, T002, and T003 can run in parallel
- T008 and T009 can run in parallel
- T012 and T013 can run in parallel
- T016 and T017 can run in parallel
- T022 through T025 can run in parallel during final polish

---

## Parallel Example: User Story 1

```bash
Task: "Update runtime lifecycle coverage in rag_agent/tests/test_worker_runtime.py for thread startup, idle polling continuity, and shutdown resource cleanup"
Task: "Update logging-stage assertions in rag_agent/tests/test_logging.py for worker lifecycle stages using standard logging"
Task: "Implement worker main loop orchestration in rag_agent/worker.py to consume continuously from Kafka in a dedicated thread"
```

## Parallel Example: User Story 2

```bash
Task: "Add startup topic-check test coverage in rag_agent/tests/test_kafka_integration.py for all-topics-present and missing-topic warning scenarios"
Task: "Add test coverage in rag_agent/tests/test_kafka_integration.py to assert no topic creation API or backend bootstrap path is invoked"
Task: "Implement warn-and-continue startup topic presence behavior in rag_agent/worker.py using results from rag_agent/kafka.py"
```

## Parallel Example: User Story 3

```bash
Task: "Update dispatch flow tests in rag_agent/tests/test_request_event.py to validate direct worker-to-agent invocation behavior"
Task: "Update completion publish path tests in rag_agent/tests/test_completion_event.py to validate publish from worker via rag_agent/kafka.py"
Task: "Ensure rag_agent/agent.py returns processing output only and contains no Kafka publish operations"
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 and Phase 2
2. Deliver User Story 1 (worker runtime)
3. Validate worker lifecycle tests

### Incremental Delivery

1. Deliver US1 (worker loop runtime)
2. Deliver US2 (topic presence check without creation)
3. Deliver US3 (direct consumer-to-agent flow)
4. Run full polish and quality gates

### Team Parallel Strategy

1. One engineer can implement US1 while another prepares US2 test coverage after Phase 2
2. US3 flow simplification can proceed in parallel with US2 implementation once foundational Kafka helpers are stable
