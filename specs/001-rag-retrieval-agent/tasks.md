# Tasks: RAG Agent Deterministic Parallel Loop Simplification

**Input**: Design documents from `/specs/001-rag-retrieval-agent/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/rag-agent-contract.md`, `quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare simple runtime configuration and test scaffolding for deterministic parallel page processing.

- [X] T001 Add simple page-parallelism env getter in `rag_agent/utils/helpers.py`
- [X] T002 [P] Add test fixture utilities for deterministic page ordering assertions in `rag_agent/tests/test_rag_agent.py`
- [X] T003 [P] Add test fixture utilities for failed-page list assertions in `rag_agent/tests/test_rag_agent.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Remove StateGraph dependency from agent page orchestration and establish minimal final state handling.

**CRITICAL**: No user story work starts before this phase is complete.

- [X] T004 Remove LangGraph StateGraph import/compile path from `rag_agent/agent.py`
- [X] T005 Implement deterministic page pointer builder with pointer order in `rag_agent/agent.py`
- [X] T006 Implement bounded parallel page dispatch loop in `rag_agent/agent.py`
- [X] T007 Implement deterministic reduce step by pointer order in `rag_agent/agent.py`
- [X] T008 Implement minimal final state structure (successful extracted content + failed page list) in `rag_agent/agent.py`
- [X] T009 [P] Add foundational regression test for non-StateGraph execution path in `rag_agent/tests/test_rag_agent.py`
- [X] T010 [P] Add foundational regression test for deterministic reduce ordering in `rag_agent/tests/test_rag_agent.py`

**Checkpoint**: Simplified deterministic parallel loop and minimal state foundations are ready.

---

## Phase 3: User Story 1 - Deterministic Parallel Page Processing (Priority: P1) 🎯 MVP

**Goal**: Process pages in parallel with simple deterministic control flow and stable output ordering.

**Independent Test**: Run multi-page request repeatedly and verify successful extracted content order always matches source pointer order.

### Tests for User Story 1

- [X] T011 [P] [US1] Add failing test for stable extracted content ordering across repeated runs in `rag_agent/tests/test_rag_agent.py`
- [X] T012 [P] [US1] Add failing test for deterministic retained-content aggregation in `rag_agent/tests/test_rag_agent.py`
- [X] T013 [P] [US1] Add failing test for bounded in-flight worker count using `RAG_PAGE_PARALLELISM` in `rag_agent/tests/test_rag_agent.py`

### Implementation for User Story 1

- [X] T014 [US1] Implement per-page worker function with basic extraction/relevance logic in `rag_agent/agent.py`
- [X] T015 [US1] Wire bounded parallel execution from pointer loop to worker function in `rag_agent/agent.py`
- [X] T016 [US1] Implement deterministic successful-page aggregation by pointer order in `rag_agent/agent.py`
- [X] T017 [US1] Keep page-processing semantics equivalent to current extraction status behavior in `rag_agent/agent.py`
- [X] T018 [US1] Keep compilation input assembly sourced only from successful extracted content in `rag_agent/agent.py`

**Checkpoint**: US1 complete and independently testable.

---

## Phase 4: User Story 2 - Failed Page Exclusion + Simple Failure List (Priority: P2)

**Goal**: Exclude failed pages from extracted content while maintaining a simple failed-page list with page number and reason.

**Independent Test**: Force selected page failures and verify they are absent from extracted content and present in failed-page list with reasons.

### Tests for User Story 2

- [X] T019 [P] [US2] Add failing test that failed pages are excluded from extracted content in `rag_agent/tests/test_rag_agent.py`
- [X] T020 [P] [US2] Add failing test that failed-page list includes page number and reason in `rag_agent/tests/test_rag_agent.py`
- [X] T021 [P] [US2] Add failing test that all failures are reflected in output errors summary in `rag_agent/tests/test_rag_agent.py`

### Implementation for User Story 2

- [X] T022 [US2] Add failed-page record structure (page number + reason) to agent runtime output assembly in `rag_agent/agent.py`
- [X] T023 [US2] Exclude failed pages from extracted content and retained context reduction in `rag_agent/agent.py`
- [X] T024 [US2] Aggregate failed-page reasons into simple output error list in `rag_agent/agent.py`
- [X] T025 [US2] Ensure final status derivation handles zero successful pages with failures in `rag_agent/agent.py`

