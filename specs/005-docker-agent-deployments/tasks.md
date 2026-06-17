# Tasks: Docker Agent Deployments

**Input**: Design documents from `/specs/005-docker-agent-deployments/`
**Branch**: `007-dockerize-agents`
**Prerequisites**: `plan.md` ✅ · `spec.md` ✅ · `research.md` ✅ · `data-model.md` ✅ · `contracts/deployment-contract.md` ✅ · `quickstart.md` ✅

**Tests**: This feature does not require new unit/integration test code. Validation tasks use deployment commands and evidence capture.

**Organization**: Tasks are grouped by user story. `[X]` = completed; `[ ]` = remaining work.

## Current Gap Summary (as of 2026-06-17)

| Gap | Affected Task(s) |
|---|---|
| `quiz_agent/worker.py` missing Kafka + LiteLLM logging policy | T040 |
| `planner-agent` service commented out in `docker-compose.yaml` | T041 |
| `ui_frontend/Dockerfile` does not exist | T042 |
| `ui-frontend` compose service missing from `docker-compose.yaml` | T043 |
| `UI_BACKEND_URL` missing from `.env.local.example` | T044 |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align feature artifacts and confirm the in-scope service list.

- [X] T001 Confirm in-scope service inventory and canonical names in specs/005-docker-agent-deployments/spec.md
- [X] T002 Align service-to-directory mapping table with implementation targets in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [X] T003 [P] Align quickstart commands with canonical compose service keys in specs/005-docker-agent-deployments/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cross-cutting fixes required before any user story can be fully validated.

**⚠️ CRITICAL**: Both open tasks below block US1 and US4 validation.

- [X] T004 Define all in-scope application service blocks with build stanzas in docker-compose.yaml
- [X] T005 Configure restart policy baseline for all in-scope services in docker-compose.yaml
- [X] T006 Preserve Kafka and Kafka UI infrastructure compatibility in docker-compose.yaml
- [X] T007 [P] Set host networking mode consistently for all services in docker-compose.yaml
- [X] T040 [P] Add `logging.getLogger("kafka").setLevel(logging.WARNING)` and `logging.getLogger("LiteLLM").setLevel(logging.WARNING)` to `quiz_agent/worker.py` immediately after the `logger = logging.getLogger(__name__)` line (all other worker.py files already have this; quiz_agent/agent.py has it but worker.py does not — FR-013, FR-014, SC-009, SC-010)
- [X] T044 [P] Add `UI_BACKEND_URL=http://localhost:8001` under the `# === UI Frontend ===` section in `.env.local.example` (`UIConfig.from_env()` raises `RuntimeError` if this var is absent; it is currently missing from the example file — FR-018)

**Checkpoint**: Logging policy complete across all workers; UI env contract fully documented.

---

## Phase 3: User Story 1 — Run All Components Locally via Compose (Priority: P1) 🎯 MVP

**Goal**: Every in-scope Python backend/agent service is active in compose and the full backend stack starts from `docker compose up -d`.

**Independent Test**: `docker compose up -d` → `docker compose ps` shows all 7 backend services running or restarting; `kafka` and `backend-service` report healthy.

### Implementation for User Story 1 (previously completed)

- [X] T008 [P] [US1] Create Docker build definition in backend_service/Dockerfile
- [X] T009 [P] [US1] Create Docker build definition in orchestrator_agent/Dockerfile
- [X] T010 [P] [US1] Create Docker build definition in planner_agent/Dockerfile
- [X] T011 [P] [US1] Create Docker build definition in rag_agent/Dockerfile
- [X] T012 [P] [US1] Create Docker build definition in teaching_agent/Dockerfile
- [X] T013 [P] [US1] Create Docker build definition in quiz_agent/Dockerfile
- [X] T014 [US1] Add healthchecks for kafka and backend-service in docker-compose.yaml
- [X] T015 [US1] Add health-aware depends_on links from each agent to kafka and backend-service in docker-compose.yaml
- [X] T016 [US1] Add shared uploads volume mapping between backend-service and rag-agent in docker-compose.yaml
- [X] T017 [US1] Document uploads path compatibility validation steps in specs/005-docker-agent-deployments/quickstart.md
- [X] T018 [US1] Document health/dependency startup validation workflow in specs/005-docker-agent-deployments/quickstart.md

