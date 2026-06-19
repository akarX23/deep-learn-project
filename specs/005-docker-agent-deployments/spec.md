# Feature Specification: Docker Agent Deployments

**Feature Branch**: `005-docker-agent-deployments`  
**Created**: 2026-06-15  
**Updated**: 2026-06-17  
**Status**: Draft  
**Input**: User description: "I want to create docker deployments for each of the agents and services. Create Dockerfiles in each agent and service directory, add them as services and buildable images in the docker compose. No need for any healthchecks, but make them restartable. The UI Frontend should also have a Dockerfile and be integrated into docker-compose. Use the corresponding environment variables from .env.local.example."

## Clarifications

### Session 2026-06-15

- Q: Should health checks be omitted for all services? → A: Add health checks for `kafka` and `backend-service`, and make all other in-scope services depend on both.
- Q: How should uploaded files be shared between backend and RAG service? → A: Map a shared uploads volume so backend-generated paths are always valid and readable by the RAG agent.
- Q: What Kafka client logging level should be used across services? → A: For each agent and service, set Kafka logger level to warning using `logging.getLogger("kafka").setLevel(logging.WARNING)`.
- Q: What LiteLLM client logging level should be used across services? → A: For each agent and service that uses LiteLLM, set LiteLLM logger level to warning using `logging.getLogger("LiteLLM").setLevel(logging.WARNING)`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run all components locally via compose (Priority: P1)

As a developer, I can start all backend agents and services from a single compose configuration so I can run and validate the full multi-agent workflow without manual per-service startup steps.

**Why this priority**: End-to-end local runtime is the core requirement and foundation for development, testing, and demos.

**Independent Test**: Can be fully tested by starting the stack with compose and verifying that each defined component launches as a running container without manual restarts.

**Acceptance Scenarios**:

1. **Given** all required source directories exist, **When** a developer starts the compose stack, **Then** each targeted agent and service is created as a runnable container from a buildable image definition.
2. **Given** a container exits unexpectedly, **When** restart policy conditions are met, **Then** the container is automatically restarted.

---

### User Story 2 - Build each component independently (Priority: P2)

As a developer, I can build any single agent or service image on demand so I can iterate on one component without rebuilding unrelated images.

**Why this priority**: Component-level builds improve development speed and reduce iteration cost.

**Independent Test**: Can be fully tested by building one selected component image and confirming the build succeeds without requiring all other components to build in the same command.

**Acceptance Scenarios**:

1. **Given** a developer selects one component, **When** they trigger a build for only that component, **Then** its image build completes independently.

---

### User Story 3 - Standardized container setup across components (Priority: P3)

As a maintainer, I can rely on a consistent containerization pattern for every agent and backend service so onboarding and troubleshooting are predictable.

**Why this priority**: Standardization reduces setup confusion and lowers maintenance overhead.

**Independent Test**: Can be fully tested by reviewing all targeted directories and confirming each contains a Dockerfile and each is represented in compose with aligned restart behavior.

**Acceptance Scenarios**:

1. **Given** a new contributor reviews deployment assets, **When** they inspect target component directories and compose services, **Then** they find a consistent containerization approach and restart settings.

---

### User Story 4 - Run UI Frontend via compose (Priority: P2)

As a developer, I can start the UI frontend as a containerized service alongside backend agents in the compose stack so the full application — from backend to browser — is available through a single startup command.

**Why this priority**: The UI frontend is the user-facing surface of the system; containerizing it alongside agents completes the deployment picture and enables end-to-end validation without running Streamlit manually.

**Independent Test**: Can be fully tested by starting the compose stack and opening the UI frontend URL in a browser to verify the Streamlit application loads and connects to the backend.

**Acceptance Scenarios**:

1. **Given** the compose stack is started with the required UI environment variables set, **When** a developer navigates to the UI frontend port in a browser, **Then** the Streamlit application loads without errors.
2. **Given** the UI container exits unexpectedly, **When** restart policy conditions are met, **Then** the container is automatically restarted without manual intervention.
3. **Given** required environment variables (`UI_WEBSOCKET_URL`, `UI_BACKEND_URL`) are missing, **When** the container starts, **Then** the application fails with a clear configuration error rather than starting silently misconfigured.

---

### Edge Cases

- A component directory exists but is missing required files for image build; the failure should be isolated to that component and clearly reported.
- A component is intentionally not part of local runtime scope; it should not be auto-added without explicit inclusion criteria.
- A component repeatedly fails at startup; restart behavior should continue per policy without requiring manual intervention.
- Service name collisions occur in compose definitions; each component must have a unique service identity.
- If either `kafka` or `backend-service` health check is failing, dependent services should remain blocked by dependency gating until both become healthy.
- If backend emits an upload path that does not resolve in the RAG container, the workflow should fail fast with a clear error instead of silently skipping file access.

