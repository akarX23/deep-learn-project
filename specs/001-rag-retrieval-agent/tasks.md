# Tasks: RAG Retrieval Agent

**Input**: Design documents from `/specs/001-rag-retrieval-agent/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are required for this feature and are included in each user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`US1`, `US2`, `US3`) for story-phase tasks only
- All tasks include exact file paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package structure and baseline tooling for the RAG agent module.

- [ ] T001 Create package directories and init files in project/__init__.py and rag_agent/__init__.py
- [ ] T002 Create test directory structure in rag_agent/tests/__init__.py and rag_agent/tests/inputs/.gitkeep
- [ ] T003 [P] Add Python dependency manifest for pydantic, pymupdf, sentence-transformers, litellm, langgraph, and pytest in requirements.txt
- [ ] T004 [P] Add pytest configuration for rag_agent tests in pytest.ini

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts and core abstractions required by all user stories.

**⚠️ CRITICAL**: No user story implementation starts before this phase completes.

- [ ] T005 Implement PageExtractionStatus enum and shared schemas in project/schemas.py
- [ ] T006 Implement LLMConfig dataclass and environment-variable loaders in rag_agent/config.py
- [ ] T007 Implement unified LiteLLM call wrapper call_llm(messages, config) in rag_agent/llm_client.py
- [ ] T008 [P] Define IMAGE_DESCRIPTION_PROMPT and MATERIAL_COMPILATION_PROMPT constants in rag_agent/prompts.py
- [ ] T009 [P] Implement helper utilities serialize_table_to_markdown, assemble_page_content, and build_compilation_context in rag_agent/helpers.py
- [ ] T010 Wire rag_agent module exports for agent and tool entry points in rag_agent/__init__.py

**Checkpoint**: Shared schemas, config, llm abstraction, and helper utilities are ready for story work.

---

## Phase 3: User Story 1 - Extract Relevant PDF Content (Priority: P1) 🎯 MVP

**Goal**: Process PDFs page-by-page, extract multimodal content, score relevance, and audit page outcomes.

**Independent Test**: Run agent input with sample PDF and confirm every page has an ExtractedPage record with SUCCESS, SKIPPED_IRRELEVANT, or FAILED_EXTRACTION.

### Tests for User Story 1 (REQUIRED)

- [ ] T011 [P] [US1] Add fixture loader for sample input and sample PDF paths in rag_agent/tests/test_rag_agent.py
- [ ] T012 [P] [US1] Implement test_get_page_count in rag_agent/tests/test_rag_agent.py
- [ ] T013 [P] [US1] Implement test_extract_text_from_page in rag_agent/tests/test_rag_agent.py
- [ ] T014 [P] [US1] Implement test_extract_tables_from_page in rag_agent/tests/test_rag_agent.py
- [ ] T015 [P] [US1] Implement test_extract_images_from_page in rag_agent/tests/test_rag_agent.py
- [ ] T016 [US1] Implement test_serialize_table_to_markdown in rag_agent/tests/test_rag_agent.py
- [ ] T017 [P] [US1] Implement test_score_page_relevance_high in rag_agent/tests/test_rag_agent.py
- [ ] T018 [P] [US1] Implement test_score_page_relevance_low in rag_agent/tests/test_rag_agent.py

### Implementation for User Story 1

- [ ] T019 [US1] Implement get_page_count and extract_text_from_page in rag_agent/tools.py
- [ ] T020 [P] [US1] Implement extract_tables_from_page using PyMuPDF table extraction in rag_agent/tools.py
- [ ] T021 [P] [US1] Implement extract_images_from_page using PyMuPDF image extraction in rag_agent/tools.py
- [ ] T022 [US1] Implement score_page_relevance with sentence-transformers cosine similarity in rag_agent/tools.py
- [ ] T023 [US1] Implement describe_image_with_vlm via llm_client.call_llm in rag_agent/tools.py
- [ ] T024 [US1] Implement LangGraph page-processing state model and tool-node orchestration in rag_agent/agent.py
- [ ] T025 [US1] Integrate per-page extraction, relevance threshold filtering, and ExtractedPage auditing in rag_agent/agent.py
- [ ] T026 [US1] Add sample PDF fixture with text/table/image coverage in rag_agent/tests/inputs/sample.pdf
- [ ] T027 [US1] Add valid serialized request fixture in rag_agent/tests/inputs/sample_input.json

**Checkpoint**: Page extraction, relevance filtering, and per-page audit flow are working independently.

---

## Phase 4: User Story 2 - Compile Study Material for Teaching (Priority: P2)

**Goal**: Produce one coherent Markdown document from retained page content.

**Independent Test**: Run full flow and verify non-empty compiled_material with organized headings and preserved table/image-derived content.

### Tests for User Story 2 (REQUIRED)

- [ ] T028 [US2] Implement test_rag_agent_output_schema for full-run validation in rag_agent/tests/test_rag_agent.py

### Implementation for User Story 2

- [ ] T029 [US2] Build retained-page compilation context assembly in rag_agent/agent.py
- [ ] T030 [US2] Implement final single-shot material compilation LLM call using MATERIAL_COMPILATION_PROMPT in rag_agent/agent.py
- [ ] T031 [US2] Ensure Markdown output consistency and fallback behavior when retained context is minimal in rag_agent/agent.py

**Checkpoint**: Final compiled Markdown output is generated from retained content and schema output remains valid.

---

## Phase 5: User Story 3 - Return Contract-Safe Status and Audit (Priority: P3)

**Goal**: Guarantee planner-safe output metadata, status signaling, and partial-failure behavior.

**Independent Test**: Provide one valid and one missing path and verify partial status with non-empty errors while retaining usable output from valid file.

### Tests for User Story 3 (REQUIRED)

- [ ] T032 [US3] Implement test_rag_agent_partial_failure in rag_agent/tests/test_rag_agent.py
- [ ] T033 [US3] Implement test_relevance_threshold_filtering in rag_agent/tests/test_rag_agent.py

### Implementation for User Story 3

- [ ] T034 [US3] Implement request-level error aggregation and non-fatal file/page failure handling in rag_agent/agent.py
- [ ] T035 [US3] Implement deterministic status derivation logic (complete|partial|failed) in rag_agent/agent.py
- [ ] T036 [US3] Ensure mirrored request metadata and aggregate counters in RAGAgentOutput creation in rag_agent/agent.py
- [ ] T037 [US3] Add synchronous CLI entrypoint for local standalone invocation in rag_agent/agent.py

**Checkpoint**: Contract-safe status semantics and partial-failure handling are complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality pass across all user stories.

- [ ] T038 [P] Document environment variables and execution workflow in rag_agent/README.md
- [ ] T039 Validate quickstart commands and expected outputs in specs/001-rag-retrieval-agent/quickstart.md
- [ ] T040 [P] Add regression test notes and fixture assumptions in rag_agent/tests/inputs/README.md
- [ ] T041 Run full test suite and capture baseline runtime metrics for sample input in rag_agent/tests/test_rag_agent.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2; establishes MVP extraction path.
- **Phase 4 (US2)**: Depends on US1 retained-content pipeline.
- **Phase 5 (US3)**: Depends on US1/US2 output assembly and status surfaces.
- **Phase 6 (Polish)**: Depends on completion of desired user stories.

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational completion.
- **US2 (P2)**: Depends on US1 retained page outputs.
- **US3 (P3)**: Depends on US1 extraction audit and US2 compiled output semantics.

### Within Each User Story

- Write tests first and confirm failing expectations before implementation.
- Implement tools/helpers before integrating agent loop behaviors.
- Finalize schema/status assembly only after extraction/compilation flows are in place.

### Dependency Graph

- Setup -> Foundational -> US1 -> US2 -> US3 -> Polish

---

## Parallel Opportunities

- **Setup**: T003 and T004 can run in parallel after T001/T002.
- **Foundational**: T008 and T009 can run in parallel after T005-T007 begin.
- **US1 Tests**: T012-T015 and T017-T018 can run in parallel.
- **US1 Implementation**: T020 and T021 can run in parallel once T019 is defined.
- **Polish**: T038 and T040 can run in parallel.

### Parallel Example: User Story 1

```bash
# Parallel test creation
Task: "T012 [US1] Implement test_get_page_count in rag_agent/tests/test_rag_agent.py"
Task: "T013 [US1] Implement test_extract_text_from_page in rag_agent/tests/test_rag_agent.py"
Task: "T014 [US1] Implement test_extract_tables_from_page in rag_agent/tests/test_rag_agent.py"
Task: "T015 [US1] Implement test_extract_images_from_page in rag_agent/tests/test_rag_agent.py"

