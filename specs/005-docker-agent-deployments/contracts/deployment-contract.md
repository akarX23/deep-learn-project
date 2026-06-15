# Deployment Contract: Local Compose Service Definitions

## Purpose
Define the required contract for introducing Dockerized agent and service components into the local compose stack.

## Contract Scope
Applies to in-scope application components:
- backend_service
- orchestrator_agent
- planner_agent
- rag_agent
- teaching_agent
- quiz_agent

## Required Service Contract
Each in-scope component MUST have exactly one compose service entry with:
- `build.context`: points to the component directory
- `build.dockerfile`: points to Dockerfile in component directory
- `restart`: explicitly set to a restartable policy
- Unique compose service name

Each in-scope component MUST have a corresponding Dockerfile in its own directory.

## Prohibited Contract Elements (feature scope)
- No `healthcheck` definitions are required or expected for in-scope services in this feature.

## Buildability Contract
The compose definition MUST support:
- Full-stack build (`compose build` on all in-scope services)
- Independent per-service build (`compose build <service_name>`)

## Runtime Contract
The compose definition MUST support:
- Full-stack startup in one command
- Automatic restart attempts for all in-scope services when containers exit unexpectedly
- Compatibility with existing infrastructure services already present in compose

## Naming and Mapping Contract
- Service names MUST be unique and stable.
- Service-to-directory mapping MUST be one-to-one for in-scope components.
- The mapping MUST be discoverable from compose without requiring external scripts.

## Verification Contract
A feature-complete implementation must satisfy all checks:
1. Compose configuration validation passes.
2. Every in-scope service builds successfully.
3. Full-stack startup launches all in-scope services.
4. Restart policy exists on all in-scope services.
5. No healthcheck block exists for newly added in-scope services in this feature.
