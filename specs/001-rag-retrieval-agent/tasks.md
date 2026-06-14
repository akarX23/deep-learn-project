# Tasks: RAG Kafka Worker Boilerplate Reduction

**Input**: Design documents from /specs/001-rag-retrieval-agent/
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included by default per constitution and behavior changes in worker runtime flow.
**Organization**: Tasks are grouped by user story for independent implementation and validation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align baseline tooling and docs context for feature 001 runtime refactor.

- [X] T001 Verify dependency set for worker runtime in requirements.txt
- [X] T002 [P] Confirm lint and format toolchain config in pyproject.toml and requirements.txt
- [X] T003 [P] Update feature quick checks and command references in specs/001-rag-retrieval-agent/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core simplification primitives required before user story work.

**CRITICAL**: User story implementation starts only after this phase is complete.

- [X] T004 Remove Kafka protocol type stubs from rag_agent/kafka.py
- [X] T005 Add concrete kafka-python type annotations at module boundaries in rag_agent/kafka.py
- [X] T006 Remove apply_kafka_security_options from rag_agent/utils/helpers.py
- [X] T007 Inline Kafka security option wiring into private kwargs builders in rag_agent/kafka.py
- [X] T008 Remove RAGWorker injectable constructor parameters from rag_agent/worker.py
- [X] T009 Remove RequestProcessor type alias and callback plumbing in rag_agent/worker.py
- [X] T010 Remove process_consumer_batch helper and related indirection in rag_agent/worker.py
- [X] T011 [P] Update WorkerRuntimeState field naming and mapping consistency in rag_agent/worker.py and project/schemas.py

**Checkpoint**: Runtime skeleton is simplified and ready for story-specific behavior work.

---

## Phase 3: User Story 1 - Run RAG as a Kafka Worker Process (Priority: P1) 🎯 MVP

**Goal**: Keep worker-only runtime with dedicated polling thread and clean shutdown.

**Independent Test**: Start worker and verify poll loop starts, idles, and shuts down cleanly without HTTP runtime.

### Tests for User Story 1

- [X] T012 [P] [US1] Update worker lifecycle thread start/stop tests in rag_agent/tests/test_worker_runtime.py
- [X] T013 [P] [US1] Add regression test for direct create_producer/create_consumer usage in rag_agent/tests/test_worker_runtime.py
- [X] T014 [P] [US1] Update runtime logging stage assertions for startup and shutdown in rag_agent/tests/test_logging.py

### Implementation for User Story 1

- [X] T015 [US1] Refactor RAGWorker.start to create Kafka clients directly via create_producer/create_consumer in rag_agent/worker.py
- [X] T016 [US1] Inline poll-and-dispatch logic directly inside _poll_loop in rag_agent/worker.py
- [X] T017 [US1] Refactor RAGWorker.stop to close consumer and producer directly in rag_agent/worker.py
- [X] T018 [US1] Keep per-iteration non-fatal exception handling and TODO markers in rag_agent/worker.py

**Checkpoint**: Worker runtime behavior is intact with reduced boilerplate.

---

## Phase 4: User Story 2 - Verify Topic Presence Without Topic Creation (Priority: P2)

**Goal**: Perform startup topic checks only, with warning-and-continue behavior.

**Independent Test**: Start worker with missing required topics and verify warning logs while worker still runs.

### Tests for User Story 2

- [X] T019 [P] [US2] Add topic-presence success and missing-topic warning tests in rag_agent/tests/test_kafka_integration.py
- [X] T020 [P] [US2] Add test that startup does not call topic creation flows in rag_agent/tests/test_kafka_integration.py
- [X] T021 [P] [US2] Add startup warning capture assertions in rag_agent/tests/test_logging.py

### Implementation for User Story 2

- [X] T022 [US2] Ensure startup check_required_topics call is retained and warning-only in rag_agent/worker.py
- [X] T023 [US2] Remove any residual topic creation code paths in rag_agent/kafka.py
- [X] T024 [US2] Keep startup check result mapping to WorkerRuntimeState warnings in rag_agent/worker.py

**Checkpoint**: Startup topic validation is lightweight and non-blocking.

---

## Phase 5: User Story 3 - Direct Consumer-to-Agent Flow Without Handler Abstraction (Priority: P3)

**Goal**: Consumer loop dispatches directly to agent and publishes completion via kafka.py.

**Independent Test**: Consume a rag request event, process through agent path, publish rag-complete from worker.

### Tests for User Story 3

