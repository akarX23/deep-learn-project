# Tasks: RAG Kafka Event Integration

**Input**: Design documents from `specs/001-rag-retrieval-agent/`  
**Branch**: `[001-build-rag-retrieval-agent]` | **Date**: 2026-06-11  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[ID]**: Sequential task number (T001, T002, ...)
- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3) for user-story-phase tasks only
- **File paths**: Exact locations for implementation

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Kafka module structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize Kafka dependencies in requirements.txt (kafka-python, httpx, FastAPI/Uvicorn)
- [ ] T003 [P] Setup environment variable template in .env.local.example
- [ ] T004 Create project/topics.py with TopicRegistry enum (rag, rag-complete)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Kafka infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Create rag_agent/config.py with KafkaRuntimeConfig class (inherit BACKEND_KAFKA* flags)
- [ ] T006 [P] Update project/schemas.py with RAGRequestEvent and RAGCompletionEvent Pydantic models
- [ ] T007 Create rag_agent/kafka.py with KafkaProducer and KafkaConsumer initialization (single gateway module)
- [ ] T008 Create rag_agent/service.py with FastAPI app and lifespan context manager (startup/shutdown hooks)
- [ ] T009 Implement startup topic bootstrap call in rag_agent/service.py (POST to BACKEND_API_TOPIC_URL)
- [ ] T010 [P] Add graceful shutdown with consumer/producer cleanup in service.py lifespan

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Consume RAG Requests From Kafka (Priority: P1) 🎯 MVP

**Goal**: Enable RAG agent to consume request events from topic `rag` and trigger retrieval pipeline execution

**Independent Test**: Publish a valid request event to topic `rag` and verify the RAG pipeline is invoked once with matching request payload

### Tests for User Story 1 (REQUIRED)

- [ ] T011 [P] [US1] Contract test for RAGRequestEvent validation in rag_agent/tests/test_request_event.py
- [ ] T012 [P] [US1] Integration test for event consumption from topic rag in rag_agent/tests/test_kafka_integration.py
- [ ] T013 [P] [US1] Integration test for request dispatch to RAGAgent pipeline in rag_agent/tests/test_kafka_integration.py

### Implementation for User Story 1

- [ ] T014 [US1] Create rag_agent/handlers.py with RAGRequestEventHandler class and process_request() method
- [ ] T015 [US1] Implement RAGRequestEvent validation logic in handlers.py (required fields, non-empty checks)
- [ ] T016 [US1] Initialize consumer subscription to topic `rag` in rag_agent/kafka.py (consumer_subscribe_rag())
- [ ] T017 [US1] Implement consumer poll loop in rag_agent/service.py (continuous polling with error continuation)
- [ ] T018 [US1] Map consumed raw event to RAGRequestEvent Pydantic model in handlers.py
- [ ] T019 [US1] Invoke existing RAGAgent.run() with request payload in handlers.py (map user_request→prompt)

**Checkpoint**: User Story 1 complete - RAG can now consume requests from Kafka and trigger processing

---

## Phase 4: User Story 2 - Publish RAG Completion Events (Priority: P2)

**Goal**: Publish completion events to topic `rag-complete` with retrieval output and metadata for downstream orchestration

**Independent Test**: Trigger one valid `rag` request event and verify one `rag-complete` event is published with required fields (session_ctx, user_prompt, compiled_material, status)

### Tests for User Story 2 (REQUIRED)

- [ ] T020 [P] [US2] Contract test for RAGCompletionEvent payload shape in rag_agent/tests/test_completion_event.py
- [ ] T021 [P] [US2] Integration test for topic rag-complete event publishing in rag_agent/tests/test_kafka_integration.py
- [ ] T022 [P] [US2] Integration test for request-to-completion correlation metadata in rag_agent/tests/test_kafka_integration.py

### Implementation for User Story 2

