# Phase 0 Research: Docker Agent Deployments

## Decision 1: Containerize each in-scope application component with one Dockerfile per directory
- Decision: Add a Dockerfile to each in-scope directory: backend_service, orchestrator_agent, planner_agent, rag_agent, teaching_agent, quiz_agent, ui_frontend.
- Rationale: The specification requires all agents and services to be buildable independently and represented directly in compose.
- Alternatives considered:
  - Single shared Dockerfile with build args for all services (rejected: weaker readability and harder per-service customization).
  - Multi-stage monorepo image containing all processes (rejected: does not align with one-service-per-container compose operations).

## Decision 2: Use repository-root compose build contexts with explicit per-service Dockerfiles
- Decision: Compose service entries will keep `context: .` at repository root and reference each component's Dockerfile explicitly.
- Rationale: Shared packages like `project/` and `requirements.txt` are used across services, so root context keeps Dockerfiles simple while preserving one-to-one component mapping.
- Alternatives considered:
  - Component-only build contexts (rejected: shared package copying becomes awkward or requires extra packaging steps).
  - A single root Dockerfile parameterized for all services (rejected: harder to reason about and maintain).

## Decision 3: Enforce restart behavior with targeted healthchecks and dependency gating
- Decision: Set restart behavior for each in-scope service, keep healthchecks only on `kafka` and `backend-service`, make all agent services depend on both healthy dependencies, and make the UI frontend depend on healthy `backend-service`.
- Rationale: Matches the clarified requirement while keeping the compose graph minimal and meaningful.
- Alternatives considered:
  - Add healthchecks to all services (rejected: unnecessary complexity; only kafka/backend are required gates).
  - Omit healthchecks and rely on startup ordering only (rejected: does not satisfy the dependency requirement).

## Decision 4: Keep shared runtime dependencies in compose and preserve interoperability
- Decision: Retain existing infrastructure services (Kafka and Kafka UI) and integrate application services around them.
- Rationale: Existing architecture already depends on these services for local workflows.
- Alternatives considered:
  - Replace infrastructure with externally managed local dependencies (rejected: not aligned with current repo-local workflow).

## Decision 5: Treat the Streamlit UI as a first-class compose service
- Decision: Add `ui_frontend` to the compose-managed application scope with its own Dockerfile, browser-accessible port, and env-driven runtime contract.
- Rationale: The feature now explicitly includes the frontend, and the UI already validates required env vars during startup.
- Alternatives considered:
  - Leave the UI as a host-run developer process (rejected: breaks the one-command startup goal).
  - Proxy the UI through backend-service (rejected: unnecessary coupling and outside scope).

## Decision 6: Verify deployment outcomes with config/build/runtime smoke checks
- Decision: Validation will include compose config parsing, per-service build checks, full stack startup smoke tests, dependency gating checks, restart-policy smoke, and a browser-level UI reachability check.
- Rationale: Provides objective evidence for requirements and constitution quality/performance gates.
- Alternatives considered:
  - Rely only on manual startup observation (rejected: less repeatable and harder to enforce in CI).

## Decision 7: Share uploads volume between backend and RAG
- Decision: Map a single shared uploads volume path between `backend-service` and `rag-agent` so backend-emitted file paths resolve directly for RAG reads.
- Rationale: Removes path translation ambiguity and guarantees consistent filesystem visibility for upload processing.
- Alternatives considered:
  - Copy files between services over API (rejected: adds unnecessary transfer overhead and coupling).
  - Maintain separate per-service upload directories (rejected: violates path consistency requirement).

## Decision 8: Standardize Kafka and LiteLLM logger levels at warning where applicable
- Decision: Configure each in-scope Kafka-using service to set `logging.getLogger("kafka").setLevel(logging.WARNING)` during startup, and each LiteLLM-using service to set `logging.getLogger("LiteLLM").setLevel(logging.WARNING)`.
- Rationale: Reduces log noise while keeping warnings and errors visible.
- Alternatives considered:
  - Keep default logger levels (rejected: noisy logs during local stack runs).
  - Raise both to ERROR only (rejected: hides potentially useful warning signals).

## Decision 9: Reuse `.env.local` for runtime and align `.env.local.example` during implementation
- Decision: Keep compose `env_file` usage centered on `.env.local` for runnable local stacks, while implementation also adds or updates `.env.local.example` so the UI env variables are documented.
- Rationale: The current compose file already uses `.env.local`, but the feature request explicitly references `.env.local.example`; aligning both avoids a hidden config contract.
- Alternatives considered:
  - Switch compose directly to `.env.local.example` (rejected: examples should not be the live runtime source).
  - Ignore the example file request (rejected: would leave the UI env contract under-documented).

## Implementation Notes

- Standard Dockerfile pattern for all in-scope services:
  - Base image: `python:3.11-slim`
  - Shared dependency install from repository `requirements.txt`
  - Service-specific source copy and shared `project/` package copy
  - Service runtime command via `python -m <service>.worker` where applicable, backend via its FastAPI/Uvicorn entrypoint, and UI via Streamlit running `ui_frontend/app.py`
- Compose build strategy:
  - Use repository-root build context (`context: .`) for all in-scope services so Dockerfiles can copy both service code and shared modules.
  - Keep per-service Dockerfile path explicit in compose (`dockerfile: <service>/Dockerfile`).
- Runtime consistency:
  - Apply `restart: unless-stopped` to all in-scope services.
  - Add explicit `healthcheck` blocks for `kafka` and `backend-service`.
  - Use compose dependency conditions so agent services depend on both `kafka` and `backend-service` readiness, and UI depends on healthy `backend-service`.
  - Map shared uploads volume across backend and RAG with matching mount path expectations.
  - Pass UI env variables through compose: `UI_WEBSOCKET_URL`, `UI_BACKEND_URL`, `UI_SIMULATOR_ENABLED`.
  - Set Kafka and LiteLLM logger levels to warning in applicable service startup paths.
