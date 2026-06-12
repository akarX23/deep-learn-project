# Implementation Plan: Backend Kafka Startup Bootstrap + RAG Test-Event API

**Branch**: `003-integrate-kafka-backend` | **Date**: 2026-06-12 | **Spec**: `specs/003-integrate-kafka-backend/spec.md`
**Input**: Feature specification from `/specs/003-integrate-kafka-backend/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Extend the backend service startup lifecycle to create Kafka topics from `project/topics` idempotently, and add a gated test-event API for topic `rag` that publishes a `RAGRequestEvent` payload using hybrid defaults+overrides. The API returns a normalized publish result that includes Kafka metadata when available. Implementation will keep advanced validation and resilience logic as TODO-marked follow-ups while satisfying current observability and performance budgets.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Pydantic v2, kafka-python, python-dotenv  
**Storage**: N/A (Kafka is external messaging infrastructure, not app-owned storage)  
**Testing**: pytest (unit + integration-like API and startup tests)  
**Target Platform**: Linux backend service runtime (local docker-compose + CI Linux)
**Project Type**: Backend web service (FastAPI + Kafka integration)  
**Performance Goals**: Startup topic bootstrap <= 5s in local dev cluster; rag test-event publish response <= 2s p95 in local dev cluster  
**Constraints**: Synchronous implementation; idempotent topic creation; test-event APIs enabled by default in dev/test, explicit opt-in in production; no direct agent invocation from API  
**Scale/Scope**: Current registry includes `rag` and `rag-complete`; immediate scope adds one topic-specific test publish route (`rag`) with extensible per-topic routing pattern

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: Pass `ruff check project backend_service` and `ruff format --check project backend_service`; fail the feature if either check fails.
- Testing Gate: Add/maintain tests for startup bootstrap path, route env-gating behavior, request validation against `RAGRequestEvent`, and publish response envelope/metadata behavior; run `pytest backend_service/tests -q`.
- UX Consistency Gate: API response patterns must remain consistent with existing backend JSON envelope conventions (`status`, typed response body, explicit error message) and deterministic HTTP status usage.
- Performance Gate: Verify bootstrap summary timing under local Kafka is <= 5s and rag test-event request/response path stays within <= 2s p95 under local single-request testing.
- Maintainability Gate: Keep route wiring in `create_app`, schema contracts in `project/schemas.py`, and add explicit logging at startup/publish boundaries.

Post-Design Re-check (Phase 1): PASS
- No constitution violations introduced by selected design.
- All gates have corresponding implementation/test artifacts planned in Phase 2.

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
│   └── backend-topic-bootstrap-contract.md
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
│   └── main.py
└── tests/
  ├── test_startup.py
  └── test_topics_api.py

project/
├── schemas.py
└── topics.py
```

**Structure Decision**: Keep the existing backend service FastAPI structure and add feature behavior by extending `backend_service/app/main.py`, `backend_service/app/api/topics.py`, `backend_service/app/config.py`, and Kafka support modules, with shared contracts in `project/schemas.py` and topic registry in `project/topics.py`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
