# Implementation Plan: RAG Agent Deterministic Parallel Loop Simplification

**Branch**: `[001-build-rag-retrieval-agent]` | **Date**: 2026-06-14 | **Spec**: [spec.md](specs/001-rag-retrieval-agent/spec.md)
**Input**: Feature specification from `/specs/001-rag-retrieval-agent/spec.md`

## Summary

Simplify `rag_agent/agent.py` by removing LangGraph StateGraph orchestration and replacing it with a deterministic loop that dispatches per-page work in parallel with bounded concurrency. Build only minimal final state from successful page extracted content, ignore failed pages from extracted content aggregation, keep a simple failure list, and retain stage logging for dispatch/process/fail/reduce.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: kafka-python, PyMuPDF (fitz), pydantic v2, litellm
**Storage**: N/A (worker runtime, Kafka transport)
**Testing**: pytest, ruff check, ruff format --check, python -m compileall
**Target Platform**: Linux server worker process
**Project Type**: Backend worker service
**Performance Goals**:
- Maintain SC-003 completion emit reliability target (>=99% terminal attempts)
- Enforce bounded in-flight page tasks (SC-008)
- Preserve deterministic output ordering under parallel execution (SC-009)
**Constraints**:
- No LangGraph StateGraph dependency in `agent.py` page processing flow
- Keep validation and exception handling basic
- Preserve Kafka-agnostic `agent.py` boundaries
- Keep final state simple: extracted content from successful pages + simple failure list
**Scale/Scope**:
- Multi-file, multi-page request inputs
- Parallelism applied inside one request execution

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: PASS
  - Remove unnecessary orchestration abstraction and keep straightforward control flow.
  - Maintain explicit typing and small function boundaries.
- Testing Gate: PASS
  - Add/adjust tests for deterministic ordering, failed-page exclusion, and failure-list behavior.
- UX Consistency Gate: PASS (N/A direct UI)
  - Operator-facing behavior is logging; ensure stage logs remain clear and consistent.
- Performance Gate: PASS
  - Bounded parallelism and deterministic reduction explicitly validated.
- Maintainability Gate: PASS
  - Fewer orchestration layers; simple state model documented in artifacts.

## Project Structure

### Documentation (this feature)

```text
specs/001-rag-retrieval-agent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── rag-agent-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
project/
├── schemas.py
└── topics.py

rag_agent/
├── agent.py
├── kafka.py
├── worker.py
├── utils/
│   ├── helpers.py
│   ├── llm_client.py
│   ├── prompts.py
│   └── tools.py
└── tests/
    ├── test_rag_agent.py
    ├── test_worker_runtime.py
    ├── test_kafka_integration.py
    └── test_logging.py
```

**Structure Decision**: Keep worker-centric structure and implement simplified deterministic parallel loop directly in `rag_agent/agent.py` without LangGraph orchestration.

## Phase 0: Outline & Research

1. Confirm simple bounded parallel loop pattern for per-page tasks.
2. Confirm deterministic reduction strategy by pointer order.
3. Confirm minimal final state model (successful extracted content + failure list).
4. Capture decisions in `research.md`.

## Phase 1: Design & Contracts

1. Update `data-model.md` for simplified runtime state and failure list entity.
2. Update contract for non-StateGraph execution and failed-page exclusion semantics.
3. Update quickstart flow and logging stages.
4. Keep `.github/copilot-instructions.md` plan reference pointing to current plan file.

## Phase 2: Implementation Planning (Tasking Input)

Planned implementation slices:
1. Replace LangGraph page orchestration with deterministic bounded parallel loop.
2. Build minimal final state from successful pages only.
3. Add failure-list capture with page number + reason and stage logging.
4. Keep basic validation/exception handling only.
5. Run tests and quality gates.

## Post-Design Constitution Check

- Code Quality Gate: PASS
  - Simplification reduces abstraction and state complexity.
- Testing Gate: PASS
  - Design includes deterministic-order and failure-list verification.
- UX Consistency Gate: PASS
  - Logging stage expectations explicitly documented.
- Performance Gate: PASS
  - Bounded parallelism requirement retained.
- Maintainability Gate: PASS
  - Final state model is intentionally minimal.

## Complexity Tracking

No constitution violations requiring exception.

## Final Implementation Notes (2026-06-14)

- Replaced LangGraph orchestration in `rag_agent/agent.py` with deterministic bounded parallel dispatch using `ThreadPoolExecutor`.
- Preserved deterministic reduction by pointer order while allowing out-of-order worker completion.
- Excluded failed pages from final extracted content aggregation and retained-page compilation context.
- Added simple failed-page tracking via error summary entries in format `file:page:<n>: <reason>`.
- Added stage logs for `page_dispatched`, `page_processed`, `page_failed`, and `state_reduced` with request correlation.
- Kept validation and exception handling basic per scope constraints.

### Verification Evidence

- `pytest -q rag_agent/tests/test_rag_agent.py`
- `pytest -q rag_agent/tests/test_worker_runtime.py rag_agent/tests/test_kafka_integration.py`
- `ruff check project rag_agent`
- `ruff format --check project rag_agent`
- `python -m compileall project rag_agent`

### Residual Risks

- Failure details are currently surfaced via `errors` list entries rather than a dedicated structured output field in `RAGAgentOutput`.
- Retry/dead-letter behavior for publish and page-level failures remains intentionally out of scope.