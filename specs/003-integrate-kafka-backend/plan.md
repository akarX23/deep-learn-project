# Implementation Plan: Backend Kafka Startup Bootstrap + RAG Test-Event API + WebSocket Channel

**Branch**: `003-integrate-kafka-backend` | **Date**: 2026-06-12 | **Spec**: `specs/003-integrate-kafka-backend/spec.md`
**Input**: Feature specification from `/specs/003-integrate-kafka-backend/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Extend the backend service startup lifecycle to create Kafka topics from `project/topics` idempotently, and add a gated test-event API for topic `rag` that publishes a `RAGRequestEvent` payload directly with default schema values applied. The API returns a normalized publish result with inline Kafka metadata when available. Additionally, mount a Socket.IO WebSocket channel on the FastAPI ASGI app so the frontend can connect and receive asynchronous Kafka-driven results routed per session: a minimal `ConnectionManager` maps `session_id` (== Socket.IO `sid`) to its connection, shared WebSocket contracts live in `project/events.py` (including the `stream-tokens` event name and body schema with `from_service`, `content`, `metadata`), and a dedicated `socket.py` holds lightweight listeners plus an `emit_event(event, payload, session_id)` function. Add a backend `UserRequest` schema in `project/schemas.py` with fields `user_prompt`, `user_level` (`list[str]`), `file_data`, and `sid`. Implementation keeps advanced resilience and WebSocket edge-case handling as TODO-marked follow-ups while satisfying current observability and performance budgets.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Pydantic v2, kafka-python, python-socketio (ASGI), python-dotenv  
**Storage**: N/A (Kafka is external messaging infrastructure, not app-owned storage)  
**Testing**: pytest (unit + integration-like API, startup, and WebSocket connection/emit tests)  
**Target Platform**: Linux backend service runtime (local docker-compose + CI Linux)
**Project Type**: Backend web service (FastAPI + Kafka integration + Socket.IO WebSocket channel)  
**Performance Goals**: Startup topic bootstrap <= 5s in local dev cluster; rag test-event publish response <= 2s p95 in local dev cluster; WebSocket emit dispatch is in-process and non-blocking  
**Constraints**: Synchronous implementation; idempotent topic creation; test-event APIs enabled by default in dev/test, explicit opt-in in production; no direct agent invocation from API; no separate schema model for test-event metadata; single shared producer owned by the Kafka admin layer; WebSocket integration favors minimum boilerplate — connection manager is a simple get/set class, listeners are lightweight stubs, and edge cases (disconnect cleanup, missing session, auth, back-pressure) are deferred via TODO markers; `project/events.py` includes both event-name constants and event body schemas; no additional custom validation or exception handling is required for `stream-tokens` body schema and `UserRequest` in this iteration  
**Scale/Scope**: Current registry includes `rag` and `rag-complete`; immediate scope adds one topic-specific test publish route (`rag`) with extensible per-topic routing pattern, plus a Socket.IO channel with one defined event (`stream-tokens`) and one initial event body schema, and adds backend `UserRequest` schema support

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: Pass `ruff check project backend_service` and `ruff format --check project backend_service`; fail the feature if either check fails.
- Testing Gate: Add/maintain tests for startup bootstrap path, route env-gating behavior, request validation against `RAGRequestEvent`, publish response envelope/metadata behavior, and WebSocket connection registration + per-session `emit_event` routing; run `pytest backend_service/tests -q`.
- UX Consistency Gate: API response patterns must remain consistent with existing backend JSON envelope conventions (`status`, typed response body, explicit error message) and deterministic HTTP status usage; WebSocket event names and body schemas must be sourced from shared contracts in `project/events.py` so frontend and backend stay in sync.
- Performance Gate: Verify bootstrap summary timing under local Kafka is <= 5s and rag test-event request/response path stays within <= 2s p95 under local single-request testing; WebSocket emit is an in-process dispatch with no added budget.
- Maintainability Gate: Keep route wiring in `create_app`, schema contracts in `project/schemas.py` (including `UserRequest`), shared WebSocket contracts in `project/events.py`, and add explicit logging at startup/publish boundaries. WebSocket integration stays minimal: a simple `ConnectionManager` with get/set, lightweight listeners in `socket.py`, and deferred edge cases marked with TODO comments.

Post-Design Re-check (Phase 1): PASS
- No constitution violations introduced by selected design.
- All gates have corresponding implementation/test artifacts planned in Phase 2.
- Simplicity principle upheld: WebSocket layer deliberately defers edge-case handling via TODO markers per spec FR-027.

## Project Structure

### Documentation (this feature)

```text
specs/003-integrate-kafka-backend/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── backend-topic-api-contract.md
│   ├── backend-topic-bootstrap-contract.md
│   └── backend-websocket-contract.md
└── tasks.md
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
backend_service/
├── app/
│   ├── api/
│   │   └── topics.py
│   ├── config.py
│   ├── kafka_admin.py
│   ├── connection_manager.py
│   ├── socket.py
│   └── main.py
└── tests/
  ├── test_startup.py
  ├── test_topics_api.py
  ├── test_connection_manager.py
  └── test_socket.py

project/
├── schemas.py
├── topics.py
└── events.py
```

**Structure Decision**: Keep the existing backend service FastAPI structure and add feature behavior by extending `backend_service/app/main.py`, `backend_service/app/api/topics.py`, `backend_service/app/config.py`, and Kafka support modules, with shared contracts in `project/schemas.py` (including `UserRequest`) and topic registry in `project/topics.py`. For the WebSocket channel, add `project/events.py` (shared event names and body schemas), `backend_service/app/connection_manager.py` (simple `ConnectionManager` with get/set keyed by `session_id`), and `backend_service/app/socket.py` (Socket.IO server instance, lightweight listeners, and `emit_event`). The Socket.IO ASGI app is mounted onto the FastAPI app in `main.py`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
