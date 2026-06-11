# Tasks: UI Frontend for Multi-Agent Tutor

**Input**: Design documents from `/specs/004-ui-frontend/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/frontend-websocket-event-contract.md`, `quickstart.md`

**Tests**: Include test tasks by default because behavior changes are required across routing, reconnect, schema validation, and simulation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., `US1`, `US2`, `US3`, `US4`)
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize frontend module scaffolding and project-level dependencies/config for websocket UI work.

- [X] T001 Create frontend package scaffold in `ui_frontend/__init__.py`
- [X] T002 Add Streamlit dependency to `requirements.txt`
- [X] T003 [P] Create frontend environment loader in `ui_frontend/config.py`
- [X] T004 [P] Create Streamlit application shell with tab placeholders in `ui_frontend/app.py`
- [X] T005 [P] Add frontend package test scaffold in `ui_frontend/tests/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared contracts and core runtime plumbing required before any user story implementation.

**CRITICAL**: No user story work begins until this phase completes.

- [X] T006 Extend websocket event schemas/enums in `project/schemas.py`
- [X] T007 Implement connection lifecycle model/state helpers in `ui_frontend/state.py`
- [X] T008 Implement websocket client with connect/reconnect lifecycle in `ui_frontend/websocket_client.py`
- [X] T009 Implement schema-validated router core in `ui_frontend/router.py`
- [ ] T010 [P] Implement diagnostics capture utilities in `ui_frontend/diagnostics.py`
- [ ] T011 [P] Add shared test fixtures for websocket events in `ui_frontend/tests/fixtures/events.py`
- [ ] T012 Add foundational unit tests for schemas and router bootstrap in `ui_frontend/tests/test_router.py`

**Checkpoint**: Foundation ready - user story implementation can begin.

---

## Phase 3: User Story 1 - Live Teaching Chat Experience (Priority: P1) MVP

**Goal**: Stream teaching tokens to chat while planner status updates render concurrently with reconnect recovery.

**Independent Test**: Connect to websocket source, emit teaching token + planner status events, force disconnect, verify reconnect and continued rendering in Chat + Status.

### Tests for User Story 1

- [ ] T013 [P] [US1] Add teaching token stream ordering test in `ui_frontend/tests/test_chat_stream.py`
- [ ] T014 [P] [US1] Add planner status rendering state test in `ui_frontend/tests/test_status_panel.py`
- [ ] T015 [P] [US1] Add reconnect transition integration test in `ui_frontend/tests/test_websocket_client.py`

### Implementation for User Story 1

- [ ] T016 [US1] Implement chat stream reducer for `teaching.token` and `teaching.complete` in `ui_frontend/state.py`
- [ ] T017 [US1] Implement planner status reducer for `planner.status` in `ui_frontend/state.py`
- [ ] T018 [US1] Wire US1 event routes in `ui_frontend/router.py`
- [ ] T019 [US1] Render Chat tab with incremental token append behavior in `ui_frontend/app.py`
- [ ] T020 [US1] Render live Status panel connection and planner progress UI in `ui_frontend/app.py`
- [ ] T021 [US1] Integrate reconnect callbacks and UI state transitions in `ui_frontend/websocket_client.py`

**Checkpoint**: US1 fully functional and independently testable.

---

## Phase 4: User Story 2 - Quiz Event Workflow (Priority: P2)

**Goal**: Route quiz lifecycle events to Quiz tab with stable state across tab switches and imperfect payloads.

**Independent Test**: Emit quiz lifecycle sequence including sparse optional fields and verify Quiz tab state progression and persistence when switching tabs.

### Tests for User Story 2

- [ ] T022 [P] [US2] Add quiz lifecycle progression test in `ui_frontend/tests/test_quiz_state.py`
- [ ] T023 [P] [US2] Add quiz optional-field resilience test in `ui_frontend/tests/test_quiz_state.py`
- [ ] T024 [P] [US2] Add tab-switch state persistence test in `ui_frontend/tests/test_app_tabs.py`

### Implementation for User Story 2

- [ ] T025 [US2] Implement quiz lifecycle reducer and validation fallbacks in `ui_frontend/state.py`
- [ ] T026 [US2] Add quiz event routing (`quiz.started`, `quiz.question`, `quiz.feedback`, `quiz.completed`) in `ui_frontend/router.py`
- [ ] T027 [US2] Implement Quiz tab UI rendering with lifecycle-aware sections in `ui_frontend/app.py`

**Checkpoint**: US2 fully functional and independently testable.

---

## Phase 5: User Story 3 - Evaluation Results Visibility (Priority: P3)

**Goal**: Route evaluation results to Evaluation tab with latest-result emphasis and retained prior context.

**Independent Test**: Emit multiple evaluation.result events and verify latest summary prominence plus historical context availability.

### Tests for User Story 3

- [ ] T028 [P] [US3] Add evaluation latest-result precedence test in `ui_frontend/tests/test_evaluation_state.py`
- [ ] T029 [P] [US3] Add evaluation history retention test in `ui_frontend/tests/test_evaluation_state.py`

### Implementation for User Story 3

- [ ] T030 [US3] Implement evaluation reducer for latest + history tracking in `ui_frontend/state.py`
- [ ] T031 [US3] Add `evaluation.result` route handling in `ui_frontend/router.py`
- [ ] T032 [US3] Implement Evaluation tab UI sections for strengths/gaps/recommendations in `ui_frontend/app.py`

**Checkpoint**: US3 fully functional and independently testable.

---

## Phase 6: User Story 4 - Reliable Event Routing and Simulation (Priority: P4)

**Goal**: Provide deterministic mock simulation and safe handling of unknown events while preserving valid event processing.

**Independent Test**: Run built-in simulator scenarios and unknown-event injection; verify correct destination routing and diagnostics without UI crash.

### Tests for User Story 4

- [ ] T033 [P] [US4] Add simulator parity test (simulated vs live routing path) in `ui_frontend/tests/test_simulator.py`
- [ ] T034 [P] [US4] Add unknown event non-crash and diagnostics test in `ui_frontend/tests/test_router.py`
- [ ] T035 [P] [US4] Add simulator/live exclusivity behavior test in `ui_frontend/tests/test_simulator.py`

### Implementation for User Story 4

- [ ] T036 [US4] Implement deterministic scenario playback engine in `ui_frontend/simulator.py`
- [ ] T037 [US4] Add simulator controls (start/pause/reset/scenario/speed) in `ui_frontend/app.py`
- [ ] T038 [US4] Implement unknown/invalid event diagnostic routing path in `ui_frontend/router.py`
- [ ] T039 [US4] Enforce simulator/live source arbitration in `ui_frontend/websocket_client.py`

**Checkpoint**: US4 fully functional and independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final quality, docs, and performance checks spanning all stories.

- [ ] T040 [P] Add end-to-end routing matrix test coverage in `ui_frontend/tests/test_router.py`
- [ ] T041 [P] Add event latency measurement helper and assertions in `ui_frontend/tests/test_performance_budget.py`
- [ ] T042 Update feature quickstart verification steps based on actual implementation commands in `specs/004-ui-frontend/quickstart.md`
- [ ] T043 Run and document final acceptance checklist results in `specs/004-ui-frontend/checklists/requirements.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies.
- Foundational (Phase 2): depends on Setup completion; blocks all user stories.
- User Stories (Phases 3-6): all depend on Foundational completion.
- Polish (Phase 7): depends on completion of desired user stories.

