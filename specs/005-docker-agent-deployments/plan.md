# Implementation Plan: Docker Agent Deployments

**Branch**: `007-dockerize-agents` | **Date**: 2026-06-15 | **Spec**: `/specs/005-docker-agent-deployments/spec.md`
**Input**: Feature specification from `/specs/005-docker-agent-deployments/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Containerize all in-scope runtime components with per-directory Dockerfiles and
compose-managed build entries. Keep one-command local startup, enforce restart behavior,
add healthchecks for `kafka` and `backend-service`, gate agents on both healthy
dependencies, mount a shared uploads volume between backend and RAG so backend file paths
remain valid for RAG reads, and standardize Kafka client log level at warning for each
agent and service.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, kafka-python, docker compose, agent-specific Python dependencies from `requirements.txt`  
**Storage**: Filesystem shared volume for uploads (`backend-service` <-> `rag-agent`), no new database  
**Testing**: docker compose config validation, image build checks, startup/health/dependency smoke checks, shared-volume path readability checks  
**Target Platform**: Linux container runtime with Docker Compose  
**Project Type**: Multi-service backend (Python agents + backend API + Kafka infra)  
**Performance Goals**: Full stack starts with healthy required services; per-service image build under 3 minutes on standard dev hardware  
**Constraints**: Healthchecks required only for `kafka` and `backend-service`; all agents depend on both; uploads paths must be valid across backend and RAG containers; Kafka logger level warning for each in-scope service  
**Scale/Scope**: 6 application services (backend_service, orchestrator_agent, planner_agent, rag_agent, teaching_agent, quiz_agent) plus infrastructure services (`kafka`, `kafka-ui`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: PASS. Changes are constrained to deployment/runtime configuration and service entrypoint logging setup; existing Python quality gates remain applicable.
- Testing Gate: PASS. Verification includes compose config, build checks, health/dependency gating checks, shared-volume readability checks, and restart smoke checks.
- UX Consistency Gate: PASS (no user-facing UX changes).
- Performance Gate: PASS. Measurable startup and build budgets are defined in specification criteria and quickstart validations.
- Maintainability Gate: PASS. Contracts and quickstart explicitly document service mapping, readiness dependencies, shared volume contract, and logging-level policy.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
```text
backend_service/
  app/
  tests/
orchestrator_agent/
  tests/
planner_agent/
  tests/
rag_agent/
  tests/
teaching_agent/
  tests/
quiz_agent/
  tests/
project/
utils/
docker-compose.yaml
requirements.txt
specs/005-docker-agent-deployments/
```

**Structure Decision**: Preserve current multi-service repository layout and implement deployment/runtime configuration changes in-place (Dockerfiles, compose, service worker logging settings, and spec artifacts).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Post-Design Constitution Check

- Code Quality Gate: PASS. Design minimizes churn and scopes edits to deployment and service runtime configuration.
- Testing Gate: PASS. Design provides deterministic validation points for healthchecks, dependencies, shared volume readability, and restart behavior.
- UX Consistency Gate: PASS. No user-interface behavior is altered.
- Performance Gate: PASS. Startup and build budgets remain measurable and validated in quickstart.
- Maintainability Gate: PASS. Added contracts for volume mapping and Kafka logging policy improve operational clarity.
