# Data Model: Docker Agent Deployments

## Entity: ContainerizedComponent
- Description: Deployable application component represented by a directory-level Dockerfile.
- Fields:
  - name (string, unique): Logical component identifier.
  - directory (string): Repository-relative path to component source.
  - dockerfile_path (string): Path to Dockerfile inside component directory.
  - build_context (string): Build context path used by compose.
  - image_tag (string): Build output image identifier used by compose.
  - startup_command (string | null): Runtime command when not using image defaults.
  - env_sources (list[string]): Referenced env files/variables required at runtime.
  - restart_policy (enum): Restart behavior policy for container runtime.
  - exposes_port (boolean): Whether the component must publish a developer-accessible port.
- Validation Rules:
  - name must be unique across all in-scope components.
  - dockerfile_path must exist and be under directory.
  - build_context must resolve to an existing local path.
  - restart_policy must be non-empty and set for each component.
  - `ui_frontend` must expose a browser-reachable port and env-driven connection settings.

## Entity: ComposeServiceEntry
- Description: Compose declaration that binds a ContainerizedComponent into the local stack.
- Fields:
  - service_name (string, unique): Compose service key.
  - component_name (string): Foreign key to ContainerizedComponent.name.
  - build (object): Compose build block including context and dockerfile.
  - image (string): Explicit image name/tag.
  - depends_on (list[string]): Compose startup dependency map.
  - healthcheck (object | null): Container health probe definition (required for kafka and backend-service).
  - restart (string): Restart policy for container.
  - environment (map[string,string|number|bool]): Runtime variables.
  - env_file (list[string]): Runtime env file sources.
  - volumes (list[string]): Optional bind mounts/named volumes.
  - ports (list[string]): Optional exposed port mappings.
- Validation Rules:
  - service_name must be unique across compose file.
  - component_name must reference an existing ContainerizedComponent.
  - build context/dockerfile pair must resolve locally.
  - restart must be present for in-scope services.
  - healthcheck must be present for `kafka` and `backend-service`.
  - healthcheck may be absent for agent services and `ui-frontend`.
  - every in-scope agent service depends_on must include both `kafka` and `backend-service`.
  - `ui-frontend` depends_on must include healthy `backend-service`.
  - `ui-frontend` must expose a host-accessible Streamlit port.

## Entity: DeploymentStack
- Description: Full local composition of infrastructure and application services.
- Fields:
  - stack_name (string)
  - infrastructure_services (list[string])
  - application_services (list[string])
  - compose_file_path (string)
- Validation Rules:
  - All in-scope components must be represented in application_services.
  - compose_file_path must resolve to repository root compose file.

## Entity: SharedUploadsVolume
- Description: Cross-service filesystem mapping that allows backend and RAG to access the same uploaded files.
- Fields:
  - volume_name (string)
  - host_path (string | null)
  - backend_mount_path (string)
  - rag_mount_path (string)
  - path_contract (string): Rule defining how backend-emitted paths remain valid for RAG reads.
- Validation Rules:
  - backend_mount_path and rag_mount_path must represent the same logical location or deterministic alias contract.
  - backend-emitted upload paths must be resolvable by RAG without mutation.

## Entity: UIFrontendEnvContract
- Description: Required environment-variable contract for the Streamlit container to connect to backend services correctly.
- Fields:
  - websocket_url (string): Runtime value for `UI_WEBSOCKET_URL`.
  - backend_url (string): Runtime value for `UI_BACKEND_URL`.
  - simulator_enabled (boolean): Optional runtime value for `UI_SIMULATOR_ENABLED`.
  - env_file_path (string): Expected compose env file source.
  - exposed_port (integer): Browser-accessible port for the frontend container.
- Validation Rules:
  - websocket_url must be non-empty or the UI must fail fast during startup.
  - backend_url must be non-empty or the UI must fail fast during startup.
  - env_file_path must point to `.env.local` for local compose execution.
  - `.env.local.example` must document the same variable names used by the container.

## Entity: ServiceLoggingPolicy
- Description: Runtime logging rules applied to Kafka-using and LiteLLM-using services.
- Fields:
  - service_name (string)
  - kafka_logger_level (enum | null): `WARNING` when Kafka clients are used.
  - litellm_logger_level (enum | null): `WARNING` when LiteLLM is used.
- Validation Rules:
  - each in-scope Kafka-using service must define kafka logger level WARNING at startup.
  - each LiteLLM-using service must define `logging.getLogger("LiteLLM").setLevel(logging.WARNING)` at startup.

## Relationships
- ContainerizedComponent 1 -> 1 ComposeServiceEntry (for in-scope feature scope).
- DeploymentStack 1 -> N ComposeServiceEntry.
- DeploymentStack 1 -> 1 SharedUploadsVolume.
- ContainerizedComponent (`ui_frontend`) 1 -> 1 UIFrontendEnvContract.
- ContainerizedComponent N -> 1 ServiceLoggingPolicy (for services that use Kafka and/or LiteLLM).

## State Transitions
- ContainerizedComponent lifecycle states:
  - defined -> buildable -> running -> restarting (on failure) -> running
  - defined -> build_failed (on invalid Dockerfile/context)
- ComposeServiceEntry lifecycle states:
  - declared -> validated (compose config passes) -> active (service started)
- UI frontend env contract states:
  - documented -> populated -> validated-at-startup -> serving
