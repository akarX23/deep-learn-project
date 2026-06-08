# Tasks: RAG Retrieval Agent (v2 Clarification Update)

**Input**: Design documents from `/specs/001-rag-retrieval-agent/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are required for this feature and are included per user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`US1`, `US2`, `US3`) for story-phase tasks only
- All tasks include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align shared environment and dependency layout with clarified architecture.

- [ ] T001 Add sectioned shared/agent dependency blocks in requirements.txt
- [ ] T002 Create project-level shared plus per-agent sections in .env.local
- [ ] T003 [P] Document .env.local section usage and VLM batch variable in rag_agent/README.md
- [ ] T004 [P] Update sample env variable guidance for batch processing in specs/001-rag-retrieval-agent/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contract and infrastructure updates that all stories depend on.

**⚠️ CRITICAL**: No user story implementation starts before this phase completes.

- [ ] T005 Remove retained_content from ExtractedPage and update output schema constraints in project/schemas.py
- [ ] T006 Add VLM batch-size config loader and defaults in rag_agent/config.py
- [ ] T007 [P] Add batch-aware image instruction template updates in rag_agent/prompts.py
- [ ] T008 [P] Refactor image-description tools to support multi-image batch calls in rag_agent/tools.py
- [ ] T009 Add fitz document lifecycle helpers for open/close per request in rag_agent/agent.py
- [ ] T010 Reorder imports into stdlib/third-party/project-local groups across project/schemas.py and rag_agent/*.py

**Checkpoint**: Shared schema, config, prompts, and core runtime scaffolding are ready for story implementation.

---

## Phase 3: User Story 1 - Extract Relevant PDF Content (Priority: P1) 🎯 MVP

**Goal**: Process PDFs page-by-page with one-time fitz document loading and per-page batched image understanding.

**Independent Test**: Run a valid sample PDF and verify all pages produce audit entries while fitz documents are opened once per file and image descriptions are generated via page-scoped batches.

### Tests for User Story 1 (REQUIRED)

- [ ] T011 [P] [US1] Add test for one-time fitz open per file during run in rag_agent/tests/test_rag_agent.py
- [ ] T012 [P] [US1] Add test for per-page VLM batch chunking using RAG_VLM_BATCH_SIZE in rag_agent/tests/test_rag_agent.py
- [ ] T013 [P] [US1] Add test for batched image prompt context propagation in rag_agent/tests/test_rag_agent.py
- [ ] T014 [US1] Update extraction and relevance tests for refactored tool signatures in rag_agent/tests/test_rag_agent.py

### Implementation for User Story 1

- [ ] T015 [US1] Refactor page extraction functions to consume opened fitz documents/pages in rag_agent/tools.py
- [ ] T016 [US1] Implement per-page image batching and response aggregation in rag_agent/tools.py
- [ ] T017 [US1] Integrate opened-document lookup into page pointers and graph state transitions in rag_agent/agent.py
- [ ] T018 [US1] Update _process_next_page to use shared document handles and batched image descriptions in rag_agent/agent.py
- [ ] T019 [US1] Preserve page-level audit outcomes for SUCCESS/SKIPPED_IRRELEVANT/FAILED_EXTRACTION with new extraction flow in rag_agent/agent.py

**Checkpoint**: US1 delivers correct extraction, relevance filtering, and page-level auditing with clarified fitz and batching behavior.

---

## Phase 4: User Story 2 - Compile Study Material for Teaching (Priority: P2)

**Goal**: Compile coherent Markdown from internal retained content while keeping output payload slim.

**Independent Test**: Execute full flow and verify compiled_material remains non-empty and coherent, while extracted_pages contains audit metadata only.

### Tests for User Story 2 (REQUIRED)

- [ ] T020 [P] [US2] Add test that compiled_material is the only assembled text output in rag_agent/tests/test_rag_agent.py
- [ ] T021 [US2] Add test that extracted_pages omits retained_content in rag_agent/tests/test_rag_agent.py

### Implementation for User Story 2

- [ ] T022 [US2] Maintain internal retained page text structures separate from ExtractedPage output records in rag_agent/agent.py
- [ ] T023 [US2] Update compilation context assembly to read internal retained content only in rag_agent/agent.py
- [ ] T024 [US2] Ensure Markdown compilation fallback remains deterministic with batched-image context in rag_agent/agent.py

**Checkpoint**: US2 produces planner-ready compiled material and no longer emits per-page retained text.

---

## Phase 5: User Story 3 - Return Contract-Safe Status and Audit (Priority: P3)

**Goal**: Keep planner-safe status, counters, and error semantics while enforcing the clarified output contract.

**Independent Test**: Run mixed valid/invalid file input and verify status/error behavior remains correct with schema-valid extracted_pages metadata-only records.

### Tests for User Story 3 (REQUIRED)

- [ ] T025 [P] [US3] Add contract test for metadata-only extracted_pages shape in rag_agent/tests/test_rag_agent.py
- [ ] T026 [P] [US3] Add regression test for partial status with mixed path validity under new internals in rag_agent/tests/test_rag_agent.py
- [ ] T027 [US3] Add regression test for relevance-threshold skip behavior under batched image path in rag_agent/tests/test_rag_agent.py

### Implementation for User Story 3

- [ ] T028 [US3] Update output assembly to mirror request metadata and counters with revised ExtractedPage model in rag_agent/agent.py
- [ ] T029 [US3] Reconcile status derivation and error aggregation with fitz lifecycle failure modes in rag_agent/agent.py
- [ ] T030 [US3] Update planner interface contract docs for metadata-only extracted_pages in specs/001-rag-retrieval-agent/contracts/rag-agent-contract.md

**Checkpoint**: US3 returns stable, schema-valid status/audit output aligned with clarified contract requirements.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, performance, and documentation alignment across all user stories.

- [ ] T031 [P] Refresh data model documentation for internal retained content and public output contract in specs/001-rag-retrieval-agent/data-model.md
- [ ] T032 [P] Refresh research decisions for implemented v2 tradeoffs in specs/001-rag-retrieval-agent/research.md
- [ ] T033 Run full regression test suite and capture updated baseline metrics in rag_agent/tests/test_rag_agent.py
- [ ] T034 Validate quickstart run and update observed results in specs/001-rag-retrieval-agent/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2; establishes MVP extraction path.
- **Phase 4 (US2)**: Depends on US1 extraction outputs.
- **Phase 5 (US3)**: Depends on US1/US2 runtime and output assembly.
- **Phase 6 (Polish)**: Depends on completion of desired user stories.

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational completion.
- **US2 (P2)**: Depends on US1 retained-content internals and compilation inputs.
- **US3 (P3)**: Depends on US1 extraction audit and US2 final output behavior.

### Dependency Graph

- Setup -> Foundational -> US1 -> US2 -> US3 -> Polish

---

## Parallel Opportunities

- **Setup**: T003 and T004 can run in parallel after T001/T002.
- **Foundational**: T007 and T008 can run in parallel after T005/T006.
- **US1 Tests**: T011, T012, and T013 can run in parallel.
- **US3 Tests**: T025 and T026 can run in parallel.
- **Polish**: T031 and T032 can run in parallel.

### Parallel Example: User Story 1

```bash
Task: "T011 [US1] Add test for one-time fitz open per file during run in rag_agent/tests/test_rag_agent.py"
Task: "T012 [US1] Add test for per-page VLM batch chunking using RAG_VLM_BATCH_SIZE in rag_agent/tests/test_rag_agent.py"
Task: "T013 [US1] Add test for batched image prompt context propagation in rag_agent/tests/test_rag_agent.py"
```

### Parallel Example: User Story 2

```bash
Task: "T020 [US2] Add test that compiled_material is the only assembled text output in rag_agent/tests/test_rag_agent.py"
Task: "T022 [US2] Maintain internal retained page text structures separate from ExtractedPage output records in rag_agent/agent.py"
```

### Parallel Example: User Story 3

```bash
Task: "T025 [US3] Add contract test for metadata-only extracted_pages shape in rag_agent/tests/test_rag_agent.py"
Task: "T026 [US3] Add regression test for partial status with mixed path validity under new internals in rag_agent/tests/test_rag_agent.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational phases.
2. Deliver US1 fitz lifecycle reuse and per-page VLM batching.
3. Validate US1 independently with focused extraction and batching tests.

### Incremental Delivery

1. Add US2 internal-retained-content compilation and slim output contract behavior.
2. Add US3 status/error contract hardening.
3. Complete polish tasks and performance baseline validation.

### Parallel Team Strategy

1. Engineer A: tools.py extraction and batching tasks.
2. Engineer B: schemas/config/prompts and contract documentation tasks.
3. Engineer C: agent graph lifecycle integration and regression tests.

---

## Notes

- All tasks follow the required checklist format with task ID and explicit file path.
- [P] tasks are limited to no-dependency or disjoint-file work.
- Planner Agent and Teaching Agent implementation remain out of scope for this task list.
