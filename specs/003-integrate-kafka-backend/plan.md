# Implementation Plan: Backend Kafka Startup Topic Bootstrap

**Branch**: `001-build-rag-retrieval-agent` | **Date**: 2026-06-12 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/003-integrate-kafka-backend/spec.md`

## Summary

The backend service's FastAPI lifespan startup function must be extended to automatically create all Kafka topics listed in the shared `project/topics` registry immediately after Kafka admin connectivity is established. Topic creation is idempotent (already-existing topics are not errors), non-fatal on transient broker errors (log-and-continue), and limited to the core create-topics loop — advanced per-topic validation, result assertion, and health checks are deferred as explicit TODO markers. No new environment variables or configuration changes are required.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI 0.111+, kafka-python 2.0+, pydantic v2, python-dotenv  
**Storage**: N/A — topics are created in the external Kafka cluster; no local persistence  
**Testing**: pytest + `fastapi.testclient.TestClient`  
**Target Platform**: Linux server (local dev via Docker Compose)  
**Project Type**: Web service (`backend_service/`)  
**Performance Goals**: Startup topic bootstrap completes within 5 seconds against a local Kafka cluster (SC-003)  
**Constraints**: Bootstrap must be idempotent; non-fatal transient errors must not abort startup; no extra env vars introduced  
**Scale/Scope**: Creates ≤10 topics at startup; single-cluster target per service instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality Gate**: All changed files must pass `ruff check` and `ruff format --check` before merge. No dead code, no commented-out blocks, bounded function size.
- **Testing Gate**: New `bootstrap_topics()` method requires unit tests covering (a) all-new topics, (b) all-already-existing, (c) mixed, (d) empty registry, (e) transient error log-and-continue. Existing startup tests must continue to pass (regression gate).
- **UX Consistency Gate**: Startup log output follows existing `logger.info(...)` pattern in `main.py`. Error events use `logger.exception(...)` consistent with existing unhandled-error handler. No new API surface changes — this is startup-only.
- **Performance Gate**: Bootstrap step duration validated in unit test (mock clock or timing assertion) to confirm O(n) over topic count with no blocking beyond admin call. SC-003: ≤5s wall-clock target documented in quickstart.
- **Maintainability Gate**: TODO markers required in `bootstrap_topics()` per FR-006. Non-obvious decisions (idempotency via `TopicAlreadyExistsError` catch, non-fatal KafkaError handling) documented in research.md and code comments.

**Post-design re-check**: All gates still pass — no additional complexity introduced. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/003-integrate-kafka-backend/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── backend-topic-bootstrap-contract.md  # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (touched files)

```text
project/
└── topics.py                          # Add get_all_topic_names() aggregator

backend_service/
├── app/
│   ├── kafka_admin.py                 # Add bootstrap_topics() method
│   └── main.py                        # Extend lifespan: call bootstrap_topics() after connect()
└── tests/
    └── test_startup.py                # Add bootstrap_topics unit tests
```

**Structure Decision**: No new modules or packages needed. All changes are additive within existing files. The `project/topics` module is the single source-of-truth for topic names; `backend_service` imports it directly.

## Data Flow

```
FastAPI lifespan startup
  → KafkaSettings.from_env()
  → KafkaAdminService.connect()          # existing: retries, raises on exhaustion
  → get_all_topic_names()                # reads project/topics registry
  → KafkaAdminService.bootstrap_topics(topic_names)
      for each topic_name:
        create_topic(topic_name, num_partitions=1, replication_factor=1)
          → "created"           → log INFO
          → "already_exists"    → log DEBUG
          → RuntimeError        → log WARNING, continue  (non-fatal)
  → yield  (service is ready)
  → KafkaAdminService.close()           # existing shutdown
```
