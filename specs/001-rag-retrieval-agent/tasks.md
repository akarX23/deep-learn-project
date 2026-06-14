# Tasks: RAG Agent Parallel Page Processing on LangGraph

**Input**: Design documents from `/specs/001-rag-retrieval-agent/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/rag-agent-contract.md`, `quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add runtime configuration and test scaffolding for bounded page parallelism.

- [ ] T001 Add `RAG_PAGE_PARALLELISM` env reading helper with default/clamp behavior in `rag_agent/utils/helpers.py`
- [ ] T002 [P] Add/refresh module-level doc comments for new parallelism configuration in `rag_agent/agent.py`
- [ ] T003 [P] Add shared test fixtures/utilities for parallel-page scenarios in `rag_agent/tests/test_rag_agent.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish core graph/state structure required by all user stories.

**CRITICAL**: No user story implementation begins before this phase completes.

- [ ] T004 Define/extend typed agent state for page-task result reduction in `rag_agent/agent.py`
- [ ] T005 Add typed per-page task result model/structure for deterministic merge in `rag_agent/agent.py`
- [ ] T006 Implement deterministic ordering helper for reduced page results in `rag_agent/agent.py`
- [ ] T007 [P] Add unit tests for deterministic ordering reducer in `rag_agent/tests/test_rag_agent.py`
- [ ] T008 Add bounded parallelism wiring point in graph execution path in `rag_agent/agent.py`
- [ ] T009 [P] Add tests for parallelism env parsing fallback/default/clamp in `rag_agent/tests/test_rag_agent.py`

**Checkpoint**: Core typed state + bounded runtime configuration ready.

---

## Phase 3: User Story 1 - Parallel Page Processing in Agent (Priority: P1) 🎯 MVP

**Goal**: Process document pages independently in parallel via LangGraph StateGraph while preserving page semantics.

**Independent Test**: Run RAG pipeline against multi-page input and verify pages are processed via parallel dispatch with expected extraction outputs.

### Tests for User Story 1

- [ ] T010 [P] [US1] Add failing regression test for sequential-vs-parallel equivalence in `rag_agent/tests/test_rag_agent.py`
- [ ] T011 [P] [US1] Add failing test for bounded in-flight page task count in `rag_agent/tests/test_rag_agent.py`
- [ ] T012 [P] [US1] Add failing test for page-level extraction status equivalence in `rag_agent/tests/test_rag_agent.py`

### Implementation for User Story 1

- [ ] T013 [US1] Refactor StateGraph nodes to dispatch page work independently in `rag_agent/agent.py`
- [ ] T014 [US1] Implement fan-out/fan-in reduction path for parallel page task results in `rag_agent/agent.py`
- [ ] T015 [US1] Preserve existing text/table/image extraction logic in per-page processing path in `rag_agent/agent.py`
- [ ] T016 [US1] Preserve relevance scoring and per-page status semantics in `rag_agent/agent.py`
- [ ] T017 [US1] Ensure reduced retained-page context remains deterministic before compilation in `rag_agent/agent.py`
- [ ] T018 [US1] Add structured debug logging for page dispatch/reduce lifecycle in `rag_agent/agent.py`

**Checkpoint**: US1 complete and independently testable with parallel page dispatch.

---

## Phase 4: User Story 2 - Env-Controlled Bounded Concurrency (Priority: P2)

**Goal**: Enforce configurable max page parallelism via env var with safe fallback behavior.

**Independent Test**: Set valid/invalid/missing `RAG_PAGE_PARALLELISM` values and verify default `4`, minimum clamp `1`, and bounded in-flight execution.

### Tests for User Story 2

- [ ] T019 [P] [US2] Add failing test for missing env var defaulting to `4` in `rag_agent/tests/test_rag_agent.py`
- [ ] T020 [P] [US2] Add failing test for invalid env var defaulting to `4` in `rag_agent/tests/test_rag_agent.py`
- [ ] T021 [P] [US2] Add failing test for min clamp behavior (`<1` -> `1`) in `rag_agent/tests/test_rag_agent.py`
- [ ] T022 [P] [US2] Add failing test for bounded maximum in-flight tasks at configured value in `rag_agent/tests/test_rag_agent.py`

### Implementation for User Story 2

- [ ] T023 [US2] Implement runtime parse/validation of `RAG_PAGE_PARALLELISM` in `rag_agent/utils/helpers.py`
- [ ] T024 [US2] Inject resolved page parallelism config into agent run path in `rag_agent/agent.py`
- [ ] T025 [US2] Enforce configured cap in graph dispatch execution in `rag_agent/agent.py`
- [ ] T026 [US2] Add warning-level log for invalid env fallback in `rag_agent/agent.py`