- [ ] T023 [US2] Create completion event publisher producer_publish_rag_complete() in rag_agent/kafka.py
- [ ] T024 [US2] Implement RAGProcessingResult→RAGCompletionEvent mapping in handlers.py (map RAGAgent output to completion contract)
- [ ] T025 [US2] Add event.json serialization for Kafka producer in handlers.py (with session_ctx preservation)
- [ ] T026 [US2] Call completion publisher after RAG processing in handlers.py (whether success, partial, or failed)
- [ ] T027 [US2] Include error metadata in RAGCompletionEvent when processing fails (FR-007 compliance)

**Checkpoint**: User Stories 1 AND 2 complete - full request-to-completion flow is operational

---

## Phase 5: User Story 3 - Track End-to-End Progress Logs (Priority: P3)

**Goal**: Emit structured progress logs at key lifecycle stages for operational traceability and diagnostics

**Independent Test**: Submit a request and verify logs include correlation metadata and all stages (consume, validate, process_start, process_end, publish_complete)

### Tests for User Story 3 (REQUIRED)

- [ ] T028 [P] [US3] Contract test for structured RequestLifecycleLogEntry format in rag_agent/tests/test_logging.py
- [ ] T029 [P] [US3] Integration test for lifecycle logging across all stages in rag_agent/tests/test_kafka_integration.py
- [ ] T030 [P] [US3] Integration test for error-stage logging when processing fails in rag_agent/tests/test_kafka_integration.py

### Implementation for User Story 3

- [ ] T031 [US3] Create rag_agent/logging.py with StructuredLogger and emit_log_entry() (RFC 3339 timestamp, correlation metadata)
- [ ] T032 [US3] Add consumed-stage log emission in consumer poll loop (service.py) after message received
- [ ] T033 [US3] Add validated-stage log emission in handlers.py after RAGRequestEvent validation passes
- [ ] T034 [US3] Add processing_started log emission in handlers.py when RAGAgent.run() is invoked
- [ ] T035 [US3] Add processing_completed log emission in handlers.py after RAGAgent.run() returns (with status)
- [ ] T036 [US3] Add publish_completed log emission in handlers.py after rag-complete event is published
- [ ] T037 [US3] Add error-stage log emission for validation failures and per-request exceptions (non-fatal continuation)

**Checkpoint**: All user stories complete - full integration with observability ready for deployment

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality validation, documentation, and end-to-end verification

- [ ] T038 [P] Update rag_agent/README.md with Kafka integration documentation (consumer setup, topic contract, startup bootstrap)
- [ ] T039 [P] Run quality checks: ruff check, ruff format --check, python -m compileall on rag_agent/
- [ ] T040 Run full test suite: pytest rag_agent/tests/test_kafka_integration.py -v (all US1/US2/US3 integration tests pass)
- [ ] T041 Validate quickstart.md walkthrough: install → .env.local → docker compose up → service startup → publish test event → verify completion event
- [ ] T042 [P] Add end-to-end integration test for complete request-to-completion lifecycle in rag_agent/tests/test_e2e.py
- [ ] T043 [P] Performance validation: measure p95 consume-to-complete latency against SC-005 budget
- [ ] T044 Record evidence: log output from quickstart validation, test run output, performance measurements

---

## Dependencies & Execution Order

### Phase Dependencies

```
Setup (Phase 1)
    ↓
Foundational (Phase 2) ← BLOCKS all user stories
    ↓
US1 (Phase 3) ←→ US2 (Phase 4) ←→ US3 (Phase 5) [can run in parallel after Foundational]
    ↓
Polish (Phase 6)
```

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - CRITICAL BLOCKER
- **User Stories (Phase 3-5)**: All depend on Foundational completion
  - Can run in parallel (by different developers) once Foundational is done
  - Or sequentially P1 → P2 → P3 (one developer)
  - Each story is independently testable
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each User Story Phase

