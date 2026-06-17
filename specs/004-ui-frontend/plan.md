# Implementation Plan: UI Frontend for Multi-Agent Tutor

**Branch**: `[005-create-feature-branch]` | **Date**: 2026-06-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-ui-frontend/spec.md`

## Summary

Build a Streamlit UI frontend that consumes a backend WebSocket relay, validates typed event envelopes, routes events to Chat, Quiz, Evaluation, and Status views, and includes robust reconnection behavior plus built-in mock simulation. The implementation extends shared schemas in `project/schemas.py`, consumes a backend relay provided by the backend team, and keeps v1 session state in memory.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Streamlit, FastAPI, pydantic v2, python-dotenv, pytest  
**Storage**: N/A (in-memory session state only)  
**Testing**: pytest  
**Target Platform**: Linux runtime and local developer environments  
**Project Type**: Web application (backend relay + frontend UI)  
**Performance Goals**: 95% of events visible in UI within 1s; reconnect starts within 2s of unexpected disconnect  
**Constraints**: WebSocket endpoint must come from environment config; all incoming events must be schema-validated before routing; unknown/invalid events must not crash UI; simulator must use same routing path as live stream  
**Scale/Scope**: One active tutoring session per frontend client in v1; planner/teaching/quiz/evaluation event families; no cross-refresh persistence in v1

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate Review

- Code Quality Gate: PASS
  - Apply lint/format/static checks to added backend relay, schema, and frontend modules.
- Testing Gate: PASS
  - Require unit tests for schema validation and routing plus integration tests for relay lifecycle and reconnect behavior.
- UX Consistency Gate: PASS
  - Maintain stable tab behavior, explicit connection-state indicators, and accessible interaction patterns.
- Performance Gate: PASS
  - Validate event-to-render and reconnect-start budgets from FR-014/SC-004.
- Maintainability Gate: PASS
  - Keep strict contract documentation, structured diagnostics for event failures, and synchronized artifacts.

## Project Structure

### Documentation (this feature)

```text
specs/004-ui-frontend/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── frontend-websocket-event-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
project/
└── schemas.py                       # Add websocket event contracts

backend_service/
└── Consumed as dependency (owned by backend team)

ui_frontend/
├── app.py                           # Streamlit entrypoint
├── websocket_client.py              # Connect/reconnect + message ingest
├── router.py                        # Event validation and routing
├── state.py                         # Session state containers
├── simulator.py                     # Mock event scenarios
└── tests/
    ├── test_router.py
    ├── test_state.py
    └── test_simulator.py
```

**Structure Decision**: Keep the existing Python-centric monorepo and introduce a dedicated `ui_frontend/` module while extending `backend_service` and shared contracts in `project/schemas.py`.

## Phase 0: Research Outcomes

Research decisions in [research.md](./research.md) resolve all major unknowns:
- Streamlit selected as frontend runtime.
- `backend_service` owns WebSocket relay endpoint.
- Shared `AgentEvent`-family contracts live in `project/schemas.py`.
- Validation-before-routing is mandatory for all websocket messages.
- Mock simulator runs through the same pipeline as live events.
- v1 state persistence remains in-memory only.

No unresolved `NEEDS CLARIFICATION` items remain.

## Phase 1: Design & Contracts

### Data Model Output

- [data-model.md](./data-model.md) defines:
  - Frontend session/runtime state entities
  - Connection lifecycle state
  - Event envelope and payload families
  - Diagnostic model for invalid/unknown events
  - Simulation scenario model and transitions

### Contract Output

- [contracts/frontend-websocket-event-contract.md](./contracts/frontend-websocket-event-contract.md) defines:
  - WebSocket connection behavior and reconnection semantics
  - Required message envelope and event taxonomy
  - Routing contract by event type
  - Error handling contract for invalid/unknown events
  - Simulator parity expectations

### Quickstart Output

- [quickstart.md](./quickstart.md) defines local setup, environment variables, backend/frontend run flow, simulator usage, and verification commands.

### Agent Context Update

- Updated SPECKIT plan references in:
  - `.github/copilot-instructions.md`
  - `CLAUDE.md`

## Post-Design Constitution Check

- Code Quality Gate: PASS
- Testing Gate: PASS
- UX Consistency Gate: PASS
- Performance Gate: PASS
- Maintainability Gate: PASS

## Complexity Tracking

No constitution violations identified. Added complexity is requirement-driven by real-time streaming, schema-safe routing, and simulation parity guarantees.