### Remaining Implementation for User Story 1

- [X] T041 [US1] Uncomment and activate the `planner-agent` service block in `docker-compose.yaml` (currently fully commented out; must match the standard pattern: `image: deep-learn/planner-agent:local`, `build.context: .`, `build.dockerfile: planner_agent/Dockerfile`, `network_mode: host`, `restart: unless-stopped`, `depends_on` with `kafka: condition: service_healthy` and `backend-service: condition: service_healthy`, `env_file: [.env.local]`, `environment: PLANNER_KAFKA_BOOTSTRAP_SERVERS: ${PLANNER_KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}`) — FR-002, FR-005, FR-011

### Acceptance Checks for User Story 1

- [X] T045 [P] [US1] Run `docker compose config` and confirm it renders without errors — SC-002, SC-003
- [X] T046 [P] [US1] Run `docker compose build backend-service orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent` and confirm all 6 images build successfully — SC-002, SC-004
- [X] T047 [US1] Run `docker compose up -d` then `docker compose ps kafka backend-service orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent` and confirm `kafka` and `backend-service` are healthy and all agent services are running — SC-003, SC-005, SC-006, SC-007

**Checkpoint**: Full backend compose stack is active and all 6 Python service images build and run independently.

---

## Phase 4: User Story 4 — Run UI Frontend via Compose (Priority: P2)

**Goal**: The Streamlit UI frontend has a Dockerfile and an active compose service so the full application is available from one compose command.

**Independent Test**: After `docker compose up -d`, opening `http://localhost:8501` shows the AI Tutor Streamlit interface. Stopping the container triggers automatic restart.

### Implementation for User Story 4

- [X] T042 [US4] Create `ui_frontend/Dockerfile`:
  - Base image `python:3.11-slim`
  - `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1`
  - `WORKDIR /app`
  - Copy `requirements.txt` → `pip install -r requirements.txt`
  - Copy `project/` → `/app/project/`
  - Copy `ui_frontend/` → `/app/ui_frontend/`
  - `EXPOSE 8501`
  - `CMD ["streamlit", "run", "ui_frontend/app.py", "--server.headless=true", "--server.port=8501", "--server.address=0.0.0.0"]`
  — FR-015, FR-019

- [X] T043 [US4] Add `ui-frontend` service to `docker-compose.yaml` after the `quiz-agent` block:
  ```yaml
  ui-frontend:
    image: deep-learn/ui-frontend:local
    build:
      context: .
      dockerfile: ui_frontend/Dockerfile
    network_mode: host
    restart: unless-stopped
    depends_on:
      backend-service:
        condition: service_healthy
    env_file:
      - .env.local
  ```
  — FR-016, FR-017, FR-018, FR-019, FR-020

### Acceptance Checks for User Story 4

- [X] T048 [P] [US4] Run `docker compose build ui-frontend` and confirm the image builds successfully — SC-001, SC-004
- [X] T049 [P] [US4] Run `docker compose up -d ui-frontend` then open `http://localhost:8501` in a browser and confirm the Streamlit AI Tutor interface loads — SC-011
- [X] T050 [US4] Temporarily remove `UI_BACKEND_URL` from `.env.local`, restart the container, confirm the app displays a clear `RuntimeError` config message instead of silently failing, then restore the value — FR-018 edge case

**Checkpoint**: UI frontend is containerized, browser-accessible, and validates its env contract visibly at startup.

---

## Phase 5: User Story 2 — Build Each Component Independently (Priority: P2)

**Goal**: Any single service image rebuilds without triggering other builds.

**Independent Test**: Each `docker compose build <service>` command in the matrix succeeds in isolation.

### Implementation for User Story 2 (previously completed)

