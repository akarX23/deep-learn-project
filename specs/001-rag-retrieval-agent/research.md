# Research: RAG Agent Deterministic Parallel Loop Simplification

## Decision 1: Remove LangGraph StateGraph from page processing path
- Decision: Do not use LangGraph StateGraph for PDF page processing in `agent.py`.
- Rationale: Clarified requirement prioritizes massive simplification and deterministic direct flow.
- Alternatives considered: Retaining graph orchestration with simplified nodes (rejected: still adds boilerplate/state structure).

## Decision 2: Use deterministic for-loop with bounded parallel dispatch
- Decision: Build page pointers deterministically, dispatch page tasks in parallel with configured max workers, then reduce in pointer order.
- Rationale: Keeps code simple while preserving bounded concurrency and deterministic outputs.
- Alternatives considered: Completion-order aggregation (rejected: non-deterministic output ordering).

## Decision 3: Keep final state minimal
- Decision: Final state stores only successful extracted page content plus a simple failed-page list (page number + reason).
- Rationale: Matches clarified scope to avoid complex intermediate state models.
- Alternatives considered: Rich per-page state machine objects (rejected: unnecessary complexity).

## Decision 4: Exclude failed pages from extracted content
- Decision: Failed pages are ignored in extracted-content aggregation and retained-content context.
- Rationale: Explicit clarification requires failures tracked separately, not mixed into extracted content.
- Alternatives considered: Keep failed pages with failure status in extracted output (rejected: conflicts with clarified requirement).

## Decision 5: Keep logging stage-oriented and simple
- Decision: Log key stages only (`page_dispatched`, `page_processed`, `page_failed`, `state_reduced`) with request correlation when available.
- Rationale: Provides operational visibility without introducing complex observability framework.
- Alternatives considered: Expanded structured telemetry/events (rejected for this scope).

## Decision 6: Keep validation and exception handling basic
- Decision: Retain lightweight payload validation and broad exception handling with continue-on-failure behavior.
- Rationale: Matches user requirement for minimal boilerplate and deferred hardening.
- Alternatives considered: Deep validation taxonomy and retry orchestration (deferred).