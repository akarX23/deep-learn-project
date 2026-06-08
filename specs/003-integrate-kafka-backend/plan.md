# Implementation Plan: Kafka Backend Integration Service

**Branch**: `[003-integrate-kafka-backend]` | **Date**: 2026-06-08 | **Spec**: `/specs/003-integrate-kafka-backend/spec.md`
**Input**: Feature specification from `/specs/003-integrate-kafka-backend/spec.md`

## Summary

Create a new root-level FastAPI backend microservice that initializes Kafka admin connectivity at startup with environment-driven retries and exposes only topic-creation API capabilities. Add root-level Docker Compose infrastructure with Kafka and Kafka UI (`provectuslabs/kafka-ui:latest`) where Kafka UI is preconfigured to connect to the Kafka container.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, Uvicorn, kafka-python (KafkaAdminClient), pydantic-settings/python-dotenv, pytest  
**Storage**: N/A (Kafka metadata only; no application persistence database)  
**Testing**: pytest + FastAPI TestClient + mocked KafkaAdminClient and startup retry behavior  
**Target Platform**: Linux local/dev and CI; Docker Compose for local Kafka + Kafka UI bootstrap  
**Project Type**: Backend microservice in a new root folder (`backend_service/`)  
**Performance Goals**: Topic creation API p95 <= 2s in local dev conditions; startup retry handling remains within configured attempt/time budget  
**Constraints**: API scope restricted to topic creation; env load from `.env.local` with process env override; compose must include Kafka and Kafka UI only  
**Scale/Scope**: One cluster target per service instance, internal admin/provisioning utility for agents and microservices

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- Code Quality Gate: PASS. Proposed backend structure isolates config, Kafka admin adapter, and API routing with explicit typed boundaries.
- Testing Gate: PASS. Independent tests are planned for startup retries, input validation, duplicate topic behavior, and docker bootstrap assumptions.
- UX Consistency Gate: PASS. API responses are standardized (created/already_exists/error) with explicit error messaging expectations.
- Performance Gate: PASS. Startup retry and topic latency targets are measurable and mapped to spec success criteria.
- Maintainability Gate: PASS. Clear runtime configuration precedence and infrastructure docs reduce operational ambiguity.

## Phase 0: Research

Research consolidated in `/specs/003-integrate-kafka-backend/research.md` covers:

- Kafka admin client library selection and startup lifecycle handling.
- FastAPI startup retry strategy using env-controlled attempts/timeouts.
- Environment precedence (`.env.local` load + process environment override).
- Docker Compose topology with Kafka plus Kafka UI connectivity.

All clarified requirements are resolved; no `NEEDS CLARIFICATION` items remain.

## Phase 1: Design and Contracts

Phase 1 outputs:

- `/specs/003-integrate-kafka-backend/data-model.md`
- `/specs/003-integrate-kafka-backend/contracts/backend-topic-api-contract.md`
- `/specs/003-integrate-kafka-backend/quickstart.md`

Design highlights:

- Runtime `KafkaConnectionConfig` and `ComposeServiceConfig` entities.
- Startup state model for retry-based readiness.
- Single topic creation endpoint contract.
- Quickstart flow including Kafka UI verification.

Agent context update completed:

- `.github/copilot-instructions.md` points to `specs/003-integrate-kafka-backend/plan.md`.

## Post-Design Constitution Re-Check

- Code Quality Gate: PASS. Design artifacts enforce modular and typed service boundaries.
- Testing Gate: PASS. Story-level independent validation paths and contract checks are specified.
- UX Consistency Gate: PASS. API response and error format expectations are explicit and reusable.
- Performance Gate: PASS. Startup and API latency budgets are retained and testable.
- Maintainability Gate: PASS. Docker bootstrap and env precedence behavior are documented clearly.

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
.env.local
```

**Structure Decision**: Introduce an isolated backend service at root while keeping compose and environment artifacts at repository root for straightforward local bootstrap with Kafka and Kafka UI.

## Complexity Tracking

No constitution violations require exception tracking.
