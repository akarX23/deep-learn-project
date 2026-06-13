# Research: Backend Kafka Startup Bootstrap + RAG Test-Event API

## Decision 1: Topic Name Source
- **Decision**: Read topic names from `project/topics.get_all_topic_names()` as the single startup source.
- **Rationale**: Centralized registry avoids config drift and keeps topic provisioning in one authoritative module.
- **Alternatives considered**: Environment-provided topic lists (drift risk), hard-coded backend list (duplicate source of truth).

## Decision 2: Bootstrap Placement
- **Decision**: Keep topic bootstrap in `KafkaAdminService.bootstrap_topics(topic_names)` and call it from FastAPI lifespan startup.
- **Rationale**: Preserves cohesion of Kafka admin operations and clean startup sequencing (`connect -> bootstrap -> serve -> close`).
- **Alternatives considered**: Standalone helper in `main.py` (splits Kafka logic), direct client calls from lifespan (harder to test/mocks).

## Decision 3: Idempotency + Non-Fatal Startup Errors
- **Decision**: Treat existing topics as success and continue startup when individual topic creation fails, recording errors in `StartupTopicBootstrapResult`.
- **Rationale**: Meets FR-003 and FR-008 while preserving observability via explicit warning logs.
- **Alternatives considered**: Fail-fast on first topic error (violates spec behavior), silent ignore (insufficient diagnostics).

## Decision 4: Test-Event API Scope Pattern
- **Decision**: Introduce topic-scoped test-event endpoint(s), starting with `rag`, and keep route behavior publish-only (no direct agent invocation).
- **Rationale**: Aligns with FR-009 and FR-012 while establishing an extensible per-topic route pattern.
- **Alternatives considered**: One generic topic endpoint for all payload types (weaker schema guarantees), direct service invocation route (violates scope boundary).

## Decision 5: Environment Gating
- **Decision**: Gate test-event routes by environment with dev/test enabled by default and production requiring explicit opt-in flag.
- **Rationale**: Satisfies FR-013 and FR-014 and minimizes accidental production misuse.
- **Alternatives considered**: Always-enabled routes (unsafe for prod), always-disabled unless enabled everywhere (friction in local testing).

## Decision 6: Direct RAG Request Body
- **Decision**: Use the `RAGRequestEvent` schema directly as the rag test-event request body, with model defaults applied where fields are omitted.
- **Rationale**: Keeps the API contract simple and avoids merge logic while still providing a predictable default payload shape.
- **Alternatives considered**: Separate override wrapper (extra indirection), custom request DTO (duplicates the schema).

## Decision 7: Publish Metadata Contract
- **Decision**: Return a normalized publish-result envelope with required correlation/status fields and optional Kafka metadata object (partition/offset/timestamp) when available.
- **Rationale**: Meets FR-015 and FR-016 while handling partial metadata scenarios without breaking API shape.
- **Alternatives considered**: Return raw broker object (leaky abstraction), omit metadata entirely (misses accepted clarification).

## Decision 8: Logging and Performance Validation
- **Decision**: Keep startup summary logs at INFO, detailed outcomes at DEBUG, and validate two budgets: startup bootstrap <= 5s and test publish response <= 2s p95 in local dev.
- **Rationale**: Satisfies observability and performance gates from constitution and spec success criteria.
- **Alternatives considered**: Minimal logs only (insufficient traceability), no explicit response-time budget (performance gate miss).