- [X] T025 [P] [US3] Update direct dispatch tests for worker -> process_request_event in rag_agent/tests/test_request_event.py
- [X] T026 [P] [US3] Update completion publish ownership tests in rag_agent/tests/test_completion_event.py
- [X] T027 [P] [US3] Add regression test that agent has no Kafka publish dependency in rag_agent/tests/test_rag_agent.py
- [X] T028 [P] [US3] Add tests for tools document-only API signatures in rag_agent/tests/test_rag_agent.py

### Implementation for User Story 3

- [X] T029 [US3] Remove _with_optional_open helper and path branching from extraction functions in rag_agent/utils/tools.py
- [X] T030 [US3] Remove _page_from_source page-number guard and keep direct page load path in rag_agent/utils/tools.py
- [X] T031 [US3] Update extraction function signatures to accept only fitz.Document in rag_agent/utils/tools.py
- [X] T032 [US3] Update call sites to use document-only extraction APIs in rag_agent/agent.py
- [X] T033 [US3] Remove handler/factory leftovers from active flow in rag_agent/worker.py and rag_agent/handlers.py
- [X] T034 [US3] Ensure completion publish remains worker-owned via publish_rag_complete in rag_agent/worker.py
- [X] T035 [US3] Add TODO comments for deferred validation/metrics hardening in rag_agent/worker.py and rag_agent/kafka.py

**Checkpoint**: Direct consume -> process -> publish flow is simpler and functionally equivalent.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate all quality gates and artifact consistency.

- [X] T036 [P] Run full worker test suite in rag_agent/tests/ with pytest rag_agent/tests -q
- [X] T037 [P] Run lint checks with ruff check project rag_agent
- [X] T038 [P] Run formatting checks with ruff format --check project rag_agent
- [X] T039 [P] Run syntax validation with python -m compileall project rag_agent
- [X] T040 Verify line-count reduction objective (SC-007) across rag_agent/kafka.py, rag_agent/worker.py, and rag_agent/utils/tools.py
- [X] T041 [P] Reconcile quickstart commands with final runtime behavior in specs/001-rag-retrieval-agent/quickstart.md
- [X] T042 [P] Reconcile contract statements with final module boundaries in specs/001-rag-retrieval-agent/contracts/rag-agent-contract.md

**Checkpoint**: Feature is ready for implementation sign-off and downstream execution.

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies.
- Foundational (Phase 2): depends on Phase 1 and blocks all user stories.
- User Story phases (Phase 3 to Phase 5): each depends on Phase 2.
- Polish (Phase 6): depends on completion of targeted user stories.

### User Story Dependencies

- US1 (P1): can start immediately after Foundational.
- US2 (P2): can start after Foundational; independent from US1 implementation details.
- US3 (P3): can start after Foundational; consumes outcomes from core simplification but remains independently testable.

### Within Each User Story

- Story tests first, then implementation.
- Maintain Kafka ownership boundary in kafka.py.
- Keep agent Kafka-agnostic.

---

## Parallel Opportunities

- Setup tasks T002 and T003 can run in parallel.
- Foundational tasks T004, T006, T008, and T011 can run in parallel after initial file ownership assignment.
- US1 tests T012, T013, and T014 can run in parallel.
- US2 tests T019, T020, and T021 can run in parallel.
- US3 tests T025, T026, T027, and T028 can run in parallel.
- Polish tasks T036 to T039 and documentation tasks T041, T042 can run in parallel.

---

## Parallel Example: User Story 3

```bash
# Tests in parallel
Task: T025 Update direct dispatch tests in rag_agent/tests/test_request_event.py
Task: T026 Update completion publish ownership tests in rag_agent/tests/test_completion_event.py
Task: T028 Add tests for tools document-only API signatures in rag_agent/tests/test_rag_agent.py

# Implementation in parallel (non-overlapping files)
Task: T029 Remove _with_optional_open helper and path branching in rag_agent/utils/tools.py
Task: T033 Remove handler/factory leftovers in rag_agent/worker.py and rag_agent/handlers.py
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Deliver US1 and validate runtime lifecycle.
3. Deliver US2 startup-check behavior.
4. Deliver US3 direct flow simplification.

### Incremental Delivery

1. Runtime simplification baseline (Phase 2).
2. Worker lifecycle and direct polling (US1).
3. Startup topic checks and warnings (US2).
4. Consumer-to-agent and tools API simplification (US3).
5. Final quality and consistency checks (Phase 6).

### Team Parallel Strategy

1. Engineer A: Foundational Kafka/type simplification in rag_agent/kafka.py.
2. Engineer B: Worker lifecycle simplification in rag_agent/worker.py.
3. Engineer C: Tools API simplification in rag_agent/utils/tools.py and agent call-site updates.
4. Merge streams at Polish phase and run full suite.