1. **Tests FIRST**: Write and run contract/integration tests (should FAIL initially)
2. **Implementation**: Code implementation to make tests pass
3. **Validation**: All tests pass, implementation meets spec acceptance criteria
4. **Ready to deploy**: Story complete before moving to next priority

### Parallel Opportunities

**Setup Phase (T001-T004)**:
- All [P] tasks can run in parallel

**Foundational Phase (T005-T010)**:
- T006 and T010 can run in parallel (different files)
- All others must follow dependency chain: T005 → T007 → T008 → T009

**User Story 1 Tests (T011-T013)**:
- All contract/integration tests marked [P] can run in parallel

**User Story 1 Implementation (T014-T019)**:
- Must follow sequence (validation before dispatch before subscription before polling)

**User Story 2 Tests (T020-T022)**:
- All marked [P] can run in parallel

**User Story 2 Implementation (T023-T027)**:
- Publisher must be created first (T023), then mapping (T024), then invocation (T026)

**User Story 3 Tests (T028-T030)**:
- All marked [P] can run in parallel

**User Story 3 Implementation (T031-T037)**:
- Logger created first (T031), then all log emissions can run in parallel across modules

**Polish Phase (T038-T044)**:
- Documentation (T038) and quality checks (T039) can run in parallel
- All validation tasks can run in parallel after tests pass

### Developer Team Example

**Single Developer** (Sequential):
1. Complete Setup (T001-T004)
2. Complete Foundational (T005-T010)
3. Complete US1 tests + impl (T011-T019)
4. Complete US2 tests + impl (T020-T027)
5. Complete US3 tests + impl (T028-T037)
6. Complete Polish (T038-T044)

**Two Developers** (After Foundational):
- Dev A: US1 (T011-T019) → US3 (T028-T037)
- Dev B: US2 (T020-T027) → Polish validation (T040-T044)

**Three Developers** (After Foundational):
- Dev A: US1 tests & impl (T011-T019)
- Dev B: US2 tests & impl (T020-T027)
- Dev C: US3 tests & impl (T028-T037)
- Then all: Polish (T038-T044)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

Deploy functional request consumption and basic completion publishing:

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T010)
3. Complete Phase 3: User Story 1 (T011-T019)
4. **STOP and VALIDATE**: All US1 tests pass ✓
5. Deploy minimal MVP: RAG can consume from Kafka

### Incremental Delivery (All Stories)

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → Deploy (MVP)
3. Add US2 → Test independently → Deploy (Request-to-Completion)
4. Add US3 → Test independently → Deploy (Observability)
5. Each story adds value independently

### Quality Gates (Per Story)

Before moving to next story:
- [ ] All tests pass (contract + integration)
- [ ] All FRs for story are implemented
- [ ] Code meets quality checks (ruff, compileall)
- [ ] Story acceptance criteria met
- [ ] Logging/observability complete
- [ ] No regressions to prior stories

---

## Success Criteria Reference

Tasks complete when these criteria are satisfied:

- **SC-001**: 100% of valid events published to topic `rag` are consumed and acknowledged
- **SC-002**: ≥99% of valid consumed requests emit exactly one corresponding completion event
- **SC-003**: 100% of completion events include required fields (session_ctx, user_prompt, compiled_material, status, correlation)
- **SC-004**: 100% of malformed events are rejected with logged validation failures (non-fatal)
- **SC-005**: p95 consume-to-complete latency within agreed performance budget
- **SC-006**: 100% of request lifecycles have logs covering consume, process start/end, and publish with correlation

---

## Notes

- All file paths shown assume repository structure from plan.md
- [P] tasks = different files, no sequential dependencies
- [Story] label = task belongs to specific user story (US1/US2/US3)
- Tests marked REQUIRED must exist before implementation for story
- Each user story is independently completable and testable
- Consumer loop error continuation is critical (FR-011 compliance) - no crashes on single-request errors
- Logging must include correlation metadata (request_id) across all stages
- Commit after each phase or logical task group
- Stop at any checkpoint to validate story independently before proceeding
