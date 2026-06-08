# Implementation Plan: Kafka Backend Integration Service

**Branch**: `[003-integrate-kafka-backend]` | **Date**: 2026-06-08 | **Spec**: `/specs/003-integrate-kafka-backend/spec.md`
**Input**: Feature specification from `/specs/003-integrate-kafka-backend/spec.md`

## Summary

Deliver a root-level FastAPI backend service that establishes Kafka admin connectivity during lifecycle-managed startup, cleans up resources at shutdown, and exposes a single topic-creation endpoint. Add unified global exception handling (validation, HTTP, and unhandled) with a consistent error payload shape. Provide root-level Docker Compose for Kafka plus Kafka UI and aligned environment examples.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Uvicorn, kafka-python (`KafkaAdminClient`), pydantic, python-dotenv  
**Storage**: N/A  
**Testing**: pytest, FastAPI TestClient, mock admin adapters  
**Target Platform**: Linux local/dev and CI  
**Project Type**: Backend microservice (`backend_service/`)  
**Performance Goals**: Topic-creation API p95 <= 2s in local conditions; startup retry behavior completes within configured attempt/time budget  
**Constraints**: Topic-creation route only; load `.env.local` when present and allow process env override; lifecycle-managed startup/shutdown; unified structured error envelope for 422/HTTP/unhandled errors  
**Scale/Scope**: One Kafka cluster target per backend service instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- Code Quality Gate: PASS. Layered module layout (`config`, `kafka_admin`, `api`, `main`) with explicit boundaries and clear naming.
- Testing Gate: PASS. Coverage includes startup success/failure/retry paths, API success/exists/validation/runtime error paths, and local infrastructure expectations.
- UX Consistency Gate: PASS. Response format standardized across success and all handled error paths.
- Performance Gate: PASS. Startup retry budget and topic-create latency budget are measurable and tracked.
- Maintainability Gate: PASS. Startup diagnostics and documented decisions in research/contracts/quickstart are included.

## Phase 0: Research

Research outcomes are recorded in `/specs/003-integrate-kafka-backend/research.md` and resolve all clarifications:

- Kafka admin library choice and startup retry strategy.
- `.env.local` plus process-env precedence.
- Docker Compose topology with Kafka UI.
- Global FastAPI exception handling strategy and unified error shape.
- Lifecycle-managed startup and shutdown approach.

No `NEEDS CLARIFICATION` items remain.

## Phase 1: Design and Contracts

Phase 1 outputs:

- `/specs/003-integrate-kafka-backend/data-model.md`
- `/specs/003-integrate-kafka-backend/contracts/backend-topic-api-contract.md`
- `/specs/003-integrate-kafka-backend/quickstart.md`

Design highlights:

- Configuration entity for Kafka connectivity and retry settings.
- Startup state model for retry attempts and terminal failure.
- API contract for `POST /api/v1/topics` with deterministic `created` and `already_exists` outcomes.
- Unified error response entity and contract for validation, HTTP, and unhandled exceptions.
- Lifecycle event requirement for startup initialization and shutdown cleanup.

Agent context update:

- `.github/copilot-instructions.md` points to `specs/003-integrate-kafka-backend/plan.md`.

## Post-Design Constitution Re-Check

- Code Quality Gate: PASS. Design artifacts align with modular structure and bounded responsibilities.
- Testing Gate: PASS. Independent, automatable tests cover startup, endpoint behavior, and exception contract consistency.
- UX Consistency Gate: PASS. Unified error payload and predictable success payload are documented.
- Performance Gate: PASS. Local baseline and budgets are documented with reproducible measurement approach.
- Maintainability Gate: PASS. Non-obvious tradeoffs and diagnostics expectations are recorded.

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

**Structure Decision**: Use a dedicated root-level microservice folder and root-level local infrastructure artifacts to keep deployment/bootstrap concerns explicit and isolated from existing agent modules.

## Complexity Tracking

No constitution violations or justified complexity exceptions.