### User Story Dependencies

- US1 (P1): starts after Phase 2; no dependency on other stories.
- US2 (P2): starts after Phase 2; independent of US1 for core behavior.
- US3 (P3): starts after Phase 2; independent of US1/US2 for core behavior.
- US4 (P4): starts after Phase 2; uses shared router/state abstractions but remains independently testable.

### Within Each User Story

- Tests first (fail-before-pass expectation).
- Reducers/state handling before UI rendering.
- Routing before final UI integration.

---

## Parallel Opportunities

- Setup: `T003`, `T004`, `T005` can run in parallel.
- Foundational: `T010` and `T011` can run in parallel after `T006`.
- US1: `T013`, `T014`, `T015` can run in parallel.
- US2: `T022`, `T023`, `T024` can run in parallel.
- US3: `T028`, `T029` can run in parallel.
- US4: `T033`, `T034`, `T035` can run in parallel.
- Polish: `T040` and `T041` can run in parallel.

---

## Parallel Example: User Story 1

```bash
# Parallel test tasks for US1
T013  ui_frontend/tests/test_chat_stream.py
T014  ui_frontend/tests/test_status_panel.py
T015  ui_frontend/tests/test_websocket_client.py

# Then implement reducers and UI wiring
T016 -> T018 -> T019/T020 -> T021
```

## Parallel Example: User Story 2

```bash
# Parallel test tasks for US2
T022  ui_frontend/tests/test_quiz_state.py
T023  ui_frontend/tests/test_quiz_state.py
T024  ui_frontend/tests/test_app_tabs.py
```

## Parallel Example: User Story 4

```bash
# Parallel test tasks for US4
T033  ui_frontend/tests/test_simulator.py
T034  ui_frontend/tests/test_router.py
T035  ui_frontend/tests/test_simulator.py
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate US1 independently (teaching stream + status + reconnect).
4. Demo/deploy MVP if acceptable.

### Incremental Delivery

1. Foundation complete.
2. Deliver US1 and validate.
3. Deliver US2 and validate independently.
4. Deliver US3 and validate independently.
5. Deliver US4 and validate simulator/unknown-event resilience.
6. Complete Phase 7 polish and evidence capture.

### Team Parallel Strategy

1. Team completes Phases 1-2 together.
2. After foundation:
   - Engineer A: US1
   - Engineer B: US2
   - Engineer C: US3
   - Engineer D: US4
3. Merge story slices after each independent test pass.

---

## Notes

- `[P]` marks tasks designed for safe parallel execution.
- `[USx]` labels provide traceability to user stories and acceptance criteria.
- Avoid coupling story behavior in a way that blocks independent testing.
- Keep schema contract updates in sync with router logic and tests.
