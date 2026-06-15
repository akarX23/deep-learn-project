# Tasks: Planner Agent Orchestrator

**Input**: Design documents from `/specs/004-planner-agent/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/planner-kafka-contract.md`, `quickstart.md`

**Tests**: Tests are required for this feature by constitution and specification (behavioral orchestration changes).

## Format: `[ID] [P?] [Story] Description`

- `[P]`: Can run in parallel (different files, no blocking dependency)
- `[Story]`: User story label (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align baseline scaffolding and test harness with current planner architecture.

- [ ] T001 Update planner feature quickstart workflow and command references in `specs/004-planner-agent/quickstart.md`
- [X] T002 [P] Add/refresh planner sample input fixture for init topic smoke tests in `planner_agent/tests/inputs/sample_input.json`
- [X] T003 [P] Ensure planner test package exports remain minimal and valid in `planner_agent/tests/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core plumbing required before user stories can be implemented safely.

**CRITICAL**: No user story work starts before this phase completes.

- [X] T004 Implement/align multi-topic consumer factory signature in `planner_agent/kafka.py`
- [X] T005 [P] Implement Kafka producer key support (`request_id`) in `planner_agent/kafka.py`
- [X] T006 [P] Add/align completion event schemas for teaching and quiz in `project/schemas.py`
- [X] T007 [P] Align topic enums and topic aggregation for planner completion topics in `project/topics.py`
- [X] T008 Enforce planner dotenv loading with `override=False` and defaults in `planner_agent/config.py`
- [ ] T009 [P] Add foundational contract/schema validation tests for planner payload models in `planner_agent/tests/test_planner_requirements.py`

**Checkpoint**: Foundation complete, user stories can proceed.

---

## Phase 3: User Story 1 - Consume init-planner Events and Assign request_id (Priority: P1) 🎯 MVP

**Goal**: Planner consumes init events, validates payloads, assigns request IDs, and keeps request context isolated.

**Independent Test**: Produce valid/invalid init events and verify `run_worker` routes to `PlannerAgent.run`, assigns unique `request_id`, and keeps loop alive on errors.

### Tests for User Story 1

- [ ] T010 [P] [US1] Add worker routing test for `init-planner` topic in `planner_agent/tests/test_worker_runtime.py`
- [ ] T011 [P] [US1] Add malformed init payload resilience test in `planner_agent/tests/test_worker_runtime.py`
- [ ] T012 [P] [US1] Add unique request_id assignment/isolation test in `planner_agent/tests/test_planner_agent.py`

### Implementation for User Story 1

- [X] T013 [US1] Refactor to a single `run_worker` with one consumer subscribed to all required topics in `planner_agent/worker.py`
- [X] T014 [US1] Implement `message.topic` branch logic and init handler dispatch in `planner_agent/worker.py`
- [X] T015 [US1] Validate `init-planner` payload through `PlannerRequestEvent` before `run` invocation in `planner_agent/worker.py`
- [X] T016 [US1] Ensure request context initialization and active request tracking are explicit in `planner_agent/agent.py`
- [X] T017 [US1] Add consume/assign/run stage logs with request correlation in `planner_agent/worker.py`

**Checkpoint**: US1 independently works and is testable.

---

## Phase 4: User Story 2 - Infer User Level with Confidence Threshold (Priority: P1)

**Goal**: Planner infers user level using planner-local LLM config or skips when user levels are provided; low-confidence path emits clarify event.

**Independent Test**: Verify skip path for provided levels, high-confidence finalize path, and low-confidence/failure clarify path.

### Tests for User Story 2

- [ ] T018 [P] [US2] Add/refresh provided-levels skip inference test in `planner_agent/tests/test_level_inference.py`
- [ ] T019 [P] [US2] Add/refresh high-confidence inference test in `planner_agent/tests/test_level_inference.py`
- [ ] T020 [P] [US2] Add/refresh low-confidence clarify emit test in `planner_agent/tests/test_level_inference.py`
- [ ] T021 [P] [US2] Add LLM failure fallback-to-clarify test in `planner_agent/tests/test_level_inference.py`
- [ ] T022 [P] [US2] Add dotenv non-override regression test in `planner_agent/tests/test_dotenv_loading.py`

### Implementation for User Story 2

- [X] T023 [US2] Implement/align planner-local LLM config usage in inference path in `planner_agent/agent.py`
- [X] T024 [US2] Implement/align confidence threshold gating and clarify transition in `planner_agent/agent.py`
- [X] T025 [US2] Implement/align `clarify-user-level` event publication using schema serialization in `planner_agent/agent.py`
- [X] T026 [US2] Ensure inference and clarify logs include reasons and confidence context in `planner_agent/agent.py`

**Checkpoint**: US2 independently works and is testable.

---

## Phase 5: User Story 3 - Orchestrate RAG/Teaching/Quiz Dispatch (Priority: P2)

**Goal**: Planner applies routing rules (files->RAG first, fan-out teaching per level, optional quiz) and publishes typed events keyed by request_id.

**Independent Test**: Run a request with files and multiple levels, verify dispatch order/fan-out/quiz gating and keyed produce behavior.

### Tests for User Story 3

- [ ] T027 [P] [US3] Add dispatch-order test (RAG first when files exist) in `planner_agent/tests/test_planner_agent.py`
- [ ] T028 [P] [US3] Add teaching fan-out per level test in `planner_agent/tests/test_planner_agent.py`
- [ ] T029 [P] [US3] Add quiz gating test (requested vs not requested) in `planner_agent/tests/test_planner_agent.py`
- [ ] T030 [P] [US3] Add request_id-keyed produce assertions for dispatched events in `planner_agent/tests/test_planner_agent.py`

### Implementation for User Story 3

- [X] T031 [US3] Implement/align route-after-infer and RAG branch rules in `planner_agent/agent.py`
- [X] T032 [US3] Implement/align teaching fan-out (publish one teaching request per level via `dispatch_teaching`) in `planner_agent/agent.py`
- [X] T033 [US3] Implement/align quiz routing and finish transition in `planner_agent/agent.py`
- [X] T034 [US3] Publish `rag`, `teaching-request`, and `quiz-request` using schema dumps and key=`request_id` in `planner_agent/agent.py`
- [X] T035 [US3] Add dispatch-stage structured logging (route/dispatch/topic/key) in `planner_agent/agent.py`

**Checkpoint**: US3 independently works and is testable.

---

## Phase 6: User Story 4 - Consume Completion Events and Resume Workflow (Priority: P2)

**Goal**: Single worker consumes completion topics, extracts outputs, resumes paused graph with `Command(resume=...)`, and emits workflow-complete.

**Independent Test**: Consume completion events in any order and verify output extraction, state merge, resume correctness, and final workflow completion emission.

### Tests for User Story 4

- [ ] T036 [P] [US4] Add completion topic parsing tests (`rag-complete`, `teaching-complete`, `quiz-complete`) in `planner_agent/tests/test_completion_resume.py`
- [ ] T037 [P] [US4] Add single-worker completion routing test (`message.topic` -> resume) in `planner_agent/tests/test_worker_runtime.py`
- [ ] T038 [P] [US4] Add malformed completion payload resilience test in `planner_agent/tests/test_worker_runtime.py`
- [ ] T039 [P] [US4] Add resume command invocation test using `Command(resume=...)` in `planner_agent/tests/test_completion_resume.py`
- [ ] T040 [P] [US4] Add merge semantics test for `teaching_materials` accumulation in `planner_agent/tests/test_completion_resume.py`
- [ ] T041 [P] [US4] Add end-to-end resume correctness test (pause->resume->complete) in `planner_agent/tests/test_completion_resume.py`

### Implementation for User Story 4

- [X] T042 [US4] Implement completion payload extraction helpers and topic-to-output mapping in `planner_agent/worker.py`
- [X] T043 [US4] Invoke `PlannerAgent.resume(request_id, outputs)` from completion handlers in `planner_agent/worker.py`
- [X] T044 [US4] Implement LangGraph pause points using `interrupt()` semantics in dedicated `await_*` nodes after producers in `planner_agent/agent.py`
- [X] T045 [US4] Implement resume path with `Command(resume=...)` and state snapshot retrieval in `planner_agent/agent.py`
- [X] T046 [US4] Implement output merge safeguards (self-describing teaching gather node accumulates `teaching_materials`) in `planner_agent/agent.py`
- [X] T047 [US4] Emit `workflow-complete` event when terminal state reached after resumptions in `planner_agent/agent.py`
- [X] T048 [US4] Add completion consume/extract/resume logs with request correlation in `planner_agent/worker.py`

**Checkpoint**: US4 independently works and is testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Finish quality gates, docs, and cross-story hardening.

- [ ] T049 [P] Update planner contract and spec alignment notes in `specs/004-planner-agent/contracts/planner-kafka-contract.md`
- [ ] T050 [P] Run and record planner test evidence (`pytest planner_agent/tests -q`) in `specs/004-planner-agent/quickstart.md`
- [ ] T051 Run lint/format/compile quality gates and record commands in `specs/004-planner-agent/quickstart.md`
- [X] T052 [P] Review/trim TODO markers and non-obvious design notes in `planner_agent/agent.py`
- [X] T053 [P] Verify all planner message boundaries use schemas and JSON serialization in `planner_agent/agent.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies
- **Phase 2 (Foundational)**: depends on Phase 1; blocks all user stories
- **Phase 3 (US1)**: depends on Phase 2
- **Phase 4 (US2)**: depends on Phase 2; can run in parallel with US1
- **Phase 5 (US3)**: depends on US1 + US2
- **Phase 6 (US4)**: depends on US3
- **Phase 7 (Polish)**: depends on all user stories

### User Story Dependencies

- **US1 (P1)**: starts after foundational readiness; no dependency on other stories
- **US2 (P1)**: starts after foundational readiness; no dependency on US1
- **US3 (P2)**: needs US1 event ingestion and US2 level outputs
- **US4 (P2)**: needs US3 dispatch flow and schema/topic foundations

### Within Each User Story

- Tests first where behavior changes
- Routing/state primitives before publish/resume integration
- Core behavior before logging polish

## Parallel Opportunities

- Foundational tasks `T005`, `T006`, `T007`, `T009`
- US1 tests `T010`, `T011`, `T012`
- US2 tests `T018`-`T022`
- US3 tests `T027`-`T030`
- US4 tests `T036`-`T041`
- Polish tasks `T049`, `T050`, `T052`, `T053`

## Parallel Example: User Story 4

```bash
# Run completion parsing and resume tests in parallel workstreams:
Task: T036 in planner_agent/tests/test_completion_resume.py
Task: T039 in planner_agent/tests/test_completion_resume.py
Task: T040 in planner_agent/tests/test_completion_resume.py

# In parallel, harden worker topic routing tests:
Task: T037 in planner_agent/tests/test_worker_runtime.py
Task: T038 in planner_agent/tests/test_worker_runtime.py
```

## Implementation Strategy

### MVP First (US1 only)

1. Complete Setup + Foundational (Phases 1-2)
2. Deliver US1 (Phase 3)
3. Validate worker ingestion behavior independently

### Incremental Delivery

1. Add US2 (inference/clarify)
2. Add US3 (dispatch orchestration)
3. Add US4 (completion consume + resume)
4. Run polish and quality gates

### Parallel Team Strategy

1. Team A: foundational schema/topic/kafka plumbing
2. Team B: US1 + US2 ingestion/inference
3. Team C: US3 + US4 orchestration/resume
4. Merge at phase checkpoints with full test gates
