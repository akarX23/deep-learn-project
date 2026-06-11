# Research: RAG Kafka Event Integration

## Decision 1: Kafka Boundary Module
- Decision: Implement all Kafka connection logic, producer/consumer initialization, and send/receive controller functions in a single `rag_agent/kafka.py` module.
- Rationale: Enforces one integration boundary, simplifies testing/mocking, and prevents transport logic from leaking across service code.
- Alternatives considered: Split producer/consumer across multiple modules (more indirection and coordination overhead), inline Kafka calls in service handlers (poor maintainability).

## Decision 2: Topic Registry Strategy
- Decision: Define all cross-service topic names in `project/topics.py` using enums grouped by service domain.
- Rationale: Centralized topic ownership avoids hardcoded strings and keeps agent/service topic contracts discoverable.
- Alternatives considered: Topic constants local to each service module (duplication risk), environment-only topic names (harder contract governance).

## Decision 3: Kafka Configuration Source
- Decision: RAG Kafka clients inherit connection details using existing `BACKEND_KAFKA*` environment flags.
- Rationale: Reuses established backend Kafka configuration contract and avoids introducing duplicate RAG-specific transport flags.
- Alternatives considered: New `RAG_KAFKA_*` flag set (configuration drift), static config file (less deployment flexibility).

## Decision 4: Service Runtime Model
- Decision: Convert the RAG integration entrypoint into a lightweight FastAPI service that stays alive and hosts startup lifecycle hooks.
- Rationale: Provides reliable process lifecycle, startup orchestration, and health/debug surfaces while keeping retrieval logic unchanged in `RAGAgent`.
- Alternatives considered: Standalone infinite consumer script (weaker lifecycle control), embedding consumer inside existing CLI path only (not service-friendly).

## Decision 5: Startup Topic Bootstrap Flow
- Decision: On FastAPI startup, call backend topic API via `BACKEND_API_TOPIC_URL` to ensure required topics exist before consumer polling begins.
- Rationale: Topic creation remains centralized in backend service while RAG ensures readiness for event processing.
- Alternatives considered: RAG direct topic creation via admin client (duplicates backend concern), manual pre-provisioning only (fragile operational setup).

## Decision 6: Consumer Loop and Dispatch
- Decision: Initialize a continuous polling loop that consumes from topic `rag`, validates event payload, and dispatches to explicit handler functions.
- Rationale: Keeps event handling deterministic and allows non-fatal continuation across malformed messages or per-request failures.
- Alternatives considered: Batch poll-and-process framework with opaque callbacks (harder observability), one-shot consumer invocation (not suitable for service mode).

## Decision 7: Completion Event Contract
- Decision: Publish processing results to topic `rag-complete` with `session_ctx`, `user_prompt`, `compiled_material`, status, errors, timing, and correlation metadata.
- Rationale: Downstream services need both retrieval output and lifecycle metadata for orchestration and diagnostics.
- Alternatives considered: Minimal success-only payload (insufficient for partial/failure handling), include full extracted page internals in event (payload bloat).

## Decision 8: Logging Strategy
- Decision: Emit structured progress logs at stages: consumed, validated, processing_started, processing_completed, publish_completed, and error stages.
- Rationale: Enables end-to-end traceability per request and supports faster incident diagnosis.
- Alternatives considered: Freeform log strings (harder querying), only error-level logs (insufficient flow visibility).

## Decision 9: Scope Guardrail
- Decision: Do not implement Planner agent logic; only consume Planner-produced events and process through RAG pipeline.
- Rationale: Preserves bounded feature scope and avoids cross-agent coupling beyond contract integration.
- Alternatives considered: Planner-side fallback or orchestration logic in RAG service (scope violation).
