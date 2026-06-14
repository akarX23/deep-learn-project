# Tasks: Planner Agent Orchestrator

**Input**: Design documents from `specs/004-planner-agent/`
**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Include test tasks by default (constitution requires testing evidence).

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: New package scaffold, shared schemas, topics, and dependencies — required by all user stories.

- [x] T001 [P] Add `langgraph>=1.2.0` and `langchain-core>=1.4.0` to `requirements.txt`
- [x] T002 [P] Create `planner_agent/` package with `__init__.py`, `agent.py`, `config.py`, `kafka.py`, `prompts.py`, `worker.py`
- [x] T003 [P] Create `planner_agent/tests/` with `__init__.py` and `planner_agent/tests/inputs/sample_input.json`
- [x] T004 [P] Add `UserLevelEnum`, `LevelInferenceResult`, `TeachingRequestEvent`, `QuizRequestEvent`, `ClarifyUserLevelEvent`, `WorkflowCompleteEvent` to `project/schemas.py`
- [x] T005 [P] Add `PlannerAgentTopics` and `AgentCompletionTopics` enums to `project/topics.py` and update `get_all_topic_names()`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core planner infrastructure shared across all user stories — `config.py`, `kafka.py`, `prompts.py`, and `PlannerState`.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006 [P] Implement `planner_agent/config.py`: `get_llm_config()` reading `PLANNER_TEXT_MODEL`, `PLANNER_TEXT_API_BASE`, `PLANNER_TEXT_API_KEY`, `PLANNER_TEXT_TEMPERATURE`, `PLANNER_TEXT_MAX_TOKENS`, `PLANNER_LEVEL_CONFIDENCE_THRESHOLD`, `PLANNER_KAFKA_BOOTSTRAP_SERVERS` env vars
- [x] T007 [P] Implement `planner_agent/kafka.py`: `make_producer()` factory returning a `KafkaProducer` with JSON value serializer
- [x] T008 [P] Implement `planner_agent/prompts.py`: `LEVEL_QUIZ_INFERENCE_PROMPT` template string with `{user_prompt}` placeholder
- [x] T009 Implement `PlannerState` TypedDict in `planner_agent/agent.py`: fields `request_id`, `user_prompt`, `sid`, `user_levels`, `file_paths`, `quiz_requested`, `rag_compiled`, `teaching_materials`, `quiz_content`, `workflow_status`
- [x] T010 [P] Add `test_schemas_and_topics` tests verifying `UserLevelEnum`, `TeachingRequestEvent`, `QuizRequestEvent`, `ClarifyUserLevelEvent`, `WorkflowCompleteEvent` serialization and `get_all_topic_names()` includes all new topics in `planner_agent/tests/test_planner_agent.py`

**Checkpoint**: Foundation ready — user stories can now be developed independently.

---

## Phase 3: User Story 1 - Consume init-planner Events and Request Assignment (Priority: P1) 🎯 MVP

**Goal**: Worker consumes `init-planner` Kafka events, `PlannerAgent.run()` is invoked per message, a unique `request_id` is assigned, and the graph entry node initializes `PlannerState`.

**Independent Test**: Call `PlannerAgent.run()` with a valid `PlannerRequestEvent` dict; verify the returned `PlannerState` has a non-empty `request_id` and all event fields copied into state.

### Tests for User Story 1

- [x] T011 [P] [US1] Add test: `PlannerAgent.run()` with valid event assigns unique `request_id` (UUID hex, non-empty) in `planner_agent/tests/test_planner_agent.py`
- [x] T012 [P] [US1] Add test: two `PlannerAgent.run()` calls receive distinct `request_id` values in `planner_agent/tests/test_planner_agent.py`
- [x] T013 [P] [US1] Add test: worker skips malformed message (invalid JSON / missing fields) without crashing in `planner_agent/tests/test_worker_runtime.py`

### Implementation for User Story 1

