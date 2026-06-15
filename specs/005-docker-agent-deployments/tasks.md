# Tasks: Docker Agent Deployments

**Input**: Design documents from `/specs/005-docker-agent-deployments/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: This feature does not require new unit/integration test code in the specification. Tasks include deployment validation commands and evidence capture in quickstart and contracts.

**Organization**: Tasks are grouped by user story for independent implementation and validation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align feature artifacts and identify the exact in-scope service list before implementation.

- [X] T001 Confirm in-scope service inventory and canonical names in specs/005-docker-agent-deployments/spec.md
- [X] T002 Align service-to-directory mapping table with implementation targets in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [X] T003 [P] Align quickstart commands with canonical compose service keys in specs/005-docker-agent-deployments/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish compose-wide baseline required before any user story tasks.

**CRITICAL**: No user story work should start until this phase is complete.

- [X] T004 Define all in-scope application service blocks with build stanzas in docker-compose.yaml
- [X] T005 Configure restart policy baseline for all in-scope services in docker-compose.yaml
- [X] T006 Preserve Kafka and Kafka UI infrastructure compatibility in docker-compose.yaml
- [X] T007 [P] Set host networking mode consistently for all services in docker-compose.yaml

**Checkpoint**: Compose foundation is ready for story-specific work.

---

## Phase 3: User Story 1 - Run all components locally via compose (Priority: P1) MVP

**Goal**: Start the full stack with one compose command, with health-aware startup gating and shared backend-RAG uploads readability.

**Independent Test**: Run `docker compose up -d`, verify `kafka` and `backend-service` become healthy, verify all agents start only after both are healthy, and verify backend upload paths are readable by RAG.

### Implementation for User Story 1

- [X] T008 [P] [US1] Create backend Docker build definition in backend_service/Dockerfile
- [X] T009 [P] [US1] Create orchestrator Docker build definition in orchestrator_agent/Dockerfile
- [X] T010 [P] [US1] Create planner Docker build definition in planner_agent/Dockerfile
- [X] T011 [P] [US1] Create RAG Docker build definition in rag_agent/Dockerfile
- [X] T012 [P] [US1] Create teaching Docker build definition in teaching_agent/Dockerfile
- [X] T013 [P] [US1] Create quiz Docker build definition in quiz_agent/Dockerfile
- [X] T014 [US1] Add healthchecks for kafka and backend-service in docker-compose.yaml
- [X] T015 [US1] Add health-aware depends_on links from each agent to kafka and backend-service in docker-compose.yaml
- [X] T016 [US1] Add shared uploads volume mapping between backend-service and rag-agent in docker-compose.yaml
- [X] T017 [US1] Document uploads path compatibility validation steps in specs/005-docker-agent-deployments/quickstart.md
- [X] T018 [US1] Document health/dependency startup validation workflow in specs/005-docker-agent-deployments/quickstart.md

**Checkpoint**: User Story 1 stack startup, readiness gating, and shared uploads access are independently verifiable.

---

## Phase 4: User Story 2 - Build each component independently (Priority: P2)

**Goal**: Support fast targeted builds for any single in-scope component.

**Independent Test**: Build any one service with `docker compose build <service>` and confirm only that target builds successfully.

### Implementation for User Story 2

- [X] T019 [US2] Define explicit build context and dockerfile mapping for each in-scope service in docker-compose.yaml
- [X] T020 [US2] Define stable image naming/tagging for each in-scope service in docker-compose.yaml
- [X] T021 [US2] Add independent build acceptance checks for each service in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [X] T022 [US2] Add per-service build command matrix in specs/005-docker-agent-deployments/quickstart.md
- [X] T023 [US2] Add single-service build timing validation notes for SC-004 in specs/005-docker-agent-deployments/quickstart.md

**Checkpoint**: User Story 2 independent-build workflow is complete and testable on its own.

---

## Phase 5: User Story 3 - Standardized container setup across components (Priority: P3)

**Goal**: Enforce consistent runtime conventions across all in-scope services.

**Independent Test**: Review startup files and compose definitions to confirm restart policy consistency, service naming consistency, and Kafka warning-level logging policy across Kafka-using services.

### Implementation for User Story 3

- [X] T024 [P] [US3] Add Kafka warning-level logger configuration in backend_service/app/main.py
- [X] T025 [P] [US3] Add Kafka warning-level logger configuration in orchestrator_agent/worker.py
- [X] T026 [P] [US3] Add Kafka warning-level logger configuration in planner_agent/worker.py
- [X] T027 [P] [US3] Add Kafka warning-level logger configuration in rag_agent/worker.py
- [X] T028 [P] [US3] Add Kafka warning-level logger configuration in teaching_agent/worker.py
- [X] T029 [P] [US3] Add Kafka warning-level logger configuration in quiz_agent/agent.py
- [X] T030 [US3] Encode Kafka logging policy verification requirements in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [X] T031 [US3] Add Kafka logger policy verification checklist in specs/005-docker-agent-deployments/quickstart.md

**Checkpoint**: User Story 3 standardization and Kafka logging policy are independently auditable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Perform final verification and keep all feature artifacts synchronized.

- [X] T032 [P] Run compose schema validation and record results in specs/005-docker-agent-deployments/quickstart.md
- [X] T033 [P] Run full-stack build validation and record results in specs/005-docker-agent-deployments/quickstart.md
- [X] T034 [P] Run targeted build validation matrix and record results in specs/005-docker-agent-deployments/quickstart.md
- [X] T035 Run healthcheck and dependency-gating runtime validation and record evidence in specs/005-docker-agent-deployments/quickstart.md
- [X] T036 Run shared uploads readability validation and record evidence in specs/005-docker-agent-deployments/quickstart.md
- [X] T037 Run restart behavior smoke validation and record evidence in specs/005-docker-agent-deployments/quickstart.md
- [X] T038 Validate cross-artifact consistency across specs/005-docker-agent-deployments/spec.md, specs/005-docker-agent-deployments/plan.md, specs/005-docker-agent-deployments/contracts/deployment-contract.md, and specs/005-docker-agent-deployments/quickstart.md
- [X] T039 Add LiteLLM warning-level logging policy across LiteLLM-using services and document it in specs/005-docker-agent-deployments/spec.md, specs/005-docker-agent-deployments/contracts/deployment-contract.md, and specs/005-docker-agent-deployments/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies.
- Foundational (Phase 2): depends on Setup completion and blocks all user story work.
- User Story phases (Phases 3-5): all depend on Foundational completion.
- Polish (Phase 6): depends on completion of selected user stories.

### User Story Dependencies

- User Story 1 (P1): can start after Phase 2; no dependency on other stories.
- User Story 2 (P2): can start after Phase 2 and compose service blocks are present.
- User Story 3 (P3): can start after Phase 2 and can run in parallel with User Story 2.

### Task Dependency Highlights

- T014 depends on T004.
- T015 depends on T004 and T014.
- T016 depends on T004.
- T017 depends on T016.
- T018 depends on T014 and T015.
- T020 depends on T019.
- T022 depends on T019.
- T023 depends on T022.
- T030 depends on T024-T029.
- T031 depends on T030.
- T032-T037 depend on T014-T023.

---

## Parallel Execution Examples

### User Story 1

- Parallel Dockerfile creation: T008, T009, T010, T011, T012, T013
- Sequential compose wiring: T014 -> T015 -> T016
- Documentation can parallelize after wiring: T017 and T018

### User Story 2

- Sequential compose mapping: T019 -> T020
- Parallel docs/contract updates after mapping: T021 and T022
- Timing notes after command matrix: T023

### User Story 3

- Parallel logging updates: T024, T025, T026, T027, T028, T029
- Contract and quickstart updates after code changes: T030 -> T031

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete User Story 1 tasks (T008-T018).
3. Validate one-command startup, health/dependency gating, and uploads readability.
4. Demo MVP runtime deployment behavior.

### Incremental Delivery

1. Deliver P1 startup and runtime readiness behavior.
2. Deliver P2 independent-build experience.
3. Deliver P3 standardization and Kafka logging policy.
4. Complete final validations and cross-artifact consistency.

### Parallel Team Strategy

1. Engineer A owns compose foundation and gating tasks (T004-T007, T014-T016).
2. Engineer B owns Dockerfiles and build optimization tasks (T008-T013, T019-T023).
3. Engineer C owns logging policy and documentation validation tasks (T024-T038).

---

## Notes

- `[P]` indicates tasks that can be executed in parallel because they touch different files with no direct dependency.
- Story labels (`[US1]`, `[US2]`, `[US3]`) are used only in user story phases.
- Every task includes an explicit file path and is written to be directly actionable by an implementation agent.
