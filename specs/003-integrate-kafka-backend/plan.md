# Implementation Plan: Kafka Backend Integration Service

**Branch**: `[003-integrate-kafka-backend]` | **Date**: 2026-06-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-integrate-kafka-backend/spec.md`

## Summary

Deliver a dedicated FastAPI backend service that initializes Kafka admin connectivity during lifespan startup, retries with env-driven controls, and exposes one topic-creation endpoint with a unified error envelope. Local bootstrap is standardized with root compose services for Kafka and Kafka UI, with Kafka pinned to `apache/kafka:4.2.1` and Kafka UI connected to the broker service.

## Technical Context

**Language/Version**: Python 3.12.x
**Primary Dependencies**: FastAPI, Uvicorn, kafka-python, Pydantic v2, python-dotenv
**Storage**: N/A (stateless service; Kafka metadata managed via broker admin API)
**Testing**: pytest + fastapi.testclient
**Target Platform**: Linux containers for local development; Linux host runtime for service
**Project Type**: Backend web service
**Performance Goals**:
- Topic-create API p95 <= 2s in local development (SC-003)
- Local compose startup to reachable Kafka + Kafka UI under 2 minutes (SC-006)
**Constraints**:
- Use FastAPI lifespan only; no deprecated `on_event` handlers (FR-014)
- Use unified global exception envelope for validation, HTTP, and unhandled failures (FR-015)
- Kafka image fixed to `apache/kafka:4.2.1` in compose contract (FR-010)
**Scale/Scope**:
- One backend service
- One API endpoint (`POST /api/v1/topics`)
- One local Kafka cluster target per service instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- Code Quality Gate: PASS
- Define `ruff check`, `ruff format --check`, and `python -m compileall backend_service` as mandatory checks before completion evidence.
- Testing Gate: PASS
- Require unit/integration tests for startup retry behavior, shutdown cleanup, API success/duplicate/validation/runtime paths, and contract-shaped error responses.
- UX Consistency Gate: PASS
- Enforce one response envelope shape for failure paths and deterministic status values for success paths (`created`, `already_exists`, `error`).
- Performance Gate: PASS
- Track startup retry timing and topic-create latency in quickstart evidence; keep topic p95 budget <= 2s and compose bootstrap target under 2 minutes.
- Maintainability Gate: PASS
- Require startup diagnostics, explicit lifecycle orchestration, and synchronized docs/contracts for env, API, and compose behavior.

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
requirements.txt
```

**Structure Decision**: Keep a single backend-service package (`backend_service/`) with explicit API, config, and Kafka admin modules, and maintain feature artifacts in `specs/003-integrate-kafka-backend/`.

## Phase 0: Research Outcomes

Research decisions are documented in [research.md](./research.md) and resolve all technical unknowns from the template baseline:

- Kafka admin library: `kafka-python` `KafkaAdminClient`
- Lifecycle orchestration: FastAPI lifespan startup/shutdown
- Env precedence: `.env.local` base + process-env override
- API scope: topic creation only
- Local infra topology: Kafka + Kafka UI with Kafka pinned to `apache/kafka:4.2.1`
- Error strategy: global exception handlers returning one envelope shape
- Retry model: env-driven retry count + timeout with strict validation

No unresolved `NEEDS CLARIFICATION` items remain.

## Phase 1: Design & Contracts

### Data Model Output

- [data-model.md](./data-model.md) defines:
- Runtime config (`KafkaConnectionConfig`)
- Startup lifecycle state (`StartupConnectionState`)
- API request/result/error envelope (`TopicCreateRequest`, `TopicCreateResult`, `ApiErrorResponse`)
- Compose topology contract entity (`ComposeServiceConfig`) including fixed Kafka image tag

### Contract Output

- [contracts/backend-topic-api-contract.md](./contracts/backend-topic-api-contract.md) defines:
- Runtime env contract and precedence
- `POST /api/v1/topics` request/response/error behavior
- Lifespan startup/shutdown contract
- Local compose infrastructure contract with `apache/kafka:4.2.1` + Kafka UI connectivity

### Quickstart Output

- [quickstart.md](./quickstart.md) defines local setup, service run flow, API usage, testing, and quality/performance validation commands.

### Agent Context Update

- `.github/copilot-instructions.md` already references `specs/003-integrate-kafka-backend/plan.md` inside both SPECKIT marker blocks; no path update required.

## Post-Design Constitution Check

- Code Quality Gate: PASS
- Quality checks and evidence commands are captured in quickstart and aligned with implementation tasks.
- Testing Gate: PASS
- Independent test scenarios from all three user stories map to existing backend test modules and contract behaviors.
- UX Consistency Gate: PASS
- Contract and quickstart preserve one failure envelope and deterministic response semantics.
- Performance Gate: PASS
- Budgets are explicitly carried from spec to plan and verification notes.
- Maintainability Gate: PASS
- Design keeps narrow service scope, explicit lifecycle behavior, and synchronized artifacts.

## Complexity Tracking

No constitution violations or justified complexity exceptions identified at planning time.