- [X] T019 [US2] Define explicit build context and dockerfile mapping for each in-scope service in docker-compose.yaml
- [X] T020 [US2] Define stable image naming/tagging for each in-scope service in docker-compose.yaml
- [X] T021 [US2] Add independent build acceptance checks for each service in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [X] T022 [US2] Add per-service build command matrix in specs/005-docker-agent-deployments/quickstart.md
- [X] T023 [US2] Add single-service build timing validation notes for SC-004 in specs/005-docker-agent-deployments/quickstart.md

### Acceptance Checks for User Story 2

- [X] T051 [P] [US2] Validate per-service independent builds for all 7 in-scope services by running each command from the build matrix and confirming only that service is rebuilt — SC-004, FR-004:
  ```
  docker compose build backend-service
  docker compose build orchestrator-agent
  docker compose build planner-agent
  docker compose build rag-agent
  docker compose build teaching-agent
  docker compose build quiz-agent
  docker compose build ui-frontend
  ```

**Checkpoint**: All 7 services build independently in under 3 minutes each.

---

## Phase 6: User Story 3 — Standardized Container Setup (Priority: P3)

**Goal**: Every component directory has a Dockerfile following the standard pattern; every compose service entry is consistently configured.

**Independent Test**: Review all 7 directories and compose entries for `python:3.11-slim` base, `restart: unless-stopped`, appropriate `depends_on`, and `env_file` usage.

### Implementation for User Story 3 (previously completed)

- [X] T024 [P] [US3] Add Kafka warning-level logger configuration in backend_service/app/main.py
- [X] T025 [P] [US3] Add Kafka warning-level logger configuration in orchestrator_agent/worker.py
- [X] T026 [P] [US3] Add Kafka warning-level logger configuration in planner_agent/worker.py
- [X] T027 [P] [US3] Add Kafka warning-level logger configuration in rag_agent/worker.py
- [X] T028 [P] [US3] Add Kafka warning-level logger configuration in teaching_agent/worker.py
- [X] T029 [P] [US3] Add Kafka warning-level logger configuration in quiz_agent/agent.py
- [X] T030 [US3] Encode Kafka logging policy verification requirements in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [X] T031 [US3] Add Kafka logger policy verification checklist in specs/005-docker-agent-deployments/quickstart.md

### Acceptance Checks for User Story 3

- [X] T052 [P] [US3] Verify all 7 Dockerfiles (`backend_service/Dockerfile`, `orchestrator_agent/Dockerfile`, `planner_agent/Dockerfile`, `rag_agent/Dockerfile`, `teaching_agent/Dockerfile`, `quiz_agent/Dockerfile`, `ui_frontend/Dockerfile`) each use `python:3.11-slim` base, install from `requirements.txt`, copy `project/` shared package, and set the correct runtime `CMD` — FR-001, FR-015, SC-001
- [X] T053 [P] [US3] Verify all 7 compose service entries in `docker-compose.yaml` each have `restart: unless-stopped`, `env_file: [.env.local]`, `build.context: .` with explicit `build.dockerfile`, unique service name, and appropriate `depends_on` health conditions — FR-002, FR-005, FR-007, FR-008, SC-002, SC-005

**Checkpoint**: Consistent containerization pattern confirmed across all 7 components.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation, logging-policy audit, restart smoke test, and evidence capture.

