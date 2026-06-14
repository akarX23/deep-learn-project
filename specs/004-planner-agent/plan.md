# Implementation Plan: Planner Agent Orchestrator

**Branch**: `005-add-planner-agent` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-planner-agent/spec.md`

## Summary

Implement a LangGraph-based planner orchestrator that runs with a single `run_worker` loop and a single Kafka consumer subscribed to `init-planner`, `rag-complete`, `teaching-complete`, and `quiz-complete`. The planner must branch by `message.topic`, schema-validate payloads, dispatch appropriate graph actions (`run` for init events, `resume` for completion events), publish downstream events keyed by `request_id`, pause via `interrupt()`, and resume via `Command(resume=...)`.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: langgraph 1.2.x, langchain-core, kafka-python, pydantic v2, litellm, python-dotenv, pytest, ruff  
**Storage**: In-memory LangGraph checkpointing (`MemorySaver`) and in-process state only (no durable persistence)  
**Testing**: pytest (`planner_agent/tests`), contract/schema assertions in unit tests, integration-style resume-flow tests  
**Target Platform**: Linux service runtime (backend worker)  
**Project Type**: Backend service worker / orchestrator module  
**Performance Goals**: 
- Level inference path <= 2s per request (SC-002)
- Post-finalization dispatch <= 500ms (SC-003)
- Completion consume + state update <= 1s (SC-004)
**Constraints**: 
- One worker and one consumer for all required topics
- Strong typing and schema boundaries on all message I/O
- Environment loading via `dotenv.load_dotenv(override=False)`
- Pause with `interrupt()` and resume with `Command(resume=...)`
- Minimal boilerplate without compromising logging or type safety
**Scale/Scope**: MVP orchestrator for RAG + Teaching + Quiz workflows with per-request in-memory state

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: Use `ruff check project planner_agent`, `ruff format --check project planner_agent`, and explicit type annotations for all planner APIs. Fail fast on any lint/format/type contract issue.
- Testing Gate: Require unit tests for topic routing, schema parsing, keying behavior, interrupt/resume correctness, and regression tests for clarify/inference/dispatch branches.
- UX Consistency Gate: Maintain existing user-facing event contracts (`clarify-user-level`, `workflow-complete`) and `sid` correlation semantics used by backend/websocket flow.
- Performance Gate: Validate SC-002/SC-003/SC-004 with targeted timing-friendly tests and lightweight worker logic (single consumer dispatch by topic).
- Maintainability Gate: Log every major stage with `request_id` correlation; document non-obvious graph pause/resume and topic routing decisions in `research.md` and contracts.

Post-design re-check: PASS. No constitution violations require exception handling.

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
planner_agent/
├── __init__.py
├── agent.py
├── config.py
├── kafka.py
├── llm_client.py
├── prompts.py
├── worker.py
└── tests/
    ├── __init__.py
    ├── test_planner_agent.py
    ├── test_level_inference.py
    ├── test_worker_runtime.py
    ├── test_completion_resume.py
    └── test_dotenv_loading.py

project/
├── schemas.py
└── topics.py

backend_service/
└── app/
    └── (topic bootstrap + API integration points)
```

**Structure Decision**: Keep planner implementation inside `planner_agent/` mirroring established agent layout and shared schemas/topics in `project/`.

## Phase 0: Research Outcomes

Research confirms:
1. LangGraph pause/resume semantics should use `interrupt()` inside nodes and `Command(resume=...)` during resumption.
2. Single-consumer topic branching is the simplest reliable worker architecture for this phase.
3. Kafka message key should be `request_id` for all planner-produced events to preserve partition affinity per workflow.
4. Completion payloads must be schema-validated per topic before resumption.

(Details captured in [research.md](./research.md).)

## Phase 1: Design Outcomes

1. Data model updated for one-worker multi-topic consumption and explicit completion event schemas.
2. Kafka contract updated to include topic-based dispatch rules, keying requirement, and active completion consumption.
3. Quickstart updated to reflect real runtime behavior (single worker handles init + completion).
4. Agent context reference already points to this plan in `.github/copilot-instructions.md`.

## Complexity Tracking

No constitution gate violations and no approved complexity exceptions.