# Parallel extraction tool implementation
Task: "T020 [US1] Implement extract_tables_from_page using PyMuPDF table extraction in rag_agent/tools.py"
Task: "T021 [US1] Implement extract_images_from_page using PyMuPDF image extraction in rag_agent/tools.py"
```

### Parallel Example: User Story 2

```bash
Task: "T029 [US2] Build retained-page compilation context assembly in rag_agent/agent.py"
Task: "T028 [US2] Implement test_rag_agent_output_schema for full-run validation in rag_agent/tests/test_rag_agent.py"
```

### Parallel Example: User Story 3

```bash
Task: "T032 [US3] Implement test_rag_agent_partial_failure in rag_agent/tests/test_rag_agent.py"
Task: "T033 [US3] Implement test_relevance_threshold_filtering in rag_agent/tests/test_rag_agent.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational phases.
2. Deliver US1 extraction tools, scoring, and page-audit loop.
3. Validate US1 independently with sample fixture and extraction tests.

### Incremental Delivery

1. Add US2 compilation to produce planner-ready Markdown output.
2. Add US3 contract-safe status/error semantics for integration reliability.
3. Complete polish tasks and performance baseline recording.

### Team Parallelization Strategy

1. Engineer A: tools.py extraction and scoring tasks.
2. Engineer B: schemas/config/llm client and prompt tasks.
3. Engineer C: agent loop integration and end-to-end tests.

---

## Notes

- All tasks follow the required checklist format with task ID and explicit file path.
- [P] tasks are limited to no-dependency or disjoint-file work.
- Planner Agent and Teaching Agent implementation remain out of scope for this task list.
