# Phase 0 Research: Docker Agent Deployments

## Decision 1: Containerize each in-scope application component with one Dockerfile per directory
- Decision: Add a Dockerfile to each in-scope directory: backend_service, orchestrator_agent, planner_agent, rag_agent, teaching_agent, quiz_agent.
- Rationale: The specification requires all agents and services to be buildable independently and represented directly in compose.
- Alternatives considered:
  - Single shared Dockerfile with build args for all services (rejected: weaker readability and harder per-service customization).
  - Multi-stage monorepo image containing all processes (rejected: does not align with one-service-per-container compose operations).

## Decision 2: Use docker-compose build contexts rooted at each component directory
- Decision: Compose service entries will use local build contexts that point to each component folder.
- Rationale: Enables isolated rebuilds and clear mapping between source directory and image definition.
- Alternatives considered:
  - Root-level build contexts with custom Dockerfile paths (rejected: less discoverable and easier to misconfigure).

## Decision 3: Enforce restart behavior with compose restart policy and omit healthchecks
- Decision: Set restart behavior for each in-scope service and explicitly skip healthchecks for this feature.
- Rationale: Matches user requirement for restartable services and no healthcheck requirement.
- Alternatives considered:
  - Add healthchecks for all services (rejected: explicitly out of scope).
  - Leave restart policy unset (rejected: violates feature requirement).

## Decision 4: Keep shared runtime dependencies in compose and preserve interoperability
- Decision: Retain existing infrastructure services (Kafka and Kafka UI) and integrate agent/service entries around them.
- Rationale: Existing architecture already depends on these services for local workflows.
- Alternatives considered:
  - Replace infrastructure stack with external managed services for local dev (rejected: not aligned with current repo-local workflow).

## Decision 5: Verify deployment outcomes with config/build/runtime smoke checks
- Decision: Validation will include compose config parsing, per-service build checks, and stack startup smoke tests.
- Rationale: Provides objective evidence for requirements and constitution testing/performance gates.
- Alternatives considered:
  - Rely only on manual startup observation (rejected: less repeatable and harder to enforce in CI).
