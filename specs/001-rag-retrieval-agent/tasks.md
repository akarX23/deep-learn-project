# Tasks: RAG Retrieval Agent

**Input**: Design documents from /specs/001-rag-retrieval-agent/
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because spec.md explicitly requires automated coverage for extraction, relevance scoring, schema-valid output, partial-failure handling, and strict threshold behavior.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align runtime config surfaces and docs scaffolding for provider-routed LiteLLM usage.

- [X] T001 Add modality-specific provider defaults (hosted_vllm) and grouped section comments in .env.local.example
- [X] T002 Align dependency sections for shared and agent-specific packages in requirements.txt
- [X] T003 [P] Add provider-routing overview and env table in rag_agent/README.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement cross-story foundations required before any user story work.

**CRITICAL**: No user story implementation starts until this phase is complete.

- [X] T004 Introduce provider fields and routed model composition helpers in rag_agent/config.py
- [X] T005 [P] Extend LiteLLM call wrapper to accept provider-aware routed model config in rag_agent/llm_client.py
- [X] T006 [P] Add shared runtime config validation for missing model/provider combinations in rag_agent/config.py
- [X] T007 Update RAGAgent initialization to load text, VLM, and embedding configs once per request in rag_agent/agent.py
- [X] T008 [P] Add regression unit tests for provider defaulting and routed model composition in rag_agent/tests/test_rag_agent.py

**Checkpoint**: Provider-aware config and call path are stable for story implementation.

---

## Phase 3: User Story 1 - Extract Relevant PDF Content (Priority: P1)

**Goal**: Process PDFs page by page, extract content, and retain only relevant pages with robust audit records.

**Independent Test**: Run the agent on sample PDF input and verify page-level statuses, relevance scores, and skip/failure behavior.

### Tests for User Story 1

- [X] T009 [P] [US1] Add test for one-time fitz.Document reuse across page processing in rag_agent/tests/test_rag_agent.py
- [X] T010 [P] [US1] Add test for SKIPPED_IRRELEVANT decisions at configurable threshold in rag_agent/tests/test_rag_agent.py
- [X] T011 [US1] Add test for FAILED_EXTRACTION non-fatal continuation on bad pages in rag_agent/tests/test_rag_agent.py

### Implementation for User Story 1

- [X] T012 [US1] Implement request-scoped fitz.Document cache lifecycle outside graph state in rag_agent/agent.py
- [X] T013 [P] [US1] Enforce explicit fitz.Document typing for open handle map in rag_agent/agent.py
- [X] T014 [US1] Refactor page extraction flow to use cached handles and preserve page audit metadata in rag_agent/agent.py
- [X] T015 [P] [US1] Update extraction helpers to support handle-reuse based reads without reopen loops in rag_agent/tools.py
- [X] T016 [US1] Wire relevance scoring path to embedding config and threshold skip semantics in rag_agent/agent.py

**Checkpoint**: US1 is independently functional and testable.

---

## Phase 4: User Story 2 - Compile Study Material for Teaching (Priority: P2)

**Goal**: Compile retained page content into one coherent Markdown study artifact preserving table/image-derived details.

**Independent Test**: Run full pipeline with retained pages and verify a non-empty, organized Markdown output.

### Tests for User Story 2

- [X] T017 [P] [US2] Add test for single final compilation call after page loop completion in rag_agent/tests/test_rag_agent.py
- [X] T018 [P] [US2] Add test ensuring compiled markdown retains table and image-derived content in rag_agent/tests/test_rag_agent.py

### Implementation for User Story 2

- [X] T019 [US2] Implement per-page image batching via VLM_BATCH_SIZE preserving page-local order in rag_agent/tools.py
- [X] T020 [P] [US2] Update image prompt composition to combine general directive with user_prompt context in rag_agent/prompts.py
- [X] T021 [US2] Integrate batched image descriptions into page content assembly pipeline in rag_agent/helpers.py
- [X] T022 [US2] Ensure final compilation consumes retained internal content only once in rag_agent/agent.py

**Checkpoint**: US2 is independently functional and testable.

---

## Phase 5: User Story 3 - Return Contract-Safe Status and Audit (Priority: P3)

**Goal**: Guarantee schema-valid outputs with mirrored metadata, explicit statuses, and non-fatal error reporting.

