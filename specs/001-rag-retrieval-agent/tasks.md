# Tasks: RAG Kafka Worker Simplification

**Input**: Design documents from `/specs/001-rag-retrieval-agent/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Included — Constitution II requires automated verification for all changed behaviours. Existing tests updated to reflect new module paths; StructuredLogger tests removed or replaced.

**Organization**: Three user stories (P1 worker runtime, P2 startup topic check, P3 handler simplification) with shared foundational restructuring.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Delete obsolete modules, create `utils/` directory, update imports and test infrastructure.

- [ ] T001 Delete `rag_agent/service.py` (was a compatibility shim; no callers)
- [ ] T002 Delete `rag_agent/logging.py` (StructuredLogger replaced by standard logging)
- [ ] T003 [P] Create `rag_agent/utils/__init__.py` (empty module marker for `utils/` package)
- [ ] T004 [P] Move `rag_agent/prompts.py` → `rag_agent/utils/prompts.py` (no content changes)
- [ ] T005 [P] Move `rag_agent/tools.py` → `rag_agent/utils/tools.py` (no content changes)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create `utils/helpers.py` with merged content from `helpers.py`, `llm_client.py`, and `config.py`; create simplified `utils/llm_client.py`; update all intra-package imports.

**⚠️ CRITICAL**: All US1–US3 tasks depend on the new `utils/` import paths being resolved first.

- [ ] T006 Create `rag_agent/utils/helpers.py` that consolidates:
  - Pure helper functions from `rag_agent/helpers.py` (`cosine_similarity`, `serialize_table_to_markdown`, `assemble_page_content`, `build_compilation_context`)
  - Config dataclasses and env-read functions from `rag_agent/config.py` (`LLMConfig`, `EmbeddingConfig`, `KafkaRuntimeConfig`, `get_text_llm_config()`, `get_vlm_config()`, `get_vlm_batch_size()`, `get_embedding_config()`, `get_kafka_config()`)
  - Module-level logger: `logger = logging.getLogger(__name__)`
  - Docstring noting consolidated responsibilities
- [ ] T007 Create `rag_agent/utils/llm_client.py` as simplified version of `rag_agent/llm_client.py`:
  - Retain only essential `call_llm(messages, config)` and `call_embedding(text, config)` function bodies
  - Remove credential-guard RuntimeError blocks — replace with `# TODO: Add credential validation guard`
  - Remove import-error guard blocks — replace with `# TODO: Handle missing litellm gracefully`
  - Remove response-format validation — replace with `# TODO: Validate response format`
  - Add `logger = logging.getLogger(__name__)`
- [ ] T008 Delete original `rag_agent/helpers.py` (content merged into `utils/helpers.py`)
- [ ] T009 Delete original `rag_agent/config.py` (content merged into `utils/helpers.py`)
- [ ] T010 Delete original `rag_agent/llm_client.py` (replaced by `utils/llm_client.py`)
- [ ] T011 Update `rag_agent/agent.py` imports: change all `from rag_agent.helpers`, `from rag_agent.config`, `from rag_agent.llm_client`, `from rag_agent.prompts`, `from rag_agent.tools` to `from rag_agent.utils.*`
- [ ] T012 [P] Update `rag_agent/worker.py` imports: change `from rag_agent.config` and any `from rag_agent.logging` to `from rag_agent.utils.helpers`; add `import logging; logger = logging.getLogger(__name__)`
- [ ] T013 [P] Update `rag_agent/handlers.py` imports: change `from rag_agent.config`, `from rag_agent.llm_client`, `from rag_agent.logging` to `from rag_agent.utils.*`; add `import logging; logger = logging.getLogger(__name__)`
- [ ] T014 [P] Update `rag_agent/kafka.py` imports: replace any `from rag_agent.config` with `from rag_agent.utils.helpers`; add `import logging; logger = logging.getLogger(__name__)`
- [ ] T015 Update `rag_agent/tests/` imports in all test files that reference `rag_agent.helpers`, `rag_agent.config`, `rag_agent.llm_client`, `rag_agent.logging`, or `rag_agent.service` to use new `rag_agent.utils.*` paths