- [x] T014 [US1] Implement `PlannerAgent` class in `planner_agent/agent.py`: constructor builds `StateGraph` with `MemorySaver`, `run(event_dict)` method generates `request_id = uuid.uuid4().hex`, initializes `PlannerState`, and invokes graph
- [x] T015 [US1] Implement worker consumer loop in `planner_agent/worker.py`: `KafkaConsumer` polling `init-planner`, deserializing JSON, calling `PlannerAgent.run()`, logging errors per message (basic try/except)

**Checkpoint**: User Story 1 complete — worker can consume and assign request IDs independently.

---

## Phase 4: User Story 2 - Infer User Knowledge Level with Confidence Threshold (Priority: P1)

**Goal**: `infer_level` graph node: if `user_levels` provided in event → use as-is and detect quiz intent; if empty → call LLM, parse `LevelInferenceResult`, finalize level if confidence ≥ threshold or produce `clarify-user-level` event and end graph.

**Independent Test**: Call `PlannerAgent.run()` monkeypatching `call_llm`. High-confidence response → `state["user_levels"]` set, graph continues. Low-confidence → `clarify-user-level` event produced, `workflow_status == "clarifying"`. Pre-defined levels → LLM not called.

### Tests for User Story 2

- [x] T016 [P] [US2] Add test: `infer_level` with LLM returning `confidence >= threshold` sets `user_levels` and `quiz_requested` in state (monkeypatch `call_llm`) in `planner_agent/tests/test_level_inference.py`
- [x] T017 [P] [US2] Add test: `infer_level` with `confidence < threshold` produces `clarify-user-level` Kafka event and sets `workflow_status = "clarifying"` (monkeypatch producer) in `planner_agent/tests/test_level_inference.py`
- [x] T018 [P] [US2] Add test: `infer_level` with non-empty `user_levels` in event skips LLM call and uses provided levels in `planner_agent/tests/test_level_inference.py`
- [x] T019 [P] [US2] Add test: `infer_level` with LLM failure logs error and produces `clarify-user-level` event (basic exception handling) in `planner_agent/tests/test_level_inference.py`

### Implementation for User Story 2

- [x] T020 [US2] Implement `infer_level` node in `planner_agent/agent.py`: check `state["user_levels"]`; if non-empty skip to quiz detection; if empty call `call_llm` with `LEVEL_QUIZ_INFERENCE_PROMPT`, parse JSON response to `LevelInferenceResult`; compare confidence to `PLANNER_LEVEL_CONFIDENCE_THRESHOLD`
- [x] T021 [US2] Implement `clarify_and_end` node in `planner_agent/agent.py`: publish `ClarifyUserLevelEvent` to `clarify-user-level` topic via producer, set `workflow_status = "clarifying"`
- [x] T022 [US2] Wire `infer_level` conditional edge in `planner_agent/agent.py`: `"clarify"` → `clarify_and_end` → END; `"continue"` → `route_rag`
- [x] T023 [P] [US2] Add TODO markers in `planner_agent/agent.py` for: quiz-only LLM call when levels are pre-provided, structured output parsing improvements, retry on LLM failure

**Checkpoint**: User Story 2 complete — level inference and clarification path independently testable.

---

## Phase 5: User Story 3 - Orchestrate Multi-Agent Workflow Creation (Priority: P2)

**Goal**: After level finalization, the graph conditionally runs RAG (if files present), fans out Teaching per level via `Send` API, and conditionally runs Quiz (if `quiz_requested`). Each node publishes a Kafka event then calls `interrupt()`.

**Independent Test**: Call `PlannerAgent.run()` with monkeypatched producer and `call_llm`. With files + 2 levels: verify `rag-request` event produced, then `teaching-request` ×2. Without files: no `rag-request`. Without quiz intent: no `quiz-request`. With quiz intent: `quiz-request` produced after teaching nodes.

### Tests for User Story 3

