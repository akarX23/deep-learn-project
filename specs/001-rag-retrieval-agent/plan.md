# Implementation Plan: RAG Kafka Event Integration

**Branch**: `[001-build-rag-retrieval-agent]` | **Date**: 2026-06-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-rag-retrieval-agent/spec.md`

## Summary

Integrate the existing RAG retrieval pipeline into a lightweight FastAPI service that consumes request events from Kafka topic `rag`, executes RAGAgent processing, and publishes completion events to topic `rag-complete`. Kafka connectivity must reuse `BACKEND_KAFKA*` environment flags, topic names must be centralized in `project/topics.py` enums, startup must call backend topic-creation API via `BACKEND_API_TOPIC_URL`, and all produce/consume interactions must pass through one `rag_agent/kafka.py` module.

## Technical Context

**Language/Version**: Python 3.12.x
**Primary Dependencies**: FastAPI, Uvicorn, kafka-python, requests/httpx (backend API call), existing rag_agent pipeline deps
**Storage**: N/A (stateless service; Kafka as message transport)
**Testing**: pytest + FastAPI TestClient + Kafka adapter mocking
**Target Platform**: Linux service runtime with Kafka cluster connectivity
**Project Type**: Backend event-driven web service
**Performance Goals**:
- p95 consume-to-complete processing latency within agreed integration budget per SC-005
- completion event publish success rate >= 99% for valid consumed requests
**Constraints**:
- RAG service must remain on branch `001-build-rag-retrieval-agent`
- Use one `rag_agent/kafka.py` for Kafka connection, producer/consumer init, and all send/receive controller functions
- Topic enums for all agents/services must reside in `project/topics.py`
- Kafka bootstrap and related connection settings inherit from `BACKEND_KAFKA*` env flags
- FastAPI startup must call backend API topic endpoint using `BACKEND_API_TOPIC_URL`
- Consumer loop continuously polls Kafka and dispatches to event handlers
- No Planner-agent business logic implementation in this feature
**Scale/Scope**:
- Consume one request event type (`rag`) and emit one completion event type (`rag-complete`)
- Reuse existing `RAGAgent` execution pipeline for retrieval work
- Add service lifecycle observability for consume/process/publish stages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- Code Quality Gate: PASS
- Enforce `ruff check`, `ruff format --check`, and `python -m compileall` for changed service and integration modules.
- Testing Gate: PASS
- Require tests for event validation, Kafka consume-dispatch behavior, completion publish payload shape, startup topic bootstrap call, and non-fatal error continuation.
- UX Consistency Gate: PASS
- Keep event payload schemas stable and logging stage names predictable across request lifecycle.
- Performance Gate: PASS
- Define and measure consume-to-complete latency and completion publish success rate.
- Maintainability Gate: PASS
- Centralize Kafka concerns in `rag_agent/kafka.py`; centralize topic enums in `project/topics.py`; keep event handlers explicit and traceable.

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
└── topics.py                     # new topic enums for all services

rag_agent/
├── agent.py                      # existing retrieval pipeline
├── kafka.py                      # new single Kafka connection+controller module
├── service.py                    # new FastAPI app lifecycle and consumer bootstrap
├── config.py                     # inherit BACKEND_KAFKA* and BACKEND_API_TOPIC_URL
└── tests/
    ├── test_rag_agent.py
    └── test_kafka_integration.py # new integration-focused tests

backend_service/
└── app/api/topics.py             # existing topic creation endpoint consumed at startup
```

**Structure Decision**: Keep retrieval logic in existing `rag_agent/agent.py`, add one Kafka gateway module (`rag_agent/kafka.py`), and add a lightweight FastAPI service entry that orchestrates startup topic bootstrap and continuous consumer polling.

## Phase 0: Research Outcomes

Research decisions are captured in [research.md](./research.md):

- Single-module Kafka boundary (`rag_agent/kafka.py`) for all produce/consume and connection logic
- Shared topic enum registry in `project/topics.py`
- Reuse backend Kafka environment contract (`BACKEND_KAFKA*`) for RAG Kafka clients
- Startup topic bootstrap through backend API (`BACKEND_API_TOPIC_URL`)
- Continuous consumer polling loop with handler dispatch and non-fatal error continuation
- Preserve strict scope: no Planner logic implementation; only consume Planner-produced events

All technical unknowns from template placeholders are resolved.

## Phase 1: Design & Contracts

### Data Model Output

[data-model.md](./data-model.md) defines:
- Incoming `RAGRequestEvent` and outgoing `RAGCompletionEvent`
- Service runtime config entity inheriting `BACKEND_KAFKA*` and `BACKEND_API_TOPIC_URL`
- Consumer lifecycle state and structured log entity for traceability
- Topic enum registry entity for centralized topic name ownership

### Contract Output

[contracts/rag-agent-contract.md](./contracts/rag-agent-contract.md) defines:
- Kafka event payload contracts and validation expectations
- Startup bootstrap contract to backend topic API
- Consume/dispatch/publish behavior and failure semantics
- Logging and correlation metadata contract

### Quickstart Output

[quickstart.md](./quickstart.md) defines:
- Environment setup and required flags
- FastAPI service startup flow
- Topic bootstrap verification
- End-to-end event roundtrip validation (`rag` -> `rag-complete`)

### Agent Context Update

- `.github/copilot-instructions.md` must reference `specs/001-rag-retrieval-agent/plan.md` in SPECKIT marker blocks for current feature context.

## Post-Design Constitution Check

- Code Quality Gate: PASS
- Planned checks and evidence steps are defined and enforceable.
- Testing Gate: PASS
- Contract/integration tests are explicitly required for consume-process-publish lifecycle and startup bootstrap.
- UX Consistency Gate: PASS
- Event schema consistency and logging stage naming are explicitly specified.
- Performance Gate: PASS
- Latency and publish reliability budgets are included in success criteria and quickstart verification.
- Maintainability Gate: PASS
- Kafka logic centralization and explicit handler mapping reduce integration sprawl and improve traceability.

## Complexity Tracking

No constitution violations requiring exception handling were identified in planning.
