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
- `build.context`: points to repository root (`.`) so shared packages can be copied during image build
- `build.dockerfile`: points to Dockerfile in component directory
- `restart`: explicitly set to a restartable policy
- Unique compose service name

Each in-scope component MUST have a corresponding Dockerfile in its own directory.

## Healthcheck and Dependency Contract

- `kafka` MUST define a compose `healthcheck`.
- `backend-service` MUST define a compose `healthcheck`.
- Every in-scope agent service (`orchestrator-agent`, `planner-agent`, `rag-agent`, `teaching-agent`, `quiz-agent`) MUST depend on both `kafka` and `backend-service`.
- Dependency gating MUST use health-aware compose conditions so agents start only after both dependencies are healthy.

## Shared Uploads Volume Contract

- `backend-service` and `rag-agent` MUST share an uploads volume mapping.
- The path emitted by backend for uploaded files MUST be valid and readable by RAG without manual path rewriting.
- Volume mapping MUST be explicit in compose and documented for local development.

## Kafka Logging Contract

- Every in-scope service that uses Kafka clients MUST set:
	- `logging.getLogger("kafka").setLevel(logging.WARNING)`
- Logging policy MUST be applied during service startup.

## LiteLLM Logging Contract

- Every in-scope service that uses LiteLLM MUST set:
	- `logging.getLogger("LiteLLM").setLevel(logging.WARNING)`
- Logging policy MUST be applied during service startup.

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

### Service-to-directory mapping table

| Compose service | Directory | Dockerfile |
|---|---|---|
| `backend-service` | `backend_service/` | `backend_service/Dockerfile` |
| `orchestrator-agent` | `orchestrator_agent/` | `orchestrator_agent/Dockerfile` |
| `planner-agent` | `planner_agent/` | `planner_agent/Dockerfile` |
| `rag-agent` | `rag_agent/` | `rag_agent/Dockerfile` |
| `teaching-agent` | `teaching_agent/` | `teaching_agent/Dockerfile` |
| `quiz-agent` | `quiz_agent/` | `quiz_agent/Dockerfile` |

All in-scope services use `build.context: .` and an explicit service-specific Dockerfile path.

All service names above are required for command-level examples and validation steps.

## Verification Contract
A feature-complete implementation must satisfy all checks:
1. Compose configuration validation passes.
2. Every in-scope service builds successfully.
3. Full-stack startup launches all in-scope services.
4. Restart policy exists on all in-scope services.
5. `kafka` and `backend-service` each have passing healthchecks.
6. Every in-scope agent service declares dependencies on both `kafka` and `backend-service` with health-aware conditions.
7. Backend and RAG share uploads volume and path readability is validated.
8. Kafka-using services apply warning-level Kafka logging policy.
9. LiteLLM-using services apply warning-level LiteLLM logging policy.

## Independent Build Acceptance Checks

- `docker compose build backend-service` succeeds independently.
- `docker compose build orchestrator-agent` succeeds independently.
- `docker compose build planner-agent` succeeds independently.
- `docker compose build rag-agent` succeeds independently.
- `docker compose build teaching-agent` succeeds independently.
- `docker compose build quiz-agent` succeeds independently.
