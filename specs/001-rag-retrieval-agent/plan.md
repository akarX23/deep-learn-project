# Implementation Plan: RAG Kafka Worker Boilerplate Reduction

**Branch**: `001-build-rag-retrieval-agent` | **Date**: 2026-06-14 | **Spec**: `specs/001-rag-retrieval-agent/spec.md`
**Input**: Feature specification from `/specs/001-rag-retrieval-agent/spec.md`

## Summary

Refactor the RAG worker runtime to keep the same poll -> process -> publish functional flow while reducing boilerplate and indirection. The key changes are: remove Kafka Protocol stubs in favor of concrete kafka-python types, remove constructor-level dependency injection in `RAGWorker`, remove trivial Kafka wrapper functions, simplify `tools.py` to operate only on open `fitz.Document` handles, and inline poll/dispatch logic directly inside `_poll_loop`. Keep only basic exception handling and retain TODO markers for deferred hardening.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: kafka-python, pydantic v2, PyMuPDF (`fitz`), LiteLLM, python-dotenv  
**Storage**: N/A (Kafka topics are external transport; PDF files are local inputs)  
**Testing**: pytest (`rag_agent/tests/`), ruff, compileall  
**Target Platform**: Linux worker runtime (local docker-compose Kafka and CI Linux)  
**Project Type**: Backend worker service (threaded Kafka consumer loop)  
**Performance Goals**: startup topic check warning/readiness always logged; worker keeps polling without idle exit; p95 poll-to-completion within existing budget for this integration  
**Constraints**: no FastAPI runtime ownership in RAG worker, no startup topic creation, direct consumer-to-agent dispatch, basic exception handling only, reduced abstraction surface, explicit type annotations at module boundaries  
**Scale/Scope**: single RAG worker consuming `rag` and publishing `rag-complete`; code-reduction scope limited to `rag_agent/kafka.py`, `rag_agent/worker.py`, and `rag_agent/utils/tools.py`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: Pass `ruff check project rag_agent` and `ruff format --check project rag_agent`; reject changes that add new abstraction-only wrappers or dead code paths.
- Testing Gate: Maintain/update tests for worker lifecycle, consume/process/publish path, startup topic checks, and contract payload behavior in `rag_agent/tests/`; run `pytest rag_agent/tests -q`.
- UX Consistency Gate: N/A for direct end-user UI; for operator-facing behavior, logs must stay consistent (`startup_topic_check`, `consumed`, `processing_started`, `processing_completed`, `publish_completed`, `error`).
- Performance Gate: Startup topic check must not block worker start when topics are missing; poll loop remains non-terminating on single-event failures.
- Maintainability Gate: Remove unnecessary indirection (Protocol stubs, trivial wrappers, injected factories, batch dispatch helper), keep TODO markers for deferred hardening, and preserve clear module ownership.

Post-Design Re-check (Phase 1): PASS
- No unresolved clarifications remain.
- Design artifacts align with FR-001 to FR-023 and SC-001 to SC-007.
- Simplification decisions reduce code surface without changing core event flow.

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
└── schemas.py

rag_agent/
├── agent.py
├── kafka.py
├── worker.py
└── utils/
    ├── content_helpers.py
    ├── helpers.py
    ├── llm_client.py
    ├── prompts.py
    └── tools.py

rag_agent/tests/
├── test_request_event.py
├── test_completion_event.py
├── test_worker_runtime.py
├── test_kafka_integration.py
├── test_rag_agent.py
└── test_logging.py
```

**Structure Decision**: Keep the existing worker-centric layout and apply simplification in-place. Preserve `kafka.py` as transport boundary, `worker.py` as lifecycle orchestrator, `agent.py` as Kafka-agnostic processor, and `tools.py` as extraction/relevance utilities with reduced abstraction.

## Phase 0: Research Output

- Updated `research.md` with decisions for concrete Kafka type annotations, constructor simplification, wrapper cleanup strategy, document-only extraction APIs, and inlined poll/dispatch loop.

## Phase 1: Design Output

- Updated `data-model.md` to reflect removal of Protocol and callback-typed entities and to encode simplified ownership boundaries.
- Updated `contracts/rag-agent-contract.md` to formalize retained vs removed functions and module boundaries.
- Updated `quickstart.md` to document the streamlined runtime flow and implementation guardrails.
- Updated agent context reference in `CLAUDE.md` to point to this plan.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