- [x] T024 [P] [US3] Add test: `run_rag` node produces `rag-request` event with correct `request_id`, `user_prompt`, `file_paths`, `sid` (monkeypatch producer + interrupt) in `planner_agent/tests/test_planner_agent.py`
- [x] T025 [P] [US3] Add test: graph skips `run_rag` when `file_paths` is empty in `planner_agent/tests/test_planner_agent.py`
- [x] T026 [P] [US3] Add test: `teach_node` produces `teaching-request` event with correct `user_level` and `rag_compiled` for each level in `planner_agent/tests/test_planner_agent.py`
- [x] T027 [P] [US3] Add test: fan-out produces one `teaching-request` event per user level (e.g., 2 levels → 2 events) in `planner_agent/tests/test_planner_agent.py`
- [x] T028 [P] [US3] Add test: `run_quiz` node produces `quiz-request` event only when `quiz_requested = True` in `planner_agent/tests/test_planner_agent.py`
- [x] T029 [P] [US3] Add test: no `quiz-request` produced when `quiz_requested = False` in `planner_agent/tests/test_planner_agent.py`

### Implementation for User Story 3

- [x] T030 [US3] Implement `route_rag` conditional function in `planner_agent/agent.py`: returns `"run_rag"` if `state["file_paths"]` non-empty, else `"fan_out_teach"`
- [x] T031 [US3] Implement `run_rag` node in `planner_agent/agent.py`: publish `RAGRequestEvent`-compatible dict to `rag-request` topic, call `interrupt()`; add TODO for Command(resume=...) resumption
- [x] T032 [US3] Implement `fan_out_teach` router function in `planner_agent/agent.py`: return `[Send("teach_node", {**state, "current_level": lvl}) for lvl in state["user_levels"]]`
- [x] T033 [US3] Implement `teach_node` in `planner_agent/agent.py`: publish `TeachingRequestEvent` to `teaching-request` topic with `user_level = state["current_level"]`, call `interrupt()`; add TODO for Command(resume=...) resumption
- [x] T034 [US3] Implement `route_quiz` conditional function in `planner_agent/agent.py`: returns `"run_quiz"` if `state["quiz_requested"]` else `"finish"`
- [x] T035 [US3] Implement `run_quiz` node in `planner_agent/agent.py`: publish `QuizRequestEvent` to `quiz-request` topic, call `interrupt()`; add TODO for Command(resume=...) resumption
- [x] T036 [US3] Wire all US3 nodes and edges in `StateGraph` in `planner_agent/agent.py`: `route_rag` conditional, `fan_out_teach` Send router, `route_quiz` conditional

**Checkpoint**: User Story 3 complete — full dispatch workflow independently testable via monkeypatched producer.

---

## Phase 6: User Story 4 - Workflow Status Tracking and Intermediate Output Storage (Priority: P2)

**Goal**: `finish` node collects all state outputs and publishes `workflow-complete` event. State fields `rag_compiled`, `teaching_materials`, `quiz_content` are populated by `Command(resume=...)` resumption (planned). `finish` sets `workflow_status = "complete"`. Tests verify `finish` publishes correctly and state fields are accessible by `request_id` via `MemorySaver`.

**Independent Test**: Run graph through `finish` node with pre-populated state (monkeypatched producer); verify `workflow-complete` event payload matches state fields and `workflow_status == "complete"`.

### Tests for User Story 4

- [x] T037 [P] [US4] Add test: `finish` node publishes `WorkflowCompleteEvent` with `request_id`, `sid`, `rag_compiled`, `teaching_materials`, `quiz_content` to `workflow-complete` topic in `planner_agent/tests/test_planner_agent.py`
- [x] T038 [P] [US4] Add test: `finish` sets `workflow_status = "complete"` in state in `planner_agent/tests/test_planner_agent.py`
- [x] T039 [P] [US4] Add test: `MemorySaver` checkpoint for a completed graph is accessible by `thread_id = request_id` (verify `graph.get_state(config)` returns expected state snapshot) in `planner_agent/tests/test_planner_agent.py`
- [x] T040 [P] [US4] Add TODO test placeholder: `Command(resume=completion_payload)` updates `rag_compiled` / `teaching_materials` / `quiz_content` in state (marked skip — future phase) in `planner_agent/tests/test_planner_agent.py`