**Independent Test**: Run mixed-validity inputs and verify partial/failed semantics with contract-safe output shape.

### Tests for User Story 3

- [X] T023 [P] [US3] Add schema contract test for mirrored metadata and extracted_pages audit-only payload in rag_agent/tests/test_rag_agent.py
- [X] T024 [P] [US3] Add mixed-validity integration test asserting partial status and populated errors in rag_agent/tests/test_rag_agent.py
- [X] T025 [US3] Add strict threshold integration test asserting zero included pages at threshold 1.0 in rag_agent/tests/test_rag_agent.py

### Implementation for User Story 3

- [X] T026 [US3] Remove retained_content from response serialization path and keep compiled_material as sole assembled text artifact in project/schemas.py
- [X] T027 [US3] Normalize complete/partial/failed derivation logic for edge cases and no-usable-content failures in rag_agent/agent.py
- [X] T028 [US3] Ensure request_id, user_prompt, and schema_version are mirrored in final output construction in rag_agent/agent.py
- [X] T029 [P] [US3] Align planner-facing contract narrative with output semantics and provider routing notes in specs/001-rag-retrieval-agent/contracts/rag-agent-contract.md

**Checkpoint**: US3 is independently functional and testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate full feature quality, documentation consistency, and performance expectations.

- [X] T030 [P] Update quickstart execution and env examples for provider-separated defaults in specs/001-rag-retrieval-agent/quickstart.md
- [X] T031 [P] Update research notes with final implementation outcomes and tradeoffs in specs/001-rag-retrieval-agent/research.md
- [X] T032 Enforce import grouping (stdlib, third-party, local) in rag_agent/agent.py, rag_agent/config.py, rag_agent/tools.py, and rag_agent/llm_client.py
- [X] T033 Run full regression suite and capture evidence for FR-016 coverage in rag_agent/tests/test_rag_agent.py
- [X] T034 Validate representative 5-10 page runtime behavior and note baseline results in specs/001-rag-retrieval-agent/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1: No dependencies, starts immediately.
- Phase 2: Depends on Phase 1, blocks all user stories.
- Phase 3 (US1): Depends on Phase 2 completion.
- Phase 4 (US2): Depends on Phase 2 completion; can run after US1 or in parallel once foundational work is stable.
- Phase 5 (US3): Depends on Phase 2 completion; can run after US1 or in parallel once foundational work is stable.
- Phase 6: Depends on completion of all targeted user stories.

### User Story Dependencies

- US1 (P1): No dependency on other stories after foundational phase.
- US2 (P2): Uses retained-content pipeline from US1 extraction but remains independently testable.
- US3 (P3): Depends on output production paths from US1/US2 but remains independently testable with contract-focused assertions.

### Within Each User Story

- Write and run story tests before or alongside implementation tasks.
- Implement core data/control-path changes before integration polish.
- Confirm story-specific independent test criteria before moving on.

---

## Parallel Opportunities

- Setup: T003 can run in parallel with T001-T002.
- Foundational: T005, T006, and T008 can run in parallel after T004 starts.
- US1: T009 and T010 can run in parallel; T013 and T015 can run in parallel.
- US2: T017 and T018 can run in parallel; T020 can run in parallel with T019.
- US3: T023 and T024 can run in parallel; T029 can run in parallel with T026-T028.
- Polish: T030 and T031 can run in parallel.

## Parallel Example: User Story 1

- Run T009 and T010 together while preparing extraction flow updates.
- Run T013 and T015 together after T012 establishes cache lifecycle.

## Parallel Example: User Story 3

- Run T023 and T024 together as contract/integration checks.
- Run T029 while T026-T028 finalize output semantics.

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1).
3. Validate US1 independent test criteria and extraction audit behavior.
4. Demo/deploy MVP extraction flow.

### Incremental Delivery

1. Foundation first: Phase 1 and 2.
2. Add US1, validate independently.
3. Add US2, validate independently.
4. Add US3, validate independently.
5. Finish with cross-cutting polish and performance validation.

### Parallel Team Strategy

1. One engineer leads foundational config and llm_client updates.
2. One engineer drives US1 extraction pipeline and handle lifecycle.
3. One engineer drives US2/US3 tests and contract alignment after foundational readiness.
