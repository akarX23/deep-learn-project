# Tasks: RAG Kafka Worker Simplification

**Input**: Design documents from `/specs/001-rag-retrieval-agent/`  
**Branch**: `[001-build-rag-retrieval-agent]` | **Date**: 2026-06-12  
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the specification and constitution require automated verification for worker lifecycle behavior, startup topic checks, consume-dispatch flow, non-fatal failures, and typed interface regressions.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align dependency/config surfaces with standalone worker runtime requirements.

- [X] T001 Remove FastAPI/uvicorn runtime dependency usage from `requirements.txt` and keep worker-relevant dependencies only
- [X] T002 [P] Remove backend topic API variable references from `.env.local.example` and add worker startup notes
- [X] T003 [P] Update runtime entrypoint documentation for worker process in `rag_agent/README.md`
- [X] T004 Confirm centralized topic registry includes required worker topics in `project/topics.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build core worker lifecycle and Kafka metadata check infrastructure that blocks all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Remove `BACKEND_API_TOPIC_URL` and related startup API config from `rag_agent/config.py`
- [X] T006 [P] Add typed `TopicPresenceCheckResult` and `WorkerRuntimeState` models in `project/schemas.py`
- [X] T007 Add typed Kafka metadata topic-presence check helper in `rag_agent/kafka.py`
- [X] T008 Create standalone worker runtime module with thread lifecycle (`start`, `run loop`, `stop`) in `rag_agent/worker.py`
- [X] T009 Migrate or remove FastAPI lifecycle orchestration from `rag_agent/service.py` and rewire runtime entry to `rag_agent/worker.py`
- [X] T010 [P] Add structured startup-stage logging (`startup_topic_check`) in `rag_agent/logging.py`

**Checkpoint**: Worker foundation is ready; user story implementation can proceed.

---

## Phase 3: User Story 1 - Run RAG as a Kafka Worker Process (Priority: P1) 🎯 MVP

**Goal**: Deliver a standalone background worker process that continuously consumes events without HTTP runtime dependency.

**Independent Test**: Start worker process, verify consumer thread enters polling loop, and verify clean shutdown closes Kafka resources.

### Tests for User Story 1

- [X] T011 [P] [US1] Add worker startup/shutdown lifecycle test in `rag_agent/tests/test_worker_runtime.py`
- [X] T012 [P] [US1] Add consumer loop continues-when-idle test in `rag_agent/tests/test_worker_runtime.py`
- [X] T013 [P] [US1] Add non-fatal per-event failure continuation test in `rag_agent/tests/test_worker_runtime.py`

### Implementation for User Story 1

- [X] T014 [US1] Implement dedicated poll thread bootstrap and stop signaling in `rag_agent/worker.py`
- [X] T015 [US1] Implement typed single-batch poll dispatch helper for worker loop in `rag_agent/worker.py`
- [X] T016 [US1] Wire worker entrypoint (`python -m rag_agent.worker`) for process startup in `rag_agent/worker.py`
- [X] T017 [US1] Ensure graceful shutdown closes consumer and producer in `rag_agent/kafka.py` and `rag_agent/worker.py`

**Checkpoint**: Worker runtime is independently functional and testable.

---

## Phase 4: User Story 2 - Verify Topic Presence Without Topic Creation (Priority: P2)

**Goal**: Perform startup topic metadata checks and warn on missing topics while continuing startup.

**Independent Test**: Start worker against mocked metadata showing missing topics and verify startup warning while worker remains running.

### Tests for User Story 2

- [X] T018 [P] [US2] Add startup topic check success test in `rag_agent/tests/test_worker_runtime.py`
- [X] T019 [P] [US2] Add missing-topic warning-and-continue startup test in `rag_agent/tests/test_worker_runtime.py`
- [X] T020 [P] [US2] Add regression test asserting no backend topic API call path is used in `rag_agent/tests/test_worker_runtime.py`

### Implementation for User Story 2

- [X] T021 [US2] Remove startup topic-creation API call behavior from `rag_agent/kafka.py`
- [X] T022 [US2] Implement required-topic presence check on startup in `rag_agent/worker.py`
- [X] T023 [US2] Emit clear actionable warning when required topics are missing in `rag_agent/logging.py`
- [X] T024 [US2] Remove backend API dependency notes from runtime docs in `rag_agent/README.md` and `specs/001-rag-retrieval-agent/quickstart.md`

**Checkpoint**: Startup topic verification flow is independently functional and testable.

---

## Phase 5: User Story 3 - Use a Minimal Typed Event Handler (Priority: P3)

**Goal**: Keep event handling focused on ingest+dispatch with explicit typing and deferred TODO markers for advanced validation/metrics.

**Independent Test**: Consume a request event and verify typed handler dispatches to RAG pipeline and completion publish path with TODO markers present for deferred concerns.

### Tests for User Story 3

- [X] T025 [P] [US3] Add typed-handler signature contract test in `rag_agent/tests/test_request_event.py`
- [X] T026 [P] [US3] Add ingest-to-dispatch integration test in `rag_agent/tests/test_kafka_integration.py`
- [X] T027 [P] [US3] Add TODO marker coverage test for deferred validation/metrics in `rag_agent/tests/test_request_event.py`

### Implementation for User Story 3

- [X] T028 [US3] Refactor `RAGRequestEventHandler` to minimal ingest+dispatch flow with explicit TODO markers in `rag_agent/handlers.py`
- [X] T029 [US3] Replace broad untyped parameters and returns in handler interfaces with explicit types in `rag_agent/handlers.py`
- [X] T030 [US3] Replace broad untyped worker/Kafka function signatures with explicit typed boundaries in `rag_agent/worker.py` and `rag_agent/kafka.py`
- [X] T031 [US3] Keep completion mapping and publish flow tied to request correlation in `rag_agent/handlers.py`

**Checkpoint**: Minimal typed handler flow is independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Complete quality, performance, and end-to-end validation evidence.

- [X] T032 [P] Update architecture and operational docs for worker runtime in `rag_agent/README.md` and `specs/001-rag-retrieval-agent/quickstart.md`
- [ ] T033 [P] Run quality checks (`.venv/bin/ruff check`, `.venv/bin/ruff format --check`, `.venv/bin/python -m compileall`) and capture output references in `specs/001-rag-retrieval-agent/quickstart.md`
- [X] T034 Run targeted worker and Kafka integration tests via `.venv/bin/python -m pytest` in `rag_agent/tests/test_worker_runtime.py` and `rag_agent/tests/test_kafka_integration.py`
- [X] T035 [P] Add poll-to-completion latency measurement script or test helper in `rag_agent/tests/test_worker_runtime.py`
- [ ] T036 Validate quickstart end-to-end flow against local Kafka and record results in `specs/001-rag-retrieval-agent/quickstart.md`
- [X] T037 Capture final implementation evidence and remaining deferred TODO scope in `specs/001-rag-retrieval-agent/research.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2.
- **Phase 4 (US2)**: Depends on Phase 2; can proceed in parallel with US3 after foundation is complete.
- **Phase 5 (US3)**: Depends on Phase 2; can proceed in parallel with US2 after foundation is complete.
- **Phase 6 (Polish)**: Depends on completion of target user stories.

