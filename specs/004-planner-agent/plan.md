# Implementation Plan: Planner Agent Orchestrator

**Branch**: `005-add-planner-agent` | **Date**: 2026-06-14 | **Spec**: `/specs/004-planner-agent/spec.md`
**Input**: Feature specification from `/specs/004-planner-agent/spec.md`

## Summary

Build a LangGraph-based planner orchestrator that consumes `init-planner` events, assigns `request_id`, infers user level + quiz intent, dispatches RAG/Teaching/Quiz work via Kafka, tracks in-memory workflow state, and emits `clarify-user-level` or `workflow-complete` events. The implementation keeps MVP constraints (no persistence, no complex retries) while enforcing planner-local LiteLLM config, schema-conformant message boundaries, explicit typing, and stage-level logging.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: langgraph>=1.2.0, langchain-core>=1.4.0, kafka-python, pydantic v2, litellm  
**Storage**: In-memory only (`MemorySaver` + process memory dict state)  
**Testing**: pytest, monkeypatch-based unit tests, schema/topic assertions  
**Target Platform**: Linux worker runtime (local + containerized dev)  
**Project Type**: Backend worker/orchestrator service  
**Performance Goals**: Inference <= 2s/request (`SC-002`), dispatch <= 500ms after level finalization (`SC-003`)  
**Constraints**: No persistence layer, no advanced retries/transactions, indefinite workflow lifetime (no timeout), strict schema boundaries  
**Scale/Scope**: Single-process MVP orchestrator for planner workflows; one thread_id per request (`request_id`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: `ruff check project planner_agent` and `ruff format --check project planner_agent` are mandatory and blocking.
- Testing Gate: Add planner unit/runtime tests covering request_id assignment, inference branching, dispatch routing, completion event emission, schema/topic compatibility, and malformed input survival.
- UX Consistency Gate: Planner is backend-facing; user-facing consistency is enforced through stable event schemas (`clarify-user-level`, `workflow-complete`) consumed by existing backend/WebSocket flow.
- Performance Gate: Validate inference and dispatch budgets in tests/instrumented logs; keep fan-out overhead bounded by small `user_levels` set.
- Maintainability Gate: Structured stage-level logs with `request_id` correlation; TODO markers for deferred persistence/retry/resume-consumer work; documentation artifacts updated.

### Post-Design Constitution Re-check

- Code Quality Gate: PASS (planned checks and explicit type signatures documented).
- Testing Gate: PASS (tests specified for all user stories and schema conformance).
- UX Consistency Gate: PASS (contract-stable outgoing events maintained).
- Performance Gate: PASS (budgets retained and measurable through logs/tests).
- Maintainability Gate: PASS (observability requirement elevated to functional requirement `FR-014`).

## Project Structure

### Documentation (this feature)

```text
specs/004-planner-agent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── planner-kafka-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
project/
├── schemas.py
└── topics.py

planner_agent/
├── __init__.py
├── agent.py
├── config.py
├── kafka.py
├── prompts.py
├── worker.py
└── tests/
    ├── __init__.py
    ├── inputs/
    │   └── sample_input.json
    ├── test_level_inference.py
    ├── test_planner_agent.py
    └── test_worker_runtime.py
```

**Structure Decision**: Single backend codebase with a dedicated `planner_agent/` package mirroring existing agent-package conventions, while shared message contracts remain in `project/`.

## Phase 0: Research Output

`research.md` resolves all technical unknowns and records decisions for graph architecture, checkpointing, fan-out, planner-local LLM configuration, Kafka integration pattern, schema placement, topics, and observability/type-safety constraints.

## Phase 1: Design Output

- `data-model.md`: Defines `PlannerState` and all inter-agent payload contracts.
- `contracts/planner-kafka-contract.md`: Defines inbound/outbound topic contracts with payload examples and serialization expectations.
- `quickstart.md`: Defines runtime setup, env vars, run/test flow, and graph behavior.
- Agent context reference updated to point to this plan in `.github/copilot-instructions.md`.

## Complexity Tracking

No constitution violations requiring exceptions.
