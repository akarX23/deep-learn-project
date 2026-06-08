# Implementation Plan: Kafka Backend Integration Service

**Branch**: `[003-integrate-kafka-backend]` | **Date**: 2026-06-08 | **Spec**: `/specs/003-integrate-kafka-backend/spec.md`
**Input**: Feature specification from `/specs/003-integrate-kafka-backend/spec.md`

## Summary

Deliver a root-level FastAPI backend service that initializes Kafka admin connectivity during application startup and performs resource cleanup at shutdown using FastAPI lifespan events only (no deprecated `on_event` handlers). Provide a single topic-creation endpoint with deterministic outcomes and a unified error envelope across validation, HTTP, and unhandled failures. Keep local developer bootstrap simple with root-level Docker Compose for Kafka + Kafka UI and aligned environment examples.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Uvicorn, kafka-python (`KafkaAdminClient`), pydantic, python-dotenv  
**Storage**: N/A  
**Testing**: pytest, FastAPI TestClient, mock admin adapters  
**Target Platform**: Linux local/dev and CI  
**Project Type**: Backend microservice (`backend_service/`)  
**Performance Goals**: Topic-create API p95 <= 2s in local conditions; startup retry behavior completes within configured attempt/time budget  
**Constraints**: Topic-create route only; `.env.local` defaults with process-env override; FastAPI lifespan-only lifecycle orchestration; unified structured error envelope for 422/HTTP/unhandled errors; avoid deprecated framework APIs  
**Scale/Scope**: One Kafka cluster target per backend service instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- Code Quality Gate: PASS. Architecture separates config, Kafka admin adapter, API, and app boundary; lifecycle design explicitly avoids deprecated FastAPI handlers.
- Testing Gate: PASS. Planned coverage includes startup success/failure/retry, shutdown cleanup, endpoint outcomes, and global exception-envelope behavior.
- UX Consistency Gate: PASS. API success and error response envelopes are standardized and contract-bound.
- Performance Gate: PASS. Startup and endpoint latency budgets are explicit and measurable.
- Maintainability Gate: PASS. Diagnostics and rationale are captured, and lifecycle behavior is centralized at app boundary.

## Phase 0: Research

Research consolidated in `/specs/003-integrate-kafka-backend/research.md` covers:

- Kafka admin library selection and retry semantics.
- `.env.local` precedence model with process-env overrides.
- Docker Compose topology decisions for Kafka + Kafka UI.
- FastAPI lifespan-only lifecycle strategy (no deprecated lifecycle handlers).
- Global exception-envelope strategy for consistent API failures.

All clarified requirements are resolved; no `NEEDS CLARIFICATION` items remain.

## Phase 1: Design and Contracts

Phase 1 outputs:

- `/specs/003-integrate-kafka-backend/data-model.md`
- `/specs/003-integrate-kafka-backend/contracts/backend-topic-api-contract.md`
- `/specs/003-integrate-kafka-backend/quickstart.md`

Design highlights:

- `KafkaConnectionConfig` for runtime and retry controls.
- `StartupConnectionState` including shutdown cleanup transition.
- Single `POST /api/v1/topics` endpoint with deterministic created/already_exists outcomes.
- `ApiErrorResponse` contract for validation, HTTP, and unhandled failures.
- Lifespan-managed startup and shutdown lifecycle orchestration.

Agent context update:

- `.github/copilot-instructions.md` already points to `specs/003-integrate-kafka-backend/plan.md`.

## Post-Design Constitution Re-Check

- Code Quality Gate: PASS. Separation of concerns is preserved and deprecated API usage is disallowed by design.
- Testing Gate: PASS. Story-level tests map directly to lifecycle, endpoint, and error-envelope contracts.
- UX Consistency Gate: PASS. Predictable success/error payload structure is explicit and reusable.
- Performance Gate: PASS. Validation tasks and baseline capture are retained.
- Maintainability Gate: PASS. Non-obvious tradeoffs and operational behavior are documented.

## Project Structure

### Documentation (this feature)

```text
specs/003-integrate-kafka-backend/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── backend-topic-api-contract.md
└── tasks.md
```

### Source Code (repository root)

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

docker-compose.yaml
.env.example
.env.local.example
```

**Structure Decision**: Keep a dedicated root-level backend service and root-level infrastructure/bootstrap artifacts for clear operational ownership and easy local setup.

## Complexity Tracking

No constitution violations or justified exceptions.
