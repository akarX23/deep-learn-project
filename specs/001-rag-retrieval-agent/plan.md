# Implementation Plan: RAG Agent Parallel Page Processing on LangGraph

**Branch**: `[001-build-rag-retrieval-agent]` | **Date**: 2026-06-14 | **Spec**: [spec.md](specs/001-rag-retrieval-agent/spec.md)
**Input**: Feature specification from `/specs/001-rag-retrieval-agent/spec.md`

## Summary

Evolve the existing LangGraph-driven RAG flow from sequential page iteration to bounded parallel page execution using the LangGraph StateGraph stack. The agent will process pages independently, enforce max in-flight work via an environment-controlled concurrency limit, preserve per-page extraction semantics, and avoid adding any separate batching orchestration layer.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: langgraph, kafka-python, PyMuPDF (fitz), pydantic v2, litellm
**Storage**: N/A (stateless worker runtime; Kafka topics are transport only)
**Testing**: pytest, ruff check, ruff format --check, python -m compileall
**Target Platform**: Linux server worker process
**Project Type**: Backend worker service
**Performance Goals**:
- Maintain SC-003 publish-success expectation (>=99% terminal attempts emit `rag-complete`)
- Enforce configured parallelism cap deterministically (SC-008)
- Improve multi-page request throughput versus strict sequential processing under representative load
**Constraints**:
- Keep worker-only architecture (no FastAPI runtime)
- Preserve Kafka-agnostic `agent.py` output contract
- No extra page-batching coordinator layer; inference server handles request batching
- Env-driven concurrency: default `4`, clamp minimum `1`
**Scale/Scope**:
- One request may include multiple documents and pages
- Page extraction workloads include text + optional table/image extraction + relevance scoring
- Parallelism applies within a single request execution

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: PASS
  - Preserve simplification direction (no new boilerplate abstractions).
  - Keep explicit typing across public boundaries.
  - Enforce via `ruff check` and `ruff format --check`.
- Testing Gate: PASS
  - Update/add tests for env var parsing, default/clamp behavior, and bounded in-flight processing.
  - Keep existing worker/kafka integration tests green.
- UX Consistency Gate: PASS (N/A direct UI)
  - Operational UX remains structured logs and actionable warning messages.
- Performance Gate: PASS
  - Add measurable bounded concurrency behavior (SC-008).
  - Validate no unbounded task fan-out and compare throughput/latency on representative fixtures.
- Maintainability Gate: PASS
  - Keep TODO markers for deferred hardening only.
  - Document parallel execution flow in quickstart and contract artifacts.

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

**Structure Decision**: Keep the existing worker-centric Python package structure. Implement parallel-page behavior inside `rag_agent/agent.py` using LangGraph StateGraph primitives and bounded concurrency configuration.

## Phase 0: Outline & Research

1. Research LangGraph StateGraph fan-out patterns suitable for independent page processing.
2. Research bounded-concurrency controls compatible with LangGraph graph invocation.
3. Research env-var configuration strategy for deterministic fallback (`default=4`, `min=1`).
4. Consolidate decisions and alternatives in `research.md`.

## Phase 1: Design & Contracts

1. Update data model for parallel page task execution and runtime concurrency config.
2. Update contract to codify:
- new env variable for page parallelism
- bounded in-flight guarantees
- unchanged page-processing semantics
3. Update quickstart with configuration and runtime flow changes.
4. Update agent context reference in `.github/copilot-instructions.md` to this plan.

## Phase 2: Implementation Planning (Tasking Input)

Planned implementation slices:
1. Concurrency config loading and validation in helper/env layer.
2. LangGraph StateGraph refactor from sequential pointer index loop to parallel page execution path.
3. Deterministic merge/reduction of extracted page outputs and errors.
4. Regression and behavior tests for bounded concurrency + fallback defaults.
5. Validation gates: pytest + lint + format + compileall.

## Post-Design Constitution Check

- Code Quality Gate: PASS
  - Design keeps direct runtime flow and avoids abstraction re-introduction.
- Testing Gate: PASS
  - Test plan includes behavior + regression coverage for new parallel semantics.
- UX Consistency Gate: PASS
  - No user-facing UI changes; operator-facing diagnostics remain explicit.
- Performance Gate: PASS
  - Bounded concurrency and SC-008 are encoded in requirements/contracts.
- Maintainability Gate: PASS
  - Artifacts updated with explicit ownership and constraints.

## Complexity Tracking

No constitution violations requiring exception.