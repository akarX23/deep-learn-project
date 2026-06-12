# Research: RAG Kafka Worker Simplification

## Decision 1: Worker Runtime Model
- Decision: Run Kafka integration as a standalone worker process with a dedicated consumer thread instead of a FastAPI lifecycle host.
- Rationale: Aligns directly with scope constraints, reduces moving parts, and avoids HTTP runtime coupling for background event processing.
- Alternatives considered: Keep FastAPI lifecycle orchestration (violates new requirements), use synchronous blocking loop on main thread (harder graceful shutdown and control).

## Decision 2: Startup Topic Presence Check
- Decision: Replace topic-creation startup flow with direct Kafka metadata checks for required topics and log warnings if missing.
- Rationale: Supports externally managed topic provisioning while preserving operator visibility at startup.
- Alternatives considered: Auto-create topics on startup (explicitly out of scope), fail hard on missing topics (contradicts continue-with-warning requirement).

## Decision 3: Remove Backend Topic API Dependency
- Decision: Eliminate direct backend topic API calls and remove associated runtime variables from worker startup contract.
- Rationale: Removes cross-service startup dependency and simplifies configuration surface.
- Alternatives considered: Keep optional backend bootstrap call (unnecessary coupling), keep variable but unused (configuration ambiguity).

## Decision 4: Kafka Gateway Responsibilities
- Decision: Keep Kafka transport concerns in `rag_agent/kafka.py` and add typed helper functions for metadata checks, polling, and publish flows.
- Rationale: Preserves a single integration boundary and keeps worker orchestration code concise.
- Alternatives considered: Spread Kafka client operations across worker and handler modules (reduced maintainability).

## Decision 5: Simplified Request Handler Scope
- Decision: Keep `RAGRequestEventHandler` focused on ingesting events and dispatching to `RAGAgent`, with advanced validation and metrics marked as TODO for later.
- Rationale: Delivers core behavior quickly while making deferred concerns explicit and traceable.
- Alternatives considered: Implement full validation/metrics now (larger scope than requested), remove TODO markers (loses clarity on deferred work).

## Decision 6: Type Safety Emphasis
- Decision: Use explicit type annotations for public function inputs/outputs in worker, Kafka, and handler modules, avoiding untyped generic placeholders wherever practical.
- Rationale: Improves reviewability and reduces runtime ambiguity in event-processing boundaries.
- Alternatives considered: Preserve broad untyped signatures (faster short-term but less maintainable).

## Decision 7: Failure Semantics
- Decision: Keep per-event failures non-fatal; log stage-scoped errors and continue consumer loop operation.
- Rationale: Matches resilience requirements and avoids worker downtime from isolated bad events.
- Alternatives considered: Fail-fast on handler exceptions (poor availability), silent retries without logs (weak observability).

## Decision 8: Logging Strategy
- Decision: Maintain structured lifecycle logging with startup check stages and request processing stages (`consumed`, `processing_started`, `processing_completed`, `publish_completed`, `error`).
- Rationale: Supports operator diagnostics while fitting simplified handler scope.
- Alternatives considered: Freeform logs only (harder filtering/analysis), no startup-stage logs (poor readiness visibility).

## Decision 9: Scope Guardrail
- Decision: Continue excluding planner-side logic; only consume planner-produced events and emit RAG completion events.
- Rationale: Keeps this feature bounded to RAG runtime behavior.
- Alternatives considered: planner-side fallback behavior inside worker (scope violation).

## Implementation Evidence
- Replaced FastAPI service lifecycle with standalone worker runtime in `rag_agent/worker.py`.
- Removed backend topic API startup dependency from config and environment templates.
- Added Kafka topic presence metadata checks that warn-and-continue on missing topics.
- Added structured startup-stage logging (`startup_topic_check`) and kept request lifecycle stages.
- Added worker runtime test coverage for lifecycle, idle loop continuity, startup topic checks, and non-fatal per-event failures.
- Added typed handler contract and TODO-marker tests for deferred validation/metrics scope.

## Deferred TODO Scope
- Advanced semantic/event validation in `RAGRequestEventHandler.parse_event`.
- Metrics instrumentation (timing/throughput counters) in `RAGRequestEventHandler.process_request`.
- Full local end-to-end quickstart validation against a running Kafka stack remains environment-dependent.