**Checkpoint**: US2 complete and independently testable for env-driven bounded concurrency.

---

## Phase 5: User Story 3 - Keep Worker Flow and Contracts Intact (Priority: P3)

**Goal**: Keep direct worker->agent->publish flow, no batching layer, and updated contracts/docs consistent with new parallel behavior.

**Independent Test**: Execute request flow through worker path and verify completion publishing remains unchanged while agent runs parallel page extraction.

### Tests for User Story 3

- [ ] T027 [P] [US3] Add regression test ensuring worker still dispatches directly to `process_request_event` in `rag_agent/tests/test_worker_runtime.py`
- [ ] T028 [P] [US3] Add regression test ensuring completion publishing path is unchanged in `rag_agent/tests/test_kafka_integration.py`
- [ ] T029 [P] [US3] Add regression test ensuring no explicit batching helper is required in `rag_agent/tests/test_rag_agent.py`

### Implementation for User Story 3

- [ ] T030 [US3] Verify and adjust worker-agent integration touchpoints for unchanged transport ownership in `rag_agent/worker.py`
- [ ] T031 [US3] Verify agent remains Kafka-agnostic after parallel refactor in `rag_agent/agent.py`
- [ ] T032 [US3] Update quickstart runtime flow to describe parallel processing and env controls in `specs/001-rag-retrieval-agent/quickstart.md`
- [ ] T033 [US3] Update contract language for bounded parallelism and no batching layer in `specs/001-rag-retrieval-agent/contracts/rag-agent-contract.md`
- [ ] T034 [US3] Update data model fields/transitions for page task reduction in `specs/001-rag-retrieval-agent/data-model.md`

**Checkpoint**: US3 complete and independently testable with docs/contracts aligned.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, cleanup, and release readiness evidence.

- [ ] T035 [P] Run targeted RAG agent tests for parallel behavior in `rag_agent/tests/test_rag_agent.py`
- [ ] T036 [P] Run worker/kafka regression tests in `rag_agent/tests/test_worker_runtime.py` and `rag_agent/tests/test_kafka_integration.py`
- [ ] T037 Run repository quality gates (`ruff check`, `ruff format --check`, `compileall`) from repository root via `rag_agent/` and `project/`
- [ ] T038 [P] Remove obsolete comments/TODOs contradicted by new parallel flow in `rag_agent/agent.py`
- [ ] T039 Validate quickstart commands end-to-end against runtime behavior in `specs/001-rag-retrieval-agent/quickstart.md`
- [ ] T040 Record final implementation notes and residual risks in `specs/001-rag-retrieval-agent/plan.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies.
- Foundational (Phase 2): Depends on Setup completion; blocks all user stories.
- User Story phases (Phase 3-5): Depend on Foundational completion.
- Polish (Phase 6): Depends on completion of all targeted user stories.

### User Story Dependencies

- US1 (P1): Starts after Foundational; delivers MVP parallel page processing.
- US2 (P2): Starts after Foundational; depends on US1 graph execution points for cap enforcement.
- US3 (P3): Starts after Foundational; validates integration and contract consistency.

### Within Each User Story

- Tests first and failing before implementation.
- State/config primitives before orchestration wiring.
- Core implementation before doc and integration verification.

### Parallel Opportunities

- T002, T003 can run in parallel during Setup.
- T007, T009 can run in parallel in Foundational phase.
- T010-T012 can run in parallel within US1.
- T019-T022 can run in parallel within US2.
- T027-T029 can run in parallel within US3.
- T035, T036, T038 can run in parallel in Polish phase.

---

## Parallel Example: User Story 2

```bash
# Run US2 tests in parallel workstreams:
Task: "Add failing test for missing env var defaulting to 4 in rag_agent/tests/test_rag_agent.py"
Task: "Add failing test for invalid env var defaulting to 4 in rag_agent/tests/test_rag_agent.py"
Task: "Add failing test for min clamp behavior (<1 -> 1) in rag_agent/tests/test_rag_agent.py"
Task: "Add failing test for bounded maximum in-flight tasks at configured value in rag_agent/tests/test_rag_agent.py"
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Setup + Foundational.
2. Complete US1 (parallel page dispatch and deterministic reduction).
3. Validate US1 independently before expanding scope.

### Incremental Delivery

1. Deliver US1 for core parallel processing.
2. Add US2 for production-safe env-controlled bounded concurrency.
3. Add US3 for integration/documentation alignment.
4. Complete Polish gates and release evidence.

### Team Parallelization

1. Team completes Setup and Foundational together.
2. Then split: one developer on US2 env behavior, one on US3 integration/docs, while US1 stabilizes.
