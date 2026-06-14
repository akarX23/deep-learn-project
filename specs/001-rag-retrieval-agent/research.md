# Research: RAG Agent Parallel Page Processing

## Decision 1: Use LangGraph StateGraph fan-out for page-level independence
- Decision: Keep LangGraph as orchestration runtime and model page extraction as independent page tasks executed through StateGraph fan-out/fan-in semantics.
- Rationale: Reuses existing graph stack and keeps orchestration centralized in `agent.py` without introducing a second orchestration mechanism.
- Alternatives considered: Manual thread pool orchestration outside LangGraph (rejected: duplicates orchestration model and drifts from current stack).

## Decision 2: Enforce bounded parallelism via runtime concurrency configuration
- Decision: Cap in-flight page tasks using runtime concurrency setting sourced from env var and passed to graph invocation/runtime.
- Rationale: Prevents unbounded resource use while enabling parallel work.
- Alternatives considered: Unbounded parallel fan-out (rejected: resource risk and non-deterministic load impact).

## Decision 3: Environment variable contract for page parallelism
- Decision: Add a page-parallelism env variable for `agent.py` with behavior: default `4` when missing/invalid and clamp minimum to `1`.
- Rationale: Matches clarified requirement and allows runtime tuning without code changes.
- Alternatives considered: Startup hard-fail on invalid env (rejected: decreases operational resilience).

## Decision 4: No explicit batching layer in agent runtime
- Decision: Do not create additional batch-building logic for page requests.
- Rationale: Requirement explicitly delegates batching optimization to inference server and keeps agent logic simpler.
- Alternatives considered: Agent-side request batching queue (rejected: adds complexity and conflicts with clarified scope).

## Decision 5: Preserve per-page processing semantics
- Decision: Keep text/table/image extraction, relevance scoring, and status assignment per page equivalent to current behavior.
- Rationale: Feature intent is concurrency and throughput, not semantic processing changes.
- Alternatives considered: Redesign page extraction pipeline while adding concurrency (rejected: increases regression risk).

## Decision 6: Deterministic reduction of parallel results
- Decision: Merge page outputs into final `extracted_pages`, retained-page context, and errors using deterministic ordering keyed by source pointer sequence.
- Rationale: Stable outputs improve test determinism and preserve expected downstream behavior.
- Alternatives considered: Completion-order aggregation (rejected: introduces non-deterministic ordering in tests and output).

## Decision 7: Keep Kafka boundary unchanged
- Decision: Maintain current worker -> agent -> publish flow and keep `agent.py` Kafka-agnostic.
- Rationale: Parallelism is internal to page processing; transport architecture remains valid.
- Alternatives considered: Push concurrency into worker/Kafka layer (rejected: violates current ownership boundaries).