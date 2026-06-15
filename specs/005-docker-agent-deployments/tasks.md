# Tasks: Docker Agent Deployments

**Input**: Design documents from /specs/005-docker-agent-deployments/
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: No dedicated automated test-authoring tasks are included because this feature is deployment configuration and the specification does not request TDD. Validation tasks are included for compose config, image builds, healthchecks, dependency gating, and runtime smoke checks.

**Organization**: Tasks are grouped by user story to enable independent implementation and validation of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align specification, contract, and quickstart docs with implementation scope and naming.

- [X] T001 Confirm in-scope component list and service-name mapping in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [X] T002 Confirm healthcheck and dependency-gating acceptance criteria in specs/005-docker-agent-deployments/spec.md
- [X] T003 [P] Align quickstart command references with compose service names in specs/005-docker-agent-deployments/quickstart.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish compose-wide baseline used by all user stories.

**CRITICAL**: No user story work begins until this phase is complete.

- [X] T004 Add or confirm application service scaffold for backend and agent services in docker-compose.yaml
- [X] T005 Define restart policy baseline for all in-scope application services in docker-compose.yaml
- [X] T006 Preserve compatibility with Kafka/Kafka-UI infrastructure definitions in docker-compose.yaml

**Checkpoint**: Foundation is ready for user-story implementation.

---

## Phase 3: User Story 1 - Run all components locally via compose (Priority: P1) MVP

**Goal**: Enable one-command startup with health-aware readiness gating.

**Independent Test**: Run `docker compose up -d` and verify kafka/backend become healthy and agent services launch only after both dependencies are healthy.

### Implementation for User Story 1

- [X] T007 [P] [US1] Create backend container build definition in backend_service/Dockerfile
- [X] T008 [P] [US1] Create orchestrator container build definition in orchestrator_agent/Dockerfile
- [X] T009 [P] [US1] Create planner container build definition in planner_agent/Dockerfile
- [X] T010 [P] [US1] Create RAG container build definition in rag_agent/Dockerfile
- [X] T011 [P] [US1] Create teaching container build definition in teaching_agent/Dockerfile
- [X] T012 [P] [US1] Create quiz container build definition in quiz_agent/Dockerfile
- [X] T013 [US1] Add compose entries for backend and all agent services with build contexts in docker-compose.yaml
- [X] T014 [US1] Add `healthcheck` for `kafka` and `backend-service` in docker-compose.yaml
- [X] T015 [US1] Configure each agent service to depend on both `kafka` and `backend-service` with health-aware conditions in docker-compose.yaml
- [X] T016 [US1] Update startup and readiness verification steps in specs/005-docker-agent-deployments/quickstart.md

**Checkpoint**: User Story 1 is independently deployable and verifiable.

---

## Phase 4: User Story 2 - Build each component independently (Priority: P2)

**Goal**: Support targeted single-service builds without rebuilding unrelated components.

**Independent Test**: Build one selected service image and verify only that target is rebuilt successfully.

### Implementation for User Story 2

- [X] T017 [US2] Add explicit per-service image tags in docker-compose.yaml
- [X] T018 [US2] Add per-service build matrix in specs/005-docker-agent-deployments/quickstart.md
- [X] T019 [US2] Encode independent-build acceptance checks in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [X] T020 [US2] Add targeted build command examples for all in-scope services in specs/005-docker-agent-deployments/quickstart.md

**Checkpoint**: User Story 2 build workflows are independently executable.

---

## Phase 5: User Story 3 - Standardized container setup across components (Priority: P3)

**Goal**: Keep deployment definitions consistent and maintainable across all services.

**Independent Test**: Verify all Dockerfiles follow common structure and compose definitions consistently apply restart, healthcheck scope, and dependency rules.

### Implementation for User Story 3

- [X] T021 [P] [US3] Standardize backend Dockerfile conventions in backend_service/Dockerfile
- [X] T022 [P] [US3] Standardize orchestrator Dockerfile conventions in orchestrator_agent/Dockerfile
- [X] T023 [P] [US3] Standardize planner Dockerfile conventions in planner_agent/Dockerfile
- [X] T024 [P] [US3] Standardize RAG Dockerfile conventions in rag_agent/Dockerfile
- [X] T025 [P] [US3] Standardize teaching Dockerfile conventions in teaching_agent/Dockerfile
- [X] T026 [P] [US3] Standardize quiz Dockerfile conventions in quiz_agent/Dockerfile
- [X] T027 [US3] Add service-to-directory mapping, healthcheck scope, and dependency rules in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [X] T028 [US3] Verify compose excludes healthchecks for agent services while keeping required checks on kafka/backend in docker-compose.yaml

**Checkpoint**: User Story 3 standardization is complete and auditable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cross-document consistency.

- [X] T029 [P] Validate compose rendering and syntax and document results in specs/005-docker-agent-deployments/quickstart.md
- [X] T030 [P] Validate full build and targeted build workflows and capture expected outcomes in specs/005-docker-agent-deployments/quickstart.md
- [X] T031 Validate healthcheck and dependency-gating runtime behavior and record evidence in specs/005-docker-agent-deployments/quickstart.md
- [X] T032 Validate restart behavior smoke flow and record evidence in specs/005-docker-agent-deployments/quickstart.md
- [X] T033 Final consistency pass across spec, plan, tasks, contract, and quickstart in specs/005-docker-agent-deployments/tasks.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies.
- Foundational (Phase 2): depends on Setup and blocks all user stories.
- User Story phases (Phases 3-5): depend on Foundational completion.
- Polish (Phase 6): depends on completion of all targeted user stories.

### User Story Dependencies

- User Story 1 (P1): starts after Phase 2; no dependency on other user stories.
- User Story 2 (P2): starts after Phase 2 and after core compose services exist.
- User Story 3 (P3): starts after Phase 2 and may overlap with User Story 2 documentation updates.

### Task Dependency Highlights

- T013 depends on T007-T012.
- T014 depends on T013.
- T015 depends on T013 and T014.
- T016 depends on T014 and T015.
- T017 depends on T013.
- T018 and T020 depend on T017.
- T027 depends on T021-T026.
- T028 depends on T014 and T015.
- T029-T032 depend on T013-T028.

---

## Parallel Execution Examples

### User Story 1

- Parallel group A: T007, T008, T009, T010, T011, T012
- Then sequential: T013 -> T014 -> T015 -> T016

### User Story 2

- Sequential core: T017 -> T018
- Parallel after T017: T019 and T020

### User Story 3

- Parallel group B: T021, T022, T023, T024, T025, T026
- Then sequential: T027 -> T028

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (User Story 1).
3. Validate full startup, healthchecks, and dependency gating.
4. Stop for MVP review/demo.

### Incremental Delivery

1. Deliver User Story 1 full-stack startup and readiness gating.
2. Deliver User Story 2 independent build workflows.
3. Deliver User Story 3 standardization and contract hardening.
4. Complete polish validations and final consistency pass.

### Parallel Team Strategy

1. One engineer owns compose foundation and health/dependency wiring (T004-T006, T013-T015).
2. Multiple engineers parallelize Dockerfile work (T007-T012, T021-T026).
3. One engineer owns documentation/contract validation updates (T016, T018-T020, T027, T029-T033).
