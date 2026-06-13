# Implementation Plan: RAG Kafka Worker Simplification

**Branch**: `001-build-rag-retrieval-agent` | **Date**: 2026-06-13 | **Spec**: `specs/001-rag-retrieval-agent/spec.md`
**Input**: Feature specification from `/specs/001-rag-retrieval-agent/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Simplify the RAG runtime to a direct worker-driven Kafka flow: `worker.py` initializes Kafka and starts the threaded consumer loop, verifies required topics exist (warn-and-continue if missing), consumes request events, calls `agent.py` directly, and publishes completion events through `kafka.py`. Remove handler and factory abstractions from active flow. Keep `agent.py` Kafka-agnostic and keep `helpers.py` limited to environment-value extraction functions. Advanced validation, edge-case hardening, and deeper exception taxonomy are deferred as TODO tasks.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: kafka-python, pydantic v2, litellm, sentence-transformers, pymupdf
**Storage**: N/A (Kafka is external transport)
**Testing**: pytest
**Target Platform**: Linux worker runtime
**Project Type**: Background worker service
**Performance Goals**: Keep current poll-to-completion behavior within existing SC-005 budget; no regression from abstraction removal
**Constraints**: No FastAPI runtime; no topic creation at startup; no handler/factory indirection; no classes/validators in `helpers.py`; defer advanced validation/error hardening with TODOs
**Scale/Scope**: Single-worker process consuming `rag` and producing `rag-complete`; no planner-side logic changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: Run `ruff check project rag_agent`, `ruff format --check project rag_agent`, and `python -m compileall project rag_agent`.
- Testing Gate: Run targeted and full `rag_agent/tests` suites for worker loop, Kafka integration, and request/completion flow.
- UX Consistency Gate: Preserve current event contracts and message semantics (request-in, completion-out) for downstream consumers.
- Performance Gate: Maintain current poll loop behavior and avoid additional blocking abstractions in consume/process/publish stages.
- Maintainability Gate: Keep runtime ownership explicit (`worker.py` orchestration, `kafka.py` transport, `agent.py` processing, `helpers.py` env extraction).

Post-Design Re-check (Phase 1): PASS
- Design adheres to simplicity and observability principles.
- Deferred validations and exception hardening are explicitly tracked as TODO scope.

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
rag_agent/
├── agent.py
├── kafka.py
├── worker.py
└── utils/
    └── helpers.py         # env extraction helpers only

project/
├── schemas.py
└── topics.py
```

**Structure Decision**: Keep runtime flow explicit and linear: `worker.py` owns consumer thread and processing pipeline orchestration; `kafka.py` owns Kafka client lifecycle and produce/consume helper functions; `agent.py` performs retrieval logic only and returns output objects.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| None | N/A | N/A |

## Phase 0: Research Findings

All open ambiguities from current scope are resolved in the clarification sessions. No additional NEEDS CLARIFICATION items remain.

Research outcomes are documented in `specs/001-rag-retrieval-agent/research.md` with explicit decisions for:
- direct worker startup and topic-presence check
- `kafka.py`-owned env config and producer/consumer functions
- direct consumer-loop call into `agent.py`
- Kafka publication from consumer loop only
- simplified `helpers.py` (env extraction only)

## Phase 1: Design Artifacts

Design outputs updated:
- `specs/001-rag-retrieval-agent/data-model.md`
- `specs/001-rag-retrieval-agent/contracts/rag-agent-contract.md`
- `specs/001-rag-retrieval-agent/quickstart.md`

No additional external API contracts are required beyond Kafka message and runtime module contracts.