- If a required UI frontend environment variable is missing, the application must fail with a clear error rather than silently serving a broken interface.
- If the backend service is unreachable from the UI container (e.g., misconfigured `UI_BACKEND_URL`), the error must surface in the UI and not crash the container silently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a container build definition in each in-scope agent and backend service directory.
- **FR-002**: The system MUST define each in-scope agent and backend service as an individual service in the compose configuration.
- **FR-003**: The system MUST allow each service image to be built from local source definitions as part of compose workflows.
- **FR-004**: The system MUST allow a developer to build any individual service image independently of other services.
- **FR-005**: The system MUST configure all in-scope services with automatic restart behavior.
- **FR-006**: The system MUST define healthcheck configurations for `kafka` and `backend-service` in compose.
- **FR-007**: The system MUST preserve interoperability with shared local infrastructure dependencies already defined in compose.
- **FR-008**: The system MUST document or encode service naming consistently so each component is uniquely addressable.
- **FR-009**: The system MUST define a scope of included components covering agents and backend services in this repository.
- **FR-010**: The system MUST keep local deployment startup as a single compose-driven operation.
- **FR-011**: The system MUST configure every in-scope agent service (orchestrator, planner, RAG, teaching, quiz) to depend on both `kafka` and `backend-service`.
- **FR-012**: The system MUST map a shared uploads volume between `backend-service` and `rag-agent` so file paths produced by backend remain valid and readable by RAG.
- **FR-013**: The system MUST ensure each in-scope agent and service configures Kafka client logging at warning level (`logging.getLogger("kafka").setLevel(logging.WARNING)`).
- **FR-014**: The system MUST ensure each in-scope agent and service that uses LiteLLM configures the LiteLLM logger at warning level (`logging.getLogger("LiteLLM").setLevel(logging.WARNING)`).
- **FR-015**: The system MUST provide a container build definition for the UI frontend (`ui_frontend/Dockerfile`).
- **FR-016**: The system MUST define the UI frontend as a service in compose with automatic restart behavior.
- **FR-017**: The system MUST allow the UI frontend image to be built from local source as part of compose workflows.
- **FR-018**: The system MUST pass the UI frontend environment variables (`UI_WEBSOCKET_URL`, `UI_BACKEND_URL`, `UI_SIMULATOR_ENABLED`) into the container via the compose `env_file` pointing to `.env.local`.
- **FR-019**: The system MUST expose the UI frontend on a port accessible to developers from their local machine.
- **FR-020**: The UI frontend compose service MUST depend on `backend-service` being healthy before starting.

### Key Entities *(include if feature involves data)*

- **Containerized Component**: A deployable unit representing one agent or backend service, with its own directory-level build definition and runtime settings.
- **Compose Service Entry**: A runtime definition that maps a containerized component into the local deployment stack, including build source and restart behavior.
- **Deployment Stack**: The complete set of compose services needed to run the project locally for integration and workflow testing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of in-scope agents and backend services have a corresponding container build definition in their directories.
- **SC-002**: 100% of in-scope agents and backend services are represented as buildable services in compose.
- **SC-003**: Developers can launch the full local deployment stack with one compose start action and no manual per-service startup steps.
- **SC-004**: Developers can build any single in-scope service image independently in under 3 minutes on a standard local development machine.
- **SC-005**: For unexpected container exit events during local runs, 100% of in-scope services attempt automatic restart per configured policy.
- **SC-006**: `kafka` and `backend-service` each expose a passing compose healthcheck in local startup flows.
- **SC-007**: 100% of in-scope agent services are configured with dependency links to both `kafka` and `backend-service`.
- **SC-008**: 100% of backend-emitted upload paths used by RAG resolve to readable files through the shared uploads volume mapping.
- **SC-009**: 100% of in-scope services that use Kafka configure the Kafka logger level to warning.
- **SC-010**: 100% of in-scope services that use LiteLLM configure the LiteLLM logger level to warning.
- **SC-011**: The UI frontend service is accessible in a browser after the compose stack starts with no additional configuration beyond setting required environment variables.

## Assumptions

- The existing repository structure for agent and backend service directories remains stable during this feature.
- Existing shared infrastructure services in compose (for example, message broker and related dependencies) continue to be used.
- Local developers have a container runtime capable of building and running compose services.
- This feature targets local deployment workflows and not production orchestration concerns.
- A `.env.local.example` file will be created or the existing `.env.local` file defines the environment variables; UI frontend env vars (`UI_WEBSOCKET_URL`, `UI_BACKEND_URL`, `UI_SIMULATOR_ENABLED`) are populated by the developer before starting the stack.
- The UI frontend Streamlit app runs on a well-known port that developers access via browser after stack startup.
- The UI frontend depends on `backend-service` being available; it does not require a compose dependency gate but the developer is expected to start the full stack together.
