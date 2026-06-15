# Data Model: Docker Agent Deployments

## Entity: ContainerizedComponent
- Description: Deployable application component represented by a directory-level Dockerfile.
- Fields:
  - name (string, unique): Logical component identifier.
  - directory (string): Repository-relative path to component source.
  - dockerfile_path (string): Path to Dockerfile inside component directory.
  - build_context (string): Build context path used by compose.
  - image_tag (string): Build output image identifier used by compose.
  - startup_command (string | null): Runtime command when not using default image command.
  - env_sources (list[string]): Referenced env files/variables required at runtime.
  - restart_policy (enum): Restart behavior policy for container runtime.
- Validation Rules:
  - name must be unique across all in-scope components.
  - dockerfile_path must exist and be under directory.
  - build_context must resolve to an existing local path.
  - restart_policy must be non-empty and set for each component.

## Entity: ComposeServiceEntry
- Description: Compose declaration that binds a ContainerizedComponent into the local stack.
- Fields:
  - service_name (string, unique): Compose service key.
  - component_name (string): Foreign key to ContainerizedComponent.name.
  - build (object): Compose build block including context and dockerfile.
  - image (string): Optional explicit image name for tagging.
  - depends_on (list[string]): Compose startup dependency hints.
  - restart (string): Restart policy for container.
  - environment (map[string,string|number|bool]): Runtime variables.
  - volumes (list[string]): Optional bind mounts/named volumes.
  - ports (list[string]): Optional exposed port mappings.
- Validation Rules:
  - service_name must be unique across compose file.
  - component_name must reference an existing ContainerizedComponent.
  - build context/dockerfile pair must resolve locally.
  - restart must be present for in-scope services.
  - healthcheck field must be absent for this feature scope.

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

## Relationships
- ContainerizedComponent 1 -> 1 ComposeServiceEntry (for in-scope feature scope).
- DeploymentStack 1 -> N ComposeServiceEntry.

## State Transitions
- ContainerizedComponent lifecycle states:
  - defined -> buildable -> running -> restarting (on failure) -> running
  - defined -> build_failed (on invalid Dockerfile/context)
- ComposeServiceEntry lifecycle states:
  - declared -> validated (compose config passes) -> active (service started)