### User Story Dependencies

- **US1 (P1)**: No dependency on US2/US3 after foundation.
- **US2 (P2)**: Depends on foundational worker startup and Kafka helper availability; independent from US3 logic.
- **US3 (P3)**: Depends on foundational worker/Kafka modules; independent from US2 startup-warning behavior.

### Within Each User Story

- Write tests first and ensure they fail before implementation.
- Implement core story behavior, then complete logging/edge handling.
- Validate story-specific independent test criteria before moving on.

---

## Parallel Opportunities

- **Setup**: T002 and T003 can run in parallel.
- **Foundational**: T006 and T010 can run in parallel after T005 starts.
- **US1 tests**: T011, T012, T013 can run in parallel.
- **US2 tests**: T018, T019, T020 can run in parallel.
- **US3 tests**: T025, T026, T027 can run in parallel.
- **Polish**: T032, T033, and T035 can run in parallel.

## Parallel Example: User Story 1

```bash
# Parallel test authoring for US1 worker lifecycle:
Task: "Add worker startup/shutdown lifecycle test in rag_agent/tests/test_worker_runtime.py"
Task: "Add consumer loop continues-when-idle test in rag_agent/tests/test_worker_runtime.py"
Task: "Add non-fatal per-event failure continuation test in rag_agent/tests/test_worker_runtime.py"
```

## Parallel Example: User Story 3

```bash
# Parallel US3 typed-handler validation tasks:
Task: "Add typed-handler signature contract test in rag_agent/tests/test_request_event.py"
Task: "Add ingest-to-dispatch integration test in rag_agent/tests/test_kafka_integration.py"
Task: "Add TODO marker coverage test for deferred validation/metrics in rag_agent/tests/test_request_event.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational).
3. Complete Phase 3 (US1).
4. Validate US1 independently using worker lifecycle tests.
5. Demonstrate standalone worker operation as MVP.

### Incremental Delivery

1. Foundation first: Setup + Foundational.
2. Add US1 and validate worker lifecycle.
3. Add US2 and validate startup topic check warnings.
4. Add US3 and validate minimal typed handler behavior.
5. Finish with Phase 6 quality/performance evidence.

### Parallel Team Strategy

1. Team completes setup and foundational work together.
2. After foundation:
   - Developer A: US1 worker lifecycle tasks
   - Developer B: US2 startup topic check tasks
   - Developer C: US3 typed handler tasks
3. Merge into polish/performance validation.

---

## Notes

- Task format strictly follows checklist requirements.
- User-story tasks include `[US1]`, `[US2]`, or `[US3]` labels.
- All tasks include explicit file paths.
- Deferred validation/metrics work remains tracked via explicit TODO tasks in US3.
- Keep branch and feature directory unchanged throughout execution.
