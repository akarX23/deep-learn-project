# Implementation Plan: Docker Agent Deployments

**Branch**: `007-dockerize-agents` | **Date**: 2026-06-15 | **Spec**: `/specs/005-docker-agent-deployments/spec.md`
**Input**: Feature specification from `/specs/005-docker-agent-deployments/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Containerize all in-scope local runtime components (backend service and all agent services)
with per-directory Dockerfiles and compose-managed build entries. Keep a single compose
entrypoint for full-stack startup, support independent service image builds, enforce
restart behavior for every in-scope service, add healthchecks to `kafka` and
`backend-service`, and gate remaining agent services on both healthy dependencies.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI (backend service), kafka-python clients, agent-specific Python dependencies from `requirements.txt`  
**Storage**: N/A (feature is deployment packaging/orchestration, no new datastore)  
**Testing**: docker compose config validation, service image build verification, runtime smoke checks for health/dependency gating and restart behavior  
**Target Platform**: Linux container runtime with Docker Compose  
**Project Type**: Multi-service backend (Python agents + backend API + Kafka infra)  
**Performance Goals**: Full local stack startup command succeeds with all in-scope services reaching running state; per-service build completes under 3 minutes on standard dev hardware  
**Constraints**: Healthchecks required only for `kafka` and `backend-service`; all agent services must depend on both; all in-scope services must be restartable  
**Scale/Scope**: 6 application services (backend_service, orchestrator_agent, planner_agent, rag_agent, teaching_agent, quiz_agent) plus existing infrastructure services in compose

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Code Quality Gate: PASS. Changes are constrained to Dockerfiles, compose definitions, and related docs; Python quality gates remain unchanged and must still pass in CI.
- Testing Gate: PASS. Required verification includes compose parse validation, per-service build checks, healthcheck/dependency gating checks, and runtime restart smoke checks.
- UX Consistency Gate: PASS (not user-interface impacting). Existing frontend interaction/accessibility patterns are unaffected.
- Performance Gate: PASS. Measurable budgets defined as stack startup completion and independent service build time threshold (<3 minutes).
- Maintainability Gate: PASS. Standardized Dockerfile pattern and explicit compose service naming/dependency contracts are documented in contracts/quickstart.

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

**Structure Decision**: Existing multi-service Python repository structure is retained.
This feature adds deployment artifacts (Dockerfiles and compose service entries) in-place
within each service directory and central compose orchestration at repository root.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Post-Design Constitution Check

- Code Quality Gate: PASS. Design keeps changes isolated to deployment artifacts with no non-essential architecture churn.
- Testing Gate: PASS. Design includes explicit verification strategy for compose configuration, image builds, health/dependency gating, and restart behavior checks.
- UX Consistency Gate: PASS. Feature does not alter user-facing UX pathways.
- Performance Gate: PASS. Design encodes measurable startup/build budgets defined in specification criteria.
- Maintainability Gate: PASS. Contracts and quickstart define repeatable service naming/build/restart/healthcheck/dependency conventions.