- [X] T032 [P] Run compose schema validation and record results in specs/005-docker-agent-deployments/quickstart.md
- [X] T033 [P] Run full-stack build validation and record results in specs/005-docker-agent-deployments/quickstart.md
- [X] T034 [P] Run targeted build validation matrix and record results in specs/005-docker-agent-deployments/quickstart.md
- [X] T035 Run healthcheck and dependency-gating runtime validation and record evidence in specs/005-docker-agent-deployments/quickstart.md
- [X] T036 Run shared uploads readability validation and record evidence in specs/005-docker-agent-deployments/quickstart.md
- [X] T037 Run restart behavior smoke validation and record evidence in specs/005-docker-agent-deployments/quickstart.md
- [X] T038 Validate cross-artifact consistency across spec.md, plan.md, contracts/deployment-contract.md, and quickstart.md
- [X] T039 Add LiteLLM warning-level logging policy across LiteLLM-using services and document in contracts and quickstart
- [X] T054 [P] Run `grep -rn 'logging.getLogger("kafka").setLevel(logging.WARNING)' backend_service/ orchestrator_agent/ planner_agent/ rag_agent/ teaching_agent/ quiz_agent/` and confirm all 6 Kafka-using service startup paths match — SC-009, FR-013
- [X] T055 [P] Run `grep -rn 'logging.getLogger("LiteLLM").setLevel(logging.WARNING)' orchestrator_agent/ planner_agent/ rag_agent/ teaching_agent/ quiz_agent/` and confirm all 5 LiteLLM-using service startup paths match — SC-010, FR-014
- [X] T056 Stop one in-scope container abruptly (`docker compose exec -T <service> sh -lc "kill -9 1"`) and run `docker compose ps <service>` to confirm it recovers to `Up` via restart policy — SC-005, FR-005
- [X] T057 Update the `### Latest validation evidence` section in `specs/005-docker-agent-deployments/quickstart.md` with dated run results covering: compose config pass, full build including `ui-frontend`, targeted `ui-frontend` build, full stack startup including `planner-agent` and `ui-frontend`, browser UI check, restart smoke, and logging policy grep results

---

## Dependencies

```
T040 ──────────────────────────────── T054, T055 (logging audit)
T044 ──────────────────────────────── T050 (UI env edge case)
T041 ──── T045, T046, T047
T042 ──── T043 ──── T048, T049, T050
T041 + T042 + T043 ──── T051, T052, T053
T047 + T049 ───────────────────────── T056, T057
```

**User story completion order**:
1. Foundational (T040, T044) — unblocks everything; both parallelizable
2. US1 (T041, T045–T047) — MVP backend stack; T041 is the only new code change
3. US4 (T042–T043, T048–T050) — UI frontend; T042 and T043 are new code changes
4. US2 (T051) — build matrix validation; depends on US1 + US4 completion
5. US3 (T052–T053) — consistency review; can run after all files exist
6. Polish (T054–T057) — final validation and evidence capture

## Parallel Execution Examples

**Phase 2 foundational (independent of each other):**
```
T040 (quiz worker logging) ─── parallel with ─── T044 (env example)
```

**After T041 completes (planner-agent activated):**
```
T045 (compose config check) ─── parallel with ─── T046 (backend builds)
```

**After T042 + T043 complete (ui-frontend Dockerfile + compose):**
```
T048 (ui build check) ─── parallel with ─── T049 (browser check)
```

**After all services complete:**
```
T051 + T052 + T053 + T054 + T055 + T056 ─── all in parallel
```

## Implementation Strategy

**MVP Scope** (deliver first): Phase 2 (T040, T044) + Phase 3 (T041, T045–T047). Delivers the complete backend stack with logging policy corrected.

**Full Scope**: Add Phase 4 (T042–T043, T048–T050). Delivers the UI frontend containerization.

**Total tasks**: 57 (39 completed `[X]`, 18 remaining `[ ]`)  
**Open implementation tasks**: T040, T041, T042, T043, T044 (5 code/file changes)  
**Open acceptance/validation tasks**: T045–T057 (13 verification steps)  
**Parallel opportunities**: T040+T044 · T045+T046 · T048+T049 · T051+T052+T053+T054+T055+T056

---

## Notes

- `[P]` tasks touch different files with no direct cross-task dependency and can run concurrently.
- Story labels (`[US1]`, `[US2]`, `[US3]`, `[US4]`) appear only in user story phases.
- Every task includes an explicit file path and is actionable without additional context.
- With `network_mode: host`, Streamlit binds directly on the host — no Docker port mapping is needed; the UI is accessible at `http://localhost:8501` on the Docker host.
