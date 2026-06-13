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

## Decision 9: WebSocket Transport
- **Decision**: Use Socket.IO via `python-socketio` (ASGI) mounted onto the FastAPI app for the frontend WebSocket channel.
- **Rationale**: Native named-event listeners (`@sio.on(...)`) and `sio.emit(event, data, to=sid)` map directly to the spec's "lightweight listeners + emit named events" design and provide per-connection routing with minimal boilerplate (FR-020).
- **Alternatives considered**: FastAPI/Starlette native `WebSocket` endpoints (requires a custom event-name dispatch layer), raw ASGI WebSocket (more boilerplate, no built-in event model).

## Decision 10: Shared WebSocket Contract Location
- **Decision**: Define shared WebSocket contracts in `project/events.py` using event-name constants plus event body schemas. For now include `stream-tokens` with body fields `from_service`, `content`, and `metadata`.
- **Rationale**: Frontend and backend must agree not only on event names but also on body shape. Keeping both in a shared module provides one source of truth and reduces contract drift (FR-021, FR-022).
- **Alternatives considered**: Names-only in `events.py` with body schema elsewhere (higher drift risk), registry metadata + handlers (over-engineered for current scope).

## Decision 11: Session Identity and Connection Manager
- **Decision**: Treat the application `session_id` as identical to the Socket.IO-generated `sid`; a simple `ConnectionManager` class maps `session_id -> connection` with minimal `get`/`set` methods. A user may own multiple independent sessions; each session is routed independently.
- **Rationale**: All inbound data carries a `session_id`, so keying directly on `sid` removes any translation layer and keeps routing to a single lookup (FR-023, FR-024). Independence avoids cross-session leakage.
- **Alternatives considered**: Separate app `session_id` mapped to `sid` (extra indirection), `user_id`-keyed many-to-one mapping (sessions are independent here, so not needed), Socket.IO rooms (unnecessary abstraction when `sid` already identifies the target).

## Decision 12: Listener Placement and Emit Signature
- **Decision**: Place lightweight Socket.IO listeners in a dedicated `backend_service/app/socket.py`, and expose `emit_event(event, payload, session_id)` in the same file to emit a named event to the connection identified by `session_id`. Listeners and `stream-tokens` emission logic are stubbed for later implementation.
- **Rationale**: Centralizes WebSocket wiring in one file with a single emit entry point routed by `session_id` (== `sid`), matching FR-025 and FR-026 while keeping boilerplate minimal.
- **Alternatives considered**: `emit_event(event, payload, user_id)` (routing is per-session, not per-user), spreading listeners across modules (harder to locate), fully implementing listeners now (spec defers behavior via TODO).

## Decision 13: Deferred WebSocket Edge Cases
- **Decision**: Defer disconnect cleanup, missing-`session_id` handling, concurrent-emit ordering/back-pressure, and WebSocket authentication via explicit TODO markers.
- **Rationale**: Spec FR-027 mandates the simplest approach with minimum boilerplate; deferring non-essential resilience keeps the first iteration small and reviewable.
- **Alternatives considered**: Implementing full lifecycle/auth now (scope creep against the spec's stated simplicity goal).

## Decision 14: Add UserRequest Schema in Shared Backend Contracts
- **Decision**: Add `UserRequest` to `project/schemas.py` with fields `user_prompt`, `user_level` (`list[str]`), `file_data`, and `sid`.
- **Rationale**: The WebSocket and async request flow now requires a standard backend request envelope keyed by session identity; defining it in shared schemas keeps downstream agent/backend contracts explicit (FR-028).
- **Alternatives considered**: Defining `UserRequest` in `backend_service` only (less reusable), embedding this shape ad hoc in endpoint handlers (no central contract).

## Decision 15: Validation Scope for New Schemas
- **Decision**: Do not add custom validation or exception-handling logic for `stream-tokens` event body schema and `UserRequest` in this iteration.
- **Rationale**: Explicitly matches the feature constraint to keep implementation minimal and defer hardening to later TODO tasks (FR-029).
- **Alternatives considered**: Strict validators now (extra boilerplate and premature complexity).