**Checkpoint**: US2 complete and independently testable.

---

## Phase 5: User Story 3 - Stage Logging and Worker Flow Compatibility (Priority: P3)

**Goal**: Add clear stage logging in simplified agent flow while keeping worker-to-agent-to-publish integration unchanged.

**Independent Test**: Execute request flow and verify expected stage logs (`page_dispatched`, `page_processed`, `page_failed`, `state_reduced`) and unchanged worker publish behavior.

### Tests for User Story 3

- [X] T026 [P] [US3] Add failing test for stage log emission across page lifecycle in `rag_agent/tests/test_rag_agent.py`
- [X] T027 [P] [US3] Add failing regression test for worker direct dispatch behavior in `rag_agent/tests/test_worker_runtime.py`
- [X] T028 [P] [US3] Add failing regression test for completion publish path compatibility in `rag_agent/tests/test_kafka_integration.py`

### Implementation for User Story 3

- [X] T029 [US3] Add `page_dispatched` stage logging with request correlation in `rag_agent/agent.py`
- [X] T030 [US3] Add `page_processed` and `page_failed` stage logging in `rag_agent/agent.py`
- [X] T031 [US3] Add `state_reduced` stage logging after deterministic aggregation in `rag_agent/agent.py`
- [X] T032 [US3] Verify worker integration touchpoints remain unchanged after agent simplification in `rag_agent/worker.py`

**Checkpoint**: US3 complete and independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, docs alignment, and quality gate verification.

- [X] T033 [P] Update runtime notes for deterministic parallel loop in `specs/001-rag-retrieval-agent/quickstart.md`
- [X] T034 [P] Update contract wording for failed-page list and stage logs in `specs/001-rag-retrieval-agent/contracts/rag-agent-contract.md`
- [X] T035 [P] Update data model wording for minimal final state fields in `specs/001-rag-retrieval-agent/data-model.md`
- [X] T036 Run focused agent tests for deterministic ordering and failure-list behavior in `rag_agent/tests/test_rag_agent.py`
- [X] T037 Run worker/kafka regression tests in `rag_agent/tests/test_worker_runtime.py` and `rag_agent/tests/test_kafka_integration.py`
- [X] T038 Run repository quality gates (`ruff check`, `ruff format --check`, `compileall`) for `project/` and `rag_agent/`
- [X] T039 Record final implementation notes and residual risks in `specs/001-rag-retrieval-agent/plan.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies.
- Foundational (Phase 2): depends on Setup; blocks all user stories.
- User Stories (Phases 3-5): depend on Foundational completion.
- Polish (Phase 6): depends on selected user stories completion.

### User Story Dependencies

- US1 (P1): starts after Foundational; delivers MVP deterministic parallel page processing.
- US2 (P2): starts after Foundational; depends on US1 page result handling for failure exclusion.
- US3 (P3): starts after Foundational; validates logging and integration compatibility.

### Within Each User Story

- Tests first and failing before implementation.
- Core loop/aggregation logic before output shaping.
- Implementation before documentation and final quality gates.

### Parallel Opportunities

- T002 and T003 can run in parallel.
- T009 and T010 can run in parallel.
- T011-T013 can run in parallel.
- T019-T021 can run in parallel.
- T026-T028 can run in parallel.
- T033-T035 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# US1 parallel test workstream:
Task: "Add failing test for stable extracted content ordering across repeated runs in rag_agent/tests/test_rag_agent.py"
Task: "Add failing test for deterministic retained-content aggregation in rag_agent/tests/test_rag_agent.py"
Task: "Add failing test for bounded in-flight worker count using RAG_PAGE_PARALLELISM in rag_agent/tests/test_rag_agent.py"
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Setup and Foundational phases.
2. Complete US1 deterministic parallel loop behavior.
3. Validate US1 independently before expanding.

### Incremental Delivery

1. Deliver US1 (parallel deterministic page processing).
2. Deliver US2 (failed-page exclusion + simple failure list).
3. Deliver US3 (stage logging + compatibility checks).
4. Complete Polish and quality gates.

### Parallel Team Strategy

1. Team completes Setup and Foundational together.
2. After checkpoint, parallelize by story:
   - Developer A: US1 loop + ordering
   - Developer B: US2 failure-list behavior
   - Developer C: US3 logging and integration checks