**Checkpoint**: All imports resolve; `python -m compileall rag_agent` passes

---

## Phase 3: User Story 1 — Run RAG as a Kafka Worker Process (Priority: P1) 🎯 MVP

**Goal**: Worker process runs without HTTP runtime, uses standard logging, passes all existing worker lifecycle tests.

**Independent Test**: `pytest rag_agent/tests/test_worker_runtime.py -q` passes.

### Tests for User Story 1

- [ ] T016 [P] [US1] Update `rag_agent/tests/test_worker_runtime.py`: replace any `StructuredLogger` mock/import with standard `logging` assertions (use `caplog` pytest fixture)
- [ ] T017 [P] [US1] Update `rag_agent/tests/test_logging.py`: remove `StructuredLogger` class tests; add test confirming each module logger name matches `__name__` (e.g. `rag_agent.worker`, `rag_agent.agent`)

### Implementation for User Story 1

- [ ] T018 [US1] Update `rag_agent/worker.py`:
  - Remove all `StructuredLogger` import and usage
  - Replace lifecycle log calls with `logger.info(...)`, `logger.warning(...)`, `logger.error(...)`
  - Add `logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")` call in `main()` entry point (once)
  - Ensure `logger = logging.getLogger(__name__)` at module scope

**Checkpoint**: `pytest rag_agent/tests/test_worker_runtime.py -q` passes

---

## Phase 4: User Story 2 — Verify Topic Presence Without Topic Creation (Priority: P2)

**Goal**: Startup topic check runs via `rag_agent/kafka.py`, logs warnings for missing topics, no backend API calls.

**Independent Test**: `pytest rag_agent/tests/test_kafka_integration.py -q` passes.

### Tests for User Story 2

- [ ] T019 [P] [US2] Update `rag_agent/tests/test_kafka_integration.py`: fix any import paths changed by foundational phase; confirm topic-check tests still cover warn-and-continue and all-present scenarios

### Implementation for User Story 2

- [ ] T020 [US2] Update `rag_agent/kafka.py`:
  - Remove any `from rag_agent.logging import StructuredLogger` usage
  - Add `import logging; logger = logging.getLogger(__name__)` at module scope
  - Replace lifecycle log calls via `StructuredLogger` with `logger.info(...)` / `logger.warning(...)`

**Checkpoint**: `pytest rag_agent/tests/test_kafka_integration.py -q` passes

---

## Phase 5: User Story 3 — Minimal Typed Event Handler (Priority: P3)

**Goal**: `agent.py` and `handlers.py` have basic exception handling only; inner per-step guards replaced with `# TODO:`; no `StructuredLogger` dependency.

**Independent Test**: `pytest rag_agent/tests/test_request_event.py rag_agent/tests/test_completion_event.py -q` passes.

### Tests for User Story 3

- [ ] T021 [P] [US3] Update `rag_agent/tests/test_request_event.py`: fix import paths; confirm handler dispatch test still passes
- [ ] T022 [P] [US3] Update `rag_agent/tests/test_completion_event.py`: fix import paths; confirm completion event tests still pass

### Implementation for User Story 3

- [ ] T023 [US3] Simplify `rag_agent/handlers.py`:
  - Remove `StructuredLogger` import and all `self._logger.emit(...)` calls
  - Replace lifecycle log calls with `logger.info(...)` / `logger.error(...)`
  - Remove inner per-step try/except blocks in `__call__()` beyond the top-level guard
  - Add `# TODO: Add specific exception handling for <concern>` for each removed guard
  - Add `# TODO: Add richer schema and semantic validation` for `parse_event()` defer
  - Add `# TODO: Add metrics instrumentation` for metrics defer
  - Preserve top-level `except Exception` guard that logs and continues
- [ ] T024 [US3] Simplify `rag_agent/agent.py`:
  - Remove inner per-step try/except blocks beyond top-level orchestration guard
  - Add `# TODO: Add specific exception handling for page-extraction failures`
  - Add `# TODO: Add retry policy for LLM call failures`
  - Add `import logging; logger = logging.getLogger(__name__)` at module scope
  - Remove any `StructuredLogger` references

