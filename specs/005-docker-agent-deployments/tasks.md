# Tasks: Docker Agent Deployments

**Input**: Design documents from /specs/005-docker-agent-deployments/
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: No dedicated automated test-authoring tasks are included because this feature is deployment configuration and the specification does not request TDD. Validation tasks are included for compose config, image builds, and runtime smoke checks.

**Organization**: Tasks are grouped by user story to enable independent implementation and validation of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align feature docs with exact in-scope deployment targets before editing runtime artifacts.

- [ ] T001 Confirm in-scope component list and service-name mapping in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [ ] T002 Align quickstart command section with intended compose service names in specs/005-docker-agent-deployments/quickstart.md
- [ ] T003 [P] Add implementation notes for containerization conventions in specs/005-docker-agent-deployments/research.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish compose-wide application service structure that all user stories depend on.

**CRITICAL**: No user story work begins until this phase is complete.

- [ ] T004 Add application service scaffold section for agent/backend containers in docker-compose.yaml
- [ ] T005 Define restart policy baseline for all in-scope application services in docker-compose.yaml
- [ ] T006 Preserve and document Kafka/Kafka-UI interoperability requirements in docker-compose.yaml

**Checkpoint**: Foundation ready. User story implementation can begin.

---

## Phase 3: User Story 1 - Run all components locally via compose (Priority: P1) MVP

**Goal**: Enable one-command startup for all in-scope agents and backend services from compose.

**Independent Test**: Run docker compose up for the full stack and verify each in-scope service becomes running/restarting without manual per-service startup.

### Implementation for User Story 1

- [ ] T007 [P] [US1] Create backend service container build definition in backend_service/Dockerfile
- [ ] T008 [P] [US1] Create orchestrator service container build definition in orchestrator_agent/Dockerfile
- [ ] T009 [P] [US1] Create planner service container build definition in planner_agent/Dockerfile
- [ ] T010 [P] [US1] Create RAG service container build definition in rag_agent/Dockerfile
- [ ] T011 [P] [US1] Create teaching service container build definition in teaching_agent/Dockerfile
- [ ] T012 [P] [US1] Create quiz service container build definition in quiz_agent/Dockerfile
- [ ] T013 [US1] Add compose services for backend and all agents with build contexts in docker-compose.yaml
- [ ] T014 [US1] Add restart behavior and startup dependency wiring for in-scope services in docker-compose.yaml
- [ ] T015 [US1] Update full-stack startup and service verification steps in specs/005-docker-agent-deployments/quickstart.md

**Checkpoint**: User Story 1 is independently deployable and verifiable.

---

## Phase 4: User Story 2 - Build each component independently (Priority: P2)

**Goal**: Support single-service image builds without rebuilding unrelated services.

**Independent Test**: Build one selected service image through compose and verify only the targeted service build executes successfully.

### Implementation for User Story 2

- [ ] T016 [US2] Add explicit per-service image names/tags to compose service entries in docker-compose.yaml
- [ ] T017 [US2] Add per-service build command matrix in specs/005-docker-agent-deployments/quickstart.md
- [ ] T018 [US2] Encode independent-build acceptance checks in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [ ] T019 [US2] Add targeted build examples for all in-scope services in specs/005-docker-agent-deployments/quickstart.md

**Checkpoint**: User Story 2 builds can be executed and validated independently.

---

## Phase 5: User Story 3 - Standardized container setup across components (Priority: P3)

**Goal**: Make containerization patterns consistent and maintainable across all in-scope components.

**Independent Test**: Review all component Dockerfiles and compose entries to confirm consistent structure, naming, and restart behavior with no healthcheck blocks.

### Implementation for User Story 3

- [ ] T020 [P] [US3] Standardize Dockerfile structure and metadata conventions in backend_service/Dockerfile
- [ ] T021 [P] [US3] Standardize Dockerfile structure and metadata conventions in orchestrator_agent/Dockerfile
- [ ] T022 [P] [US3] Standardize Dockerfile structure and metadata conventions in planner_agent/Dockerfile
- [ ] T023 [P] [US3] Standardize Dockerfile structure and metadata conventions in rag_agent/Dockerfile
- [ ] T024 [P] [US3] Standardize Dockerfile structure and metadata conventions in teaching_agent/Dockerfile
- [ ] T025 [P] [US3] Standardize Dockerfile structure and metadata conventions in quiz_agent/Dockerfile
- [ ] T026 [US3] Add service-to-directory mapping table and naming rules in specs/005-docker-agent-deployments/contracts/deployment-contract.md
- [ ] T027 [US3] Enforce no-healthcheck rule for in-scope services in docker-compose.yaml

**Checkpoint**: User Story 3 standardization is complete and auditable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation hardening across all stories.

- [ ] T028 [P] Validate compose schema/rendering and update validation notes in specs/005-docker-agent-deployments/quickstart.md
- [ ] T029 [P] Validate full and targeted build workflows and capture expected outcomes in specs/005-docker-agent-deployments/quickstart.md
- [ ] T030 Validate runtime smoke and restart behavior evidence in specs/005-docker-agent-deployments/quickstart.md
- [ ] T031 Final consistency pass across spec, plan, and tasks in specs/005-docker-agent-deployments/tasks.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies.
- Foundational (Phase 2): Depends on Setup completion and blocks all user stories.
- User Story phases (Phases 3-5): Depend on Foundational completion.
- Polish (Phase 6): Depends on completion of the targeted user stories.

### User Story Dependencies

- US1 (P1): Starts immediately after Phase 2; no dependency on other user stories.
- US2 (P2): Starts after Phase 2 and after US1 compose service entries exist.
- US3 (P3): Starts after Phase 2 and may run in parallel with late US2 documentation tasks.

### Task Dependency Highlights

- T013 depends on T007-T012.
- T014 depends on T013.
- T015 depends on T013-T014.
- T016 depends on T013.
- T017 and T019 depend on T016.
- T026 depends on T020-T025.
- T027 depends on T013.
- T028-T030 depend on completion of T013-T027.

---

## Parallel Execution Examples

### User Story 1

- Parallel group A: T007, T008, T009, T010, T011, T012
- Then sequential: T013 -> T014 -> T015

### User Story 2

- Sequential core: T016 -> T017
- Parallel after T016: T018 and T019

### User Story 3

- Parallel group B: T020, T021, T022, T023, T024, T025
- Then sequential: T026 -> T027

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate independent US1 runtime behavior.
4. Pause for demo/review.

### Incremental Delivery

1. Deliver US1 full-stack startup.
2. Deliver US2 independent build workflows.
3. Deliver US3 standardization and consistency hardening.
4. Complete Polish phase validations and final alignment.

### Team Parallelization

1. One engineer owns compose foundation (T004-T006).
2. Multiple engineers split Dockerfile tasks (T007-T012 and T020-T025).
3. One engineer handles contract/quickstart updates (T015, T017-T019, T026, T028-T030).
