# Tasks: Planner Agent Orchestrator

**Input**: Design documents from `/specs/004-planner-agent/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included by default (constitution requires test evidence for behavior changes).

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure project scaffolding and shared contracts are ready for all user stories.

- [x] T001 [P] Ensure planner dependencies are present in `requirements.txt` (`langgraph>=1.2.0`, `langchain-core>=1.4.0`)
- [x] T002 [P] Create planner package scaffold in `planner_agent/__init__.py`, `planner_agent/agent.py`, `planner_agent/config.py`, `planner_agent/llm_client.py`, `planner_agent/kafka.py`, `planner_agent/prompts.py`, `planner_agent/worker.py`
- [x] T003 [P] Create planner test scaffold in `planner_agent/tests/__init__.py` and `planner_agent/tests/inputs/sample_input.json`
- [x] T004 [P] Add/update planner shared schema models in `project/schemas.py`: `UserLevelEnum`, `LevelInferenceResult`, `TeachingRequestEvent`, `QuizRequestEvent`, `ClarifyUserLevelEvent`, `WorkflowCompleteEvent`
- [x] T005 [P] Add/update planner topic enums in `project/topics.py`: `PlannerAgentTopics`, `AgentCompletionTopics`, and `get_all_topic_names()` aggregation
- [x] T006 [P] Register planner tests in `pytest.ini` (`planner_agent/tests`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build core planner infrastructure required by all user stories.

**CRITICAL**: No user story work should start before this phase is complete.

- [x] T007 [P] Implement planner-local LLM env configuration in `planner_agent/config.py` (`PLANNER_TEXT_*`, confidence threshold, bootstrap servers) with explicit return types
- [x] T008 [P] Implement planner-local LiteLLM wrapper in `planner_agent/llm_client.py` using planner config only (no `rag_agent` config imports)
- [x] T009 [P] Implement typed Kafka producer/consumer factories in `planner_agent/kafka.py` with JSON serialization/deserialization
- [x] T010 [P] Implement `LEVEL_QUIZ_INFERENCE_PROMPT` with structured JSON output contract in `planner_agent/prompts.py`
- [x] T011 Implement `PlannerState` `TypedDict` in `planner_agent/agent.py` with fields from `data-model.md`
- [x] T012 Implement schema-boundary helpers in `planner_agent/agent.py` and `planner_agent/worker.py` to parse inbound and serialize outbound events via `project/schemas.py`
- [x] T013 Implement stage-level logger calls in `planner_agent/agent.py` and `planner_agent/worker.py` for consume, assign, infer, route, dispatch, finish paths
- [x] T014 [P] Add foundational contract tests for schema/topic conformance in `planner_agent/tests/test_planner_agent.py`
- [x] T015 [P] Add foundational typing/signature tests and lint expectations in `planner_agent/tests/test_worker_runtime.py` and `planner_agent/tests/test_level_inference.py`
- [ ] T015a [P] Implement dotenv environment variable loading in `planner_agent/config.py` using `load_dotenv(override=False)` to preserve system-set variables
- [ ] T015b [P] Add unit test verifying dotenv does not override system-set environment variables in `planner_agent/tests/`

**Checkpoint**: Core planner plumbing, schema boundaries, observability, and environment management are ready.

---

## Phase 3: User Story 1 - Consume init-planner Events and Request Assignment (Priority: P1) 🎯 MVP

**Goal**: Consume `init-planner` events, assign unique `request_id`, initialize planner state, and keep worker runtime resilient.

**Independent Test**: Run `PlannerAgent.run()` and worker loop with valid + malformed input; verify unique IDs, state initialization, and non-crashing behavior.

### Tests for User Story 1

- [x] T016 [P] [US1] Add test for unique `request_id` assignment per run in `planner_agent/tests/test_planner_agent.py`
- [x] T017 [P] [US1] Add test for complete state initialization from `PlannerRequestEvent` in `planner_agent/tests/test_planner_agent.py`
- [x] T018 [P] [US1] Add worker test for malformed inbound event handling without process crash in `planner_agent/tests/test_worker_runtime.py`
- [x] T019 [P] [US1] Add worker logging test for consume/parse failure paths in `planner_agent/tests/test_worker_runtime.py`

### Implementation for User Story 1

- [x] T020 [US1] Implement `PlannerAgent.run(event: dict[str, object]) -> dict[str, object]` entry in `planner_agent/agent.py` with `request_id` generation and typed initial state
- [x] T021 [US1] Implement worker consume loop in `planner_agent/worker.py` for `init-planner` with schema parsing via `PlannerRequestEvent`
- [x] T022 [US1] Add request lifecycle logs (`request_id`, `sid`, topic, status) in `planner_agent/worker.py` and `planner_agent/agent.py`

**Checkpoint**: US1 is independently testable and operational.

---

## Phase 4: User Story 2 - Infer User Knowledge Level with Confidence Threshold (Priority: P1)

**Goal**: Infer level + quiz intent with planner-local LLM config, apply confidence threshold, and emit clarify event on low confidence/failure.

**Independent Test**: Mock LLM outputs and verify: high confidence continues, low confidence clarifies, pre-filled levels skip inference, and failures clarify.

### Tests for User Story 2

- [x] T023 [P] [US2] Add inference test for high-confidence result path (`user_levels`, `quiz_requested`) in `planner_agent/tests/test_level_inference.py`
- [x] T024 [P] [US2] Add inference test for low-confidence clarify path and topic publish in `planner_agent/tests/test_level_inference.py`
- [x] T025 [P] [US2] Add inference test for pre-defined levels skipping LLM call in `planner_agent/tests/test_level_inference.py`
- [x] T026 [P] [US2] Add inference test for LLM exception fallback to clarify event in `planner_agent/tests/test_level_inference.py`
- [x] T027 [P] [US2] Add test proving planner LLM config source is `planner_agent/config.py` only in `planner_agent/tests/test_level_inference.py`
- [x] T028 [P] [US2] Add logging-level test for inference decision branches in `planner_agent/tests/test_level_inference.py`

### Implementation for User Story 2

- [x] T029 [US2] Implement `_infer_level` node in `planner_agent/agent.py` with `LevelInferenceResult` parsing and threshold check
- [x] T030 [US2] Implement `_clarify_and_end` node in `planner_agent/agent.py` publishing `ClarifyUserLevelEvent` to `clarify-user-level`
- [x] T031 [US2] Wire infer-level routing (`continue` vs `clarify`) in `planner_agent/agent.py`
- [x] T032 [US2] Ensure explicit argument/return annotations for inference and clarify helpers in `planner_agent/agent.py`

**Checkpoint**: US2 inference and clarification behavior is independently testable.

---

## Phase 5: User Story 3 - Orchestrate Multi-Agent Workflow Creation (Priority: P2)

**Goal**: Route workflow through optional RAG, parallel teaching fan-out, and optional quiz dispatch with schema-conformant outbound events.

**Independent Test**: Verify event routing and payloads for files/no-files and quiz/no-quiz permutations with topic-level assertions.

### Tests for User Story 3

- [x] T033 [P] [US3] Add test for `run_rag` dispatch payload/topic conformance in `planner_agent/tests/test_planner_agent.py`
- [x] T034 [P] [US3] Add test confirming RAG path is skipped when `file_paths` is empty in `planner_agent/tests/test_planner_agent.py`
- [x] T035 [P] [US3] Add test for teaching fan-out count and per-level payload in `planner_agent/tests/test_planner_agent.py`
- [x] T036 [P] [US3] Add test for quiz dispatch when `quiz_requested` is true in `planner_agent/tests/test_planner_agent.py`
- [x] T037 [P] [US3] Add test for no quiz dispatch when `quiz_requested` is false in `planner_agent/tests/test_planner_agent.py`
- [x] T038 [P] [US3] Add logging tests for route and dispatch stages (`run_rag`, `teach_node`, `run_quiz`) in `planner_agent/tests/test_planner_agent.py`

### Implementation for User Story 3

- [x] T039 [US3] Implement `_route_rag` conditional in `planner_agent/agent.py`
- [x] T040 [US3] Implement `_run_rag` node in `planner_agent/agent.py` with schema-conformant outbound request payload
- [x] T041 [US3] Implement `_fan_out_teach` using `Send` API in `planner_agent/agent.py`
- [x] T042 [US3] Implement `_teach_node` in `planner_agent/agent.py` publishing `TeachingRequestEvent`
- [x] T043 [US3] Implement `_route_quiz` conditional and `_run_quiz` node in `planner_agent/agent.py` publishing `QuizRequestEvent`
- [x] T044 [US3] Wire US3 graph edges and interrupt/checkpoint behavior in `planner_agent/agent.py`

**Checkpoint**: US3 orchestration is independently testable and schema-safe.

---

## Phase 6: User Story 4 - Workflow Status Tracking and Intermediate Output Storage (Priority: P2)

**Goal**: Track state through completion path, consume completion events, resume workflows via `Command(resume=...)`, produce `workflow-complete`, and keep memory checkpoints retrievable by `request_id`.

**Independent Test**: Verify final payload composition, completion event consumption, graph resumption at correct nodes, state consistency, and output collection using pre-populated state snapshots.

### Tests for User Story 4

- [x] T045 [P] [US4] Add finish-node test for `workflow-complete` payload conformance in `planner_agent/tests/test_planner_agent.py`
- [x] T046 [P] [US4] Add finish-node test for `workflow_status = "complete"` in `planner_agent/tests/test_planner_agent.py`
- [x] T047 [P] [US4] Add checkpoint retrieval test by `thread_id = request_id` in `planner_agent/tests/test_planner_agent.py`
- [x] T048 [P] [US4] Add deferred test placeholder for `Command(resume=...)` completion updates in `planner_agent/tests/test_planner_agent.py`
- [ ] T048a [P] [US4] Add test for completion event consumption from `rag-complete`, `teaching-complete`, `quiz-complete` topics in `planner_agent/tests/`
- [ ] T048b [P] [US4] Add test verifying `Command(resume=...)` is issued with correct state after completion event in `planner_agent/tests/`
- [ ] T048c [P] [US4] Add test verifying intermediate outputs are extracted from completion events and merged into workflow state in `planner_agent/tests/`
- [ ] T048d [P] [US4] Add test verifying resumption correctness (graph resumes at dispatch node, state is restored, outputs preserved) in `planner_agent/tests/`

### Implementation for User Story 4

- [x] T049 [US4] Implement `_finish` node in `planner_agent/agent.py` publishing `WorkflowCompleteEvent`
- [x] T050 [US4] Wire `finish -> END` and completion-path logs in `planner_agent/agent.py`
- [x] T051 [US4] Add explicit TODO markers for deferred completion-consumer/resume flow in `planner_agent/agent.py` and `planner_agent/worker.py`
- [ ] T051a [US4] Implement completion event consumer in `planner_agent/worker.py` that subscribes to `rag-complete`, `teaching-complete`, `quiz-complete` topics
- [ ] T051b [US4] Implement completion event payload parsing and output extraction via schemas in `planner_agent/worker.py`
- [ ] T051c [US4] Implement resumption callback registry (request_id -> resume_callback) in `planner_agent/agent.py` to coordinate graph/consumer interaction
- [ ] T051d [US4] Implement `Command(resume=...)` invocation in completion consumer with updated state and outputs from completion event
- [ ] T051e [US4] Add logging at completion event consumption, output extraction, and resumption points in both agent and consumer loops

**Checkpoint**: US4 completion flow, event consumption, and graph resumption are independently testable and operational.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, quality gates, and docs/config consistency.

- [x] T052 [P] Add/refresh planner env examples in `.env.local.example` for all `PLANNER_TEXT_*` and `PLANNER_KAFKA_BOOTSTRAP_SERVERS`
- [x] T053 [P] Run planner test suite with evidence: `pytest planner_agent/tests -q`
- [x] T054 [P] Run quality gates: `ruff check project planner_agent` and `ruff format --check project planner_agent`
- [x] T055 [P] Run syntax gate: `python -m compileall project planner_agent -q`
- [x] T056 [P] Verify topic bootstrap regression in `backend_service/tests/test_startup.py` for expanded topic set from `project/topics.py`
- [x] T057 [P] Validate sample inputs in `planner_agent/tests/inputs/sample_input.json` cover empty-level+files and predefined-level+no-files paths
- [x] T058 [P] Update implementation notes and deferred-scope TODO references in `specs/004-planner-agent/quickstart.md` and `specs/004-planner-agent/research.md`
- [ ] T058a [P] Add unit test evidence for dotenv `override=False` behavior in test run output
- [ ] T058b [P] Add completion-event and resumption integration test evidence in test run output
- [ ] T058c [P] Run final quality gates with new tasks: `pytest planner_agent/tests -q`, `ruff check project planner_agent`, `ruff format --check project planner_agent`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1 and blocks all user-story phases.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 2; can proceed independently of US1 implementation details.
- **Phase 5 (US3)**: Depends on US2 (needs finalized `user_levels` and `quiz_requested`).
- **Phase 6 (US4)**: Depends on US3 routing/dispatch graph completion.
- **Phase 7 (Polish)**: Depends on all prior phases.

### User Story Dependencies

- **US1 (P1)**: First executable slice after foundational completion.
- **US2 (P1)**: Parallel priority story after foundational completion; feeds US3 routing state.
- **US3 (P2)**: Requires US2 inference outputs.
- **US4 (P2)**: Requires US3 graph wiring and final dispatch structure.

---

## Parallel Opportunities

- Setup tasks: T001, T002, T003, T004, T005, T006.
- Foundational tasks: T007, T008, T009, T010, T014, T015 can run in parallel; T011-T013 depend on foundational scaffolding.
- US1 tests: T016-T019 in parallel.
- US2 tests: T023-T028 in parallel.
- US3 tests: T033-T038 in parallel.
- US4 tests: T045-T048 in parallel.
- Polish tasks: T052-T058 in parallel where tooling allows.

---

## Parallel Example: User Story 1

```bash
Task: "T016 [US1] Add request_id assignment test in planner_agent/tests/test_planner_agent.py"
Task: "T017 [US1] Add state initialization test in planner_agent/tests/test_planner_agent.py"
Task: "T018 [US1] Add malformed inbound event test in planner_agent/tests/test_worker_runtime.py"
Task: "T019 [US1] Add worker logging test in planner_agent/tests/test_worker_runtime.py"
```

## Parallel Example: User Story 2

```bash
Task: "T023 [US2] Add high-confidence inference test in planner_agent/tests/test_level_inference.py"
Task: "T024 [US2] Add low-confidence clarify test in planner_agent/tests/test_level_inference.py"
Task: "T027 [US2] Add planner-local config source test in planner_agent/tests/test_level_inference.py"
Task: "T028 [US2] Add inference logging-level test in planner_agent/tests/test_level_inference.py"
```

## Parallel Example: User Story 3

```bash
Task: "T033 [US3] Add run_rag payload conformance test in planner_agent/tests/test_planner_agent.py"
Task: "T035 [US3] Add teaching fan-out test in planner_agent/tests/test_planner_agent.py"
Task: "T036 [US3] Add quiz dispatch test in planner_agent/tests/test_planner_agent.py"
Task: "T038 [US3] Add dispatch logging test in planner_agent/tests/test_planner_agent.py"
```

## Parallel Example: User Story 4

```bash
Task: "T045 [US4] Add workflow-complete payload test in planner_agent/tests/test_planner_agent.py"
Task: "T046 [US4] Add workflow status completion test in planner_agent/tests/test_planner_agent.py"
Task: "T047 [US4] Add checkpoint retrieval test in planner_agent/tests/test_planner_agent.py"
Task: "T048 [US4] Add deferred resume placeholder test in planner_agent/tests/test_planner_agent.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1 and Phase 2.
2. Deliver US1 request ingestion and request_id assignment.
3. Deliver US2 level inference and clarify branch.
4. Validate with tests before expanding orchestration.

### Incremental Delivery

1. Foundation: schema-safe plumbing, planner-local config, and logging.
2. US1: worker + graph entry and state initialization.
3. US2: inference routing and clarify event path.
4. US3: dispatch orchestration with fan-out and quiz routing.
5. US4: completion emission and checkpoint verification.
6. Polish: quality gates and documentation/contract verification.