**Checkpoint**: `pytest rag_agent/tests/test_request_event.py rag_agent/tests/test_completion_event.py -q` passes

---

## Phase 6: Integration & Regression

**Purpose**: Confirm full test suite passes on new module layout; no stale imports remain.

- [ ] T025 Run `python -m compileall rag_agent` — must produce zero errors
- [ ] T026 Run `pytest rag_agent/tests/ -q` — all tests must pass
- [ ] T027 [P] Run `ruff check rag_agent` — must produce zero errors
- [ ] T028 [P] Run `ruff format --check rag_agent` — apply format if needed, then re-check
- [ ] T029 [US1] [US2] [US3] Confirm `rag_agent/utils/` directory exists with `__init__.py`, `helpers.py`, `llm_client.py`, `prompts.py`, `tools.py` and that `service.py` and `logging.py` are absent from `rag_agent/`
- [ ] T030 Record quality-gate evidence in `specs/001-rag-retrieval-agent/quickstart.md` (ruff, compileall, pytest outputs)

**Checkpoint**: All 6 phases complete — feature is production-ready

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup — Delete & Create)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 (utils/ package must exist)
- **Phase 3–5 (US1–US3)**: All depend on Phase 2 checkpoint (imports must resolve)
  - US1, US2, US3 can proceed in parallel after Phase 2 completes
- **Phase 6 (Integration)**: Depends on Phases 3–5 completion

### Within Phase 2

1. T006–T007: Create new `utils/` module files (can be parallel)
2. T008–T010: Delete old root-level files (after T006–T007 are complete)
3. T011–T014: Update imports in consuming modules (can be parallel after deletes)
4. T015: Update all test file imports (after T011–T014 to avoid confusion)

### Parallel Opportunities

- **Phase 1**: T003, T004, T005 can run in parallel with each other
- **Phase 2**: T006 and T007 can run in parallel; T011–T014 can run in parallel after T008–T010
- **Phase 3–5**: US1 (T016–T018), US2 (T019–T020), US3 (T021–T024) can all start in parallel after Phase 2
- **Phase 6**: T027, T028, T029 can run in parallel

---

## Parallel Example: Phase 3–5 after Foundational Gate

```
# Launch simultaneously after Phase 2 checkpoint passes:
Task: "Update test_worker_runtime.py to use caplog (T016)"
Task: "Update test_logging.py, remove StructuredLogger tests (T017)"
Task: "Update worker.py logging (T018)"

Task: "Update test_kafka_integration.py import paths (T019)"
Task: "Update kafka.py logging (T020)"

Task: "Update test_request_event.py (T021)"
Task: "Update test_completion_event.py (T022)"
Task: "Simplify handlers.py (T023)"
Task: "Simplify agent.py (T024)"
```

---

## Implementation Strategy

### MVP (Phases 1–3 only)

1. Phase 1: Delete service.py and logging.py; create utils/
2. Phase 2: Create helpers.py + llm_client.py in utils/; update all imports
3. Phase 3: Update worker.py to use standard logging; fix worker tests
4. **STOP and VALIDATE**: `pytest rag_agent/tests/test_worker_runtime.py` passes
5. Proceed to US2 + US3 in parallel

### Full Delivery (All Phases)

1. Phases 1–2 (foundational restructuring)
2. Phases 3–5 in parallel (US1 + US2 + US3 simplification)
3. Phase 6 (integration, quality gates, evidence capture)

---

## Notes

- [P] tasks = different files, no blocking dependency on incomplete tasks
- [USx] label maps task to specific user story for traceability
- Test-driven where behaviour changes: fix tests to reflect new paths before or alongside implementation
- Avoid: editing test files before import paths in source files are correct (will cause confusing failures)
- Every removed exception guard must have a corresponding `# TODO:` comment — no silent deletions
- `rag_agent/utils/helpers.py` is the only file that consolidates multiple responsibilities; all others move unchanged
- Stop at Phase 2 checkpoint to validate import resolution before touching any test files
