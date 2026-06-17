# Implementation Plan: Docker Agent Deployments

**Branch**: `007-dockerize-agents` | **Date**: 2026-06-17 | **Spec**: `/specs/005-docker-agent-deployments/spec.md`
**Input**: Feature specification from `/specs/005-docker-agent-deployments/spec.md`

## Summary

Add or complete per-directory Dockerfiles for the Python backend and agent services plus the Streamlit UI frontend, then wire each component into `docker-compose.yaml` as an independently buildable, restartable local service. Preserve the existing Kafka-backed local stack, keep `kafka` and `backend-service` as the only health-gated dependencies, reuse `.env.local` for runtime configuration, and expose the UI frontend through a browser-accessible Streamlit container.

## Technical Context

**Language/Version**: Python 3.11 for all application services and the UI frontend  
**Primary Dependencies**: FastAPI, Uvicorn, kafka-python/Kafka clients, Streamlit, requests, Pydantic, project-shared schemas  
**Storage**: Local filesystem uploads mount (`uploads/`) plus Kafka topics; no database changes  
**Testing**: `pytest`, targeted compose validation (`docker compose config`), per-service image builds, stack smoke checks  
**Target Platform**: Linux-based local Docker/Compose development environment  
**Project Type**: Multi-service backend plus browser-accessed Streamlit frontend  
**Performance Goals**: Single-service image build under 3 minutes on a standard dev machine; UI reachable after stack startup; full stack starts from one compose command  
**Constraints**: `kafka` and `backend-service` remain the only health-checked dependencies, every in-scope service uses `restart: unless-stopped`, backend/RAG uploads path must stay readable across containers, UI runtime depends on required env vars being present  
**Scale/Scope**: 7 in-scope application components (`backend_service`, `orchestrator_agent`, `planner_agent`, `rag_agent`, `teaching_agent`, `quiz_agent`, `ui_frontend`) plus existing local infrastructure services (`kafka`, `kafka-ui`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: Limited to deployment asset changes (`Dockerfile`s, `docker-compose.yaml`, env contract updates, and small startup adjustments where logging policy is missing). Validation requires `docker compose config` plus targeted code review for consistent build/runtime patterns.
- Testing Gate: Implementation must add or update automated tests where runtime startup code changes, and must include executable deployment validation: compose config render, targeted image builds, full-stack smoke startup, dependency gating checks, restart-policy smoke, and UI reachability verification.
- UX Consistency Gate: The UI frontend must continue to use the existing Streamlit interaction flow and fail with clear, user-visible configuration errors when required env vars are missing. No new UI interaction model is introduced.
- Performance Gate: Maintain SC-004 by validating independent image builds under 3 minutes and verify stack startup remains a one-command local flow without extra manual bootstrapping.
- Maintainability Gate: Keep one Dockerfile per component directory, preserve one-to-one service-to-directory mapping in compose, document the env contract in planning artifacts, and avoid introducing custom wrapper scripts when direct module entrypoints are already present.

Post-design re-check: PASS. The design keeps the solution at the compose/Dockerfile layer, reuses existing application entrypoints, documents the UI env contract, and defines concrete validation evidence for quality, testing, UX, performance, and maintainability.

## Project Structure

### Documentation (this feature)

```text
specs/005-docker-agent-deployments/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── deployment-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
backend_service/
├── Dockerfile
├── app/
└── tests/

orchestrator_agent/
├── Dockerfile
├── worker.py
└── tests/

planner_agent/
├── Dockerfile
├── worker.py
└── tests/

rag_agent/
├── Dockerfile
├── worker.py
└── tests/

teaching_agent/
├── Dockerfile
├── worker.py
└── tests/

quiz_agent/
├── Dockerfile
├── worker.py
└── tests/

ui_frontend/
├── Dockerfile
├── app.py
├── config.py
└── tests/

project/
├── schemas.py
├── topics.py
└── events.py

docker-compose.yaml
requirements.txt
uploads/
```

**Structure Decision**: Keep the existing multi-directory Python service layout. Each in-scope component owns its Dockerfile, while `docker-compose.yaml` at repo root remains the single source of truth for local orchestration. Shared code continues to live in `project/`, and the existing `uploads/` directory remains the host-backed volume shared by backend and RAG.

## Phase 0: Research Summary

Research is complete in `/specs/005-docker-agent-deployments/research.md`.

- One Dockerfile per component remains the selected pattern because it preserves discoverability and independent builds.
- Compose continues to use repository-root build contexts with explicit service Dockerfile paths so component builds can copy shared modules without extra packaging work.
- `kafka` and `backend-service` remain the only health-gated dependencies; all agents depend on both, and the UI frontend depends on healthy `backend-service`.
- The UI frontend is treated as a first-class compose service using the existing Streamlit entrypoint and env-driven configuration (`UI_WEBSOCKET_URL`, `UI_BACKEND_URL`, `UI_SIMULATOR_ENABLED`).
- `.env.local` remains the runtime env source today; implementation should also add or align `.env.local.example` so the documented UI env contract is discoverable.

## Phase 1: Design Artifacts

- Data model: `/specs/005-docker-agent-deployments/data-model.md`
- Deployment contract: `/specs/005-docker-agent-deployments/contracts/deployment-contract.md`
- Quickstart and validation flow: `/specs/005-docker-agent-deployments/quickstart.md`
- Agent context reference: `.github/copilot-instructions.md` already points to `/specs/005-docker-agent-deployments/plan.md`; no path change required.

## Implementation Direction

1. Normalize Dockerfiles across all in-scope directories, including `ui_frontend/`.
2. Update `docker-compose.yaml` so every in-scope component has an active, buildable service entry with `restart: unless-stopped`.
3. Keep `kafka` and `backend-service` healthchecks; gate all agent services on both and gate the UI frontend on healthy `backend-service`.
4. Pass service env vars from `.env.local`, and add `.env.local.example` coverage during implementation if it is still missing.
5. Preserve the shared uploads mount between backend and RAG.
6. Verify logging-policy requirements in any touched service runtime code where Kafka or LiteLLM warning-level setup is currently missing.

## Complexity Tracking

No constitution violations or justified complexity exceptions are required for this plan.
