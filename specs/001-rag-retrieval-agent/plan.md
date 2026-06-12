# Implementation Plan: RAG Kafka Worker Simplification

**Branch**: `[001-build-rag-retrieval-agent]` | **Date**: 2026-06-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-rag-retrieval-agent/spec.md`

## Summary

Refactor the RAG Kafka runtime from a FastAPI-hosted lifecycle to a standalone worker process that runs a dedicated consumer thread, removes backend topic-creation API dependencies, performs startup Kafka topic-presence checks, and keeps request handling focused on ingestion and dispatch with strongly typed function boundaries.

## Technical Context

**Language/Version**: Python 3.12.x  
**Primary Dependencies**: kafka-python, Python stdlib threading/logging, existing rag_agent pipeline dependencies  
**Storage**: N/A (stateless worker, Kafka transport only)  
**Testing**: pytest (unit + integration-style worker tests with Kafka adapter mocking)  
**Target Platform**: Linux worker runtime with Kafka cluster connectivity  
**Project Type**: Backend worker process  
**Performance Goals**: p95 poll-to-completion latency within SC-005 budget; completion emission success >= 99% for terminal attempts  
**Constraints**:
- No FastAPI runtime dependency for Kafka worker lifecycle
- No startup topic creation calls and no backend topic API dependency
- Startup must check topic presence directly against Kafka metadata and continue with warnings when topics are missing
- Handler remains intentionally minimal (ingest + dispatch), with validation/metrics deferred via explicit TODO markers
- Public worker/Kafka/handler function boundaries must be strongly typed and avoid broad untyped placeholders
**Scale/Scope**:
- Consume one request topic (`rag`), emit one completion topic (`rag-complete`)
- Preserve existing `RAGAgent` retrieval behavior
- Focus only on runtime architecture and dispatch simplification (no planner logic)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- Code Quality Gate: PASS
- Enforce `.venv/bin/ruff check`, `.venv/bin/ruff format --check`, and `.venv/bin/python -m compileall` on touched modules.
- Testing Gate: PASS
- Require tests for worker startup/shutdown lifecycle, topic-presence check warnings, consume-dispatch loop behavior, completion publish behavior, and non-fatal per-event failure continuation.
- UX Consistency Gate: PASS
- Ensure startup logs and lifecycle stage names stay consistent and actionable for operators.
- Performance Gate: PASS
- Validate polling latency and completion emission reliability under representative load.
- Maintainability Gate: PASS
- Keep Kafka transport in `rag_agent/kafka.py`, worker lifecycle in non-FastAPI runtime module, and simplified typed handler boundaries in `rag_agent/handlers.py`.

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
├── config.py
├── handlers.py
├── kafka.py
├── logging.py
├── worker.py                # new worker runtime entrypoint replacing FastAPI lifecycle
└── tests/
    ├── test_request_event.py
    ├── test_completion_event.py
    ├── test_kafka_integration.py
    └── test_worker_runtime.py  # new worker lifecycle tests
```

**Structure Decision**: Keep retrieval internals unchanged, isolate Kafka transport behavior in `rag_agent/kafka.py`, and move process lifecycle ownership into a standalone thread-based worker runtime (`rag_agent/worker.py`) so Kafka processing is independent of HTTP service concerns.

## Phase 0: Research Outcomes

Research decisions are captured in [research.md](./research.md):

- Adopt standalone worker runtime and remove FastAPI dependency from Kafka processing path
- Replace startup topic bootstrap API calls with direct Kafka metadata topic-presence checks
- Continue startup with clear warnings when required topics are missing
- Simplify request handler scope to typed ingest/dispatch flow with deferred TODOs for advanced validation and metrics
- Maintain strong type annotations across worker/Kafka/handler module interfaces

All technical unknowns are resolved.

## Phase 1: Design & Contracts

### Data Model Output

[data-model.md](./data-model.md) defines:
- Worker runtime state and thread lifecycle entities
- Topic presence check result model and warning semantics
- Typed request/completion event contracts used across consume/dispatch/publish flow
- Deferred validation/metrics TODO boundary markers

### Contract Output

[contracts/rag-agent-contract.md](./contracts/rag-agent-contract.md) defines:
- Environment contract without backend topic API dependencies
- Startup Kafka metadata check behavior and warning requirements
- Worker loop consume-dispatch-publish behavior and non-fatal failure semantics
- Typed function boundary requirements and deferred validation/metrics scope

### Quickstart Output

[quickstart.md](./quickstart.md) defines:
- Worker startup commands and environment setup
- Topic presence check verification
- End-to-end event roundtrip validation (`rag` -> `rag-complete`) without backend API calls

### Agent Context Update

- `.github/copilot-instructions.md` must reference `specs/001-rag-retrieval-agent/plan.md` in SPECKIT marker blocks.

## Post-Design Constitution Check

- Code Quality Gate: PASS
- Quality checks and compile validation are explicit and executable.
- Testing Gate: PASS
- Worker lifecycle, topic-presence check, dispatch/publish, and failure continuation tests are explicitly required.
- UX Consistency Gate: PASS
- Startup and runtime logs are specified with consistent stage naming and warning semantics.
- Performance Gate: PASS
- Poll-to-completion latency and completion emission reliability remain measurable requirements.
- Maintainability Gate: PASS
- Architecture is simplified by removing HTTP lifecycle coupling and external topic-bootstrap API dependencies.

## Complexity Tracking

No constitution violations requiring exception handling were identified in planning.
