# Research: UI Frontend WebSocket Integration

## Decision 1: Frontend Runtime

- Decision: Use Streamlit as the frontend runtime for chat, quiz, evaluation, and status views.
- Rationale: Repository is Python-first and Streamlit enables fast delivery of tabbed interactive UX with minimal stack fragmentation.
- Alternatives considered: React + TypeScript (strong UI ecosystem but adds separate toolchain), vanilla web UI (less structure for stateful multi-stream workflows).

## Decision 2: WebSocket Relay Ownership

- Decision: Implement the WebSocket relay endpoint inside `backend_service`.
- Rationale: Keeps integration boundary centralized and avoids direct browser-to-Kafka coupling.
- Alternatives considered: separate gateway service (extra operational complexity), frontend mock-only mode (does not satisfy live integration requirement).

## Decision 3: Shared Event Contract Location

- Decision: Define websocket event envelope and payload models in `project/schemas.py`.
- Rationale: Aligns with existing shared-contract pattern used by agent schemas and enables one source of truth for backend + frontend validation.
- Alternatives considered: frontend-only schema parsing (drift risk), backend-only shape guarantees (insufficient for runtime UI safety).

## Decision 4: Routing Strategy

- Decision: Validate incoming event -> route by explicit `event_type` -> update destination view state.
- Rationale: Deterministic routing supports comprehensive testability and predictable behavior under interleaved streams.
- Alternatives considered: payload-shape inference routing (ambiguous), agent-channel-only routing (too coarse for multi-event flows).

## Decision 5: Reconnection Behavior

- Decision: Auto-reconnect with bounded retries and explicit state transitions (`connecting`, `connected`, `reconnecting`, `disconnected`, `failed`).
- Rationale: Meets reliability and UX requirements while preventing silent failures.
- Alternatives considered: manual reconnect only (poor UX), unbounded aggressive retries (operationally noisy).

## Decision 6: Simulator Design

- Decision: Provide built-in Streamlit simulator with deterministic scenarios and feed simulated events through the same validation/routing pipeline as live events.
- Rationale: Ensures parity and enables reliable demos/tests before full backend readiness.
- Alternatives considered: fixture-only tests (no interactive validation), backend-driven simulation only (tight coupling).

## Decision 7: State Persistence Scope

- Decision: Keep session state in memory only for v1.
- Rationale: Matches agreed scope and reduces implementation risk for initial release.
- Alternatives considered: local storage persistence (extra migration and reconciliation logic), server-side persistence (out of scope).

## Decision 8: Unknown/Invalid Event Handling

- Decision: Reject unsafe render paths, log structured diagnostics, continue processing subsequent valid events.
- Rationale: Preserves UI stability and observability under malformed/unexpected input.
- Alternatives considered: hard-fail connection on first invalid event (poor resilience), silently discard without diagnostics (poor maintainability).