### Implementation for User Story 4

- [x] T041 [US4] Implement `finish` node in `planner_agent/agent.py`: publish `WorkflowCompleteEvent` to `workflow-complete` topic, set `workflow_status = "complete"`
- [x] T042 [US4] Wire `finish` → END in `StateGraph` in `planner_agent/agent.py`
- [x] T043 [P] [US4] Add TODO markers in `planner_agent/agent.py` for: `Command(resume=...)` resumption filling `rag_compiled`, `teaching_materials`, `quiz_content`; Kafka consumer integration; timeout/incomplete workflow handling

**Checkpoint**: User Story 4 complete — full graph from entry to `workflow-complete` event independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, documentation validation, and `pytest.ini` registration.

- [x] T044 [P] Update `pytest.ini` to include `planner_agent/tests` in `testpaths` (or add separate `testpaths` entry)
- [x] T045 [P] Run full test suite: `pytest planner_agent/tests -q` — confirm all tests pass
- [x] T046 [P] Run `ruff check project planner_agent` and `ruff format --check project planner_agent` — confirm clean
- [x] T047 [P] Run `python -m compileall project planner_agent -q` — confirm no syntax errors
- [x] T048 [P] Verify `get_all_topic_names()` includes all new planner topics in `project/topics.py` and backend startup bootstrap test passes
- [x] T049 [P] Add `PLANNER_TEXT_*` and `PLANNER_KAFKA_BOOTSTRAP_SERVERS` env var examples to `.env.local.example`
- [x] T050 [P] Verify `planner_agent/tests/inputs/sample_input.json` covers at least: (a) event with `user_level=[]` and files, (b) event with pre-defined levels and no files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies. All T001–T005 parallelizable.
- **Phase 2 (Foundational)**: Depends on Phase 1. T006–T009 can run in parallel except T009 (needs T008 for prompts). T010 needs T004/T005.
- **Phase 3 (US1)**: Depends on Phase 2 completion.
- **Phase 4 (US2)**: Depends on Phase 2 completion. Independent of Phase 3 (different nodes/files).
- **Phase 5 (US3)**: Depends on Phase 4 completion (needs `infer_level` + level routing).
- **Phase 6 (US4)**: Depends on Phase 5 completion (needs all dispatch nodes wired).
- **Phase 7 (Polish)**: Depends on all user story phases.

### User Story Dependencies

- **US1 + US2 (P1)**: Can start in parallel after Phase 2; US1 = worker/entry, US2 = infer_level node.
- **US3 (P2)**: Depends on US2 (needs finalized `user_levels` and `quiz_requested` in state).
- **US4 (P2)**: Depends on US3 (needs all dispatch nodes present to wire `finish`).

---

## Parallel Opportunities

- Setup tasks T001–T005 run in parallel (different files).
- Foundational tasks T006, T007, T008 run in parallel; T009 follows T008.
- US1 tests T011–T013 run in parallel.
- US1 + US2 implementations run in parallel (T014–T015 vs T020–T023).
- US2 tests T016–T019 run in parallel.
- US3 tests T024–T029 run in parallel.
- US3 implementation T030–T035 can run in parallel (different node functions); T036 follows all.
- US4 tests T037–T040 run in parallel.
- Polish tasks T044–T050 run in parallel.

---

## Implementation Strategy

**MVP Scope**: Phase 1 + Phase 2 + Phase 3 (US1) + Phase 4 (US2) — delivers a working worker that consumes events, assigns IDs, infers levels, and routes to clarification. Demonstrates end-to-end graph execution.

**Incremental Delivery**:
1. Phase 1–2: Scaffold + shared contracts (no logic yet).
2. Phase 3: Worker + graph entry (independently runnable).
3. Phase 4: Level inference (graph reaches decision point).
4. Phase 5: Full dispatch (all agent events produced; graph pauses at interrupts).
5. Phase 6: Finish node (graph runs to completion for the no-interrupt path).
6. Phase 7: Quality gates (merge-ready).
