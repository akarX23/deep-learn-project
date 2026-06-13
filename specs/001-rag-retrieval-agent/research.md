# Research: RAG Kafka Worker Simplification

## Decision 1: Worker-Centric Startup Flow
- Decision: `worker.py` is the only startup entry point and owns threaded loop initialization plus startup topic presence check.
- Rationale: Keeps runtime orchestration explicit and removes service-layer indirection.
- Alternatives considered: FastAPI service lifecycle (out of scope), extra orchestration layer (unnecessary abstraction).

## Decision 2: `kafka.py` as the Kafka Ownership Boundary
- Decision: Keep Kafka connector initialization, producer/consumer creation, and consume/produce helper functions only in `kafka.py`.
- Rationale: Single ownership for Kafka lifecycle avoids scattered client logic across modules.
- Alternatives considered: Producer/consumer ownership in worker/agent modules (duplicates responsibilities).

## Decision 3: Direct Consumer-to-Agent Dispatch
- Decision: Consumer loop calls `agent.py` directly with typed inputs and receives typed output; no handler abstraction in primary flow.
- Rationale: Removes indirection and makes poll -> process -> publish path easier to follow and maintain.
- Alternatives considered: Keep handler abstraction/factory pattern (explicitly rejected in clarifications).

## Decision 4: Kafka-Agnostic Agent
- Decision: `agent.py` only returns processing output and never publishes to Kafka.
- Rationale: Clean separation between business processing and transport behavior.
- Alternatives considered: Agent-owned publish path (couples processing with transport).

## Decision 5: Simplified `helpers.py`
- Decision: Keep `helpers.py` limited to environment-value extraction helpers; no classes and no validators.
- Rationale: Matches simplification constraints and reduces unnecessary abstraction surface.
- Alternatives considered: Config classes/validation layers in this phase (deferred).

## Decision 6: Deferred Hardening as TODO Scope
- Decision: Advanced validation, edge-case handling, and deep exception taxonomy remain deferred with explicit TODO markers.
- Rationale: Current phase prioritizes core flow simplification and type-safe boundaries.
- Alternatives considered: Full hardening now (scope expansion beyond clarified requirement).

## Deferred TODO Scope
- Payload semantic validation beyond baseline schema checks.
- Retry and backoff policy tuning for consume/process/publish failures.
- Extended exception classes for transport and processing stages.
- Additional metrics instrumentation and throughput counters.
