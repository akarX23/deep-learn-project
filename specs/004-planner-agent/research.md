# Research: Planner Agent Orchestrator

**Feature**: `004-planner-agent`  
**Branch**: `005-add-planner-agent`  
**Date**: 2026-06-14

## Decision 1: Single Worker + Single Multi-Topic Consumer

**Decision**: Use one `run_worker` process and one Kafka consumer subscribed to `init-planner`, `rag-complete`, `teaching-complete`, and `quiz-complete`.

**Rationale**: This minimizes boilerplate while keeping orchestration state local and deterministic. A single consumer loop simplifies ordering, logging, and error handling, and directly satisfies FR-001 and FR-021.

**Alternatives considered**:
- Separate worker loops per topic group: more coordination overhead and duplicated error handling.
- Separate service for completion events: extra deployment complexity for MVP.

## Decision 2: Topic-Based Dispatch and Schema Validation

**Decision**: Branch handling by `message.topic`, then parse payload with topic-specific Pydantic schemas before invoking planner APIs (`run` or `resume`).

**Rationale**: Topic routing is explicit, strongly typed, and easy to test. Schema-first parsing prevents cross-topic payload drift and ensures strict message boundaries (FR-016).

**Alternatives considered**:
- Heuristic payload detection without topic routing: ambiguous and brittle.
- Untyped dict handling: faster to write, weaker guarantees and poorer debuggability.

## Decision 3: Pause via `interrupt()`, Resume via `Command(resume=...)`

**Decision**: Pause graph execution using LangGraph `interrupt()` semantics and resume with `Command(resume=...)` when completion events arrive.

**Rationale**: This follows the documented LangGraph interrupt model and aligns with clarified requirements. It preserves graph control flow integrity and avoids ad hoc state-machine behavior.

**Alternatives considered**:
- Static `interrupt_after` graph config: does not match clarified requirement.
- Manual state polling + re-invocation without command resume: less expressive and easier to break.

## Decision 4: Request-Correlated Kafka Keying

**Decision**: Set Kafka message key to `request_id` for every planner-produced event.

**Rationale**: Keying by `request_id` keeps workflow messages partition-coherent and improves traceability/log correlation across dispatch and completion events.

**Alternatives considered**:
- No key (round-robin partitioning): weak ordering/correlation per workflow.
- Key by `sid`: less precise than workflow-level identity.

## Decision 5: Planner-Local Configuration with dotenv Non-Override

**Decision**: Keep planner-local LLM/Kafka configuration and load `.env.local` via `dotenv.load_dotenv(override=False)`.

**Rationale**: Preserves runtime environment precedence and avoids hidden coupling to other agent configuration surfaces.

**Alternatives considered**:
- Reusing rag config module: violates ownership boundary (FR-015).
- `override=True`: can unexpectedly mask system-provided secrets.

## Decision 6: Observability and Type Safety as Non-Negotiable Constraints

**Decision**: Emit stage-level logs for consume, route, dispatch, pause, resume, and completion; require explicit type annotations on planner APIs.

**Rationale**: The planner is integration-heavy; operational debugging requires request-scoped visibility. Strong typing reduces message and state regressions.

**Alternatives considered**:
- Minimal logging only on errors: insufficient for resume-flow debugging.
- Relaxed typing with broad `Any`: faster iteration but weaker contracts.
