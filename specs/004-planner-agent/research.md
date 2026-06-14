# Research: Planner Agent Orchestrator

**Feature**: `004-planner-agent`  
**Branch**: `005-add-planner-agent`  
**Date**: 2026-06-13

---

## Decision 1: LangGraph State Graph Architecture

**Decision**: Use LangGraph `StateGraph` with `TypedDict`-based `PlannerState` as the shared graph state — same pattern as `rag_agent/agent.py`. Graph resumption uses the `Command` API: `graph.invoke(Command(resume=completion_payload), config={"configurable": {"thread_id": request_id}})`.

**Rationale**: LangGraph 1.2.x (already in venv) provides `StateGraph`, `interrupt()`, `Command`, and `MemorySaver` out of the box. `interrupt()` halts the graph at a node and checkpoints state. Resumption via `Command(resume=...)` is the idiomatic LangGraph pattern — it delivers the agent's completion payload back into the graph at the point of interruption, without re-running prior nodes. Using the same TypedDict + `StateGraph` pattern as the existing RAG agent keeps the codebase consistent.

**Alternatives considered**:
- `graph.invoke(None, config)`: resumes without a payload; requires reading state from an external store to get the completion result.
- Celery task chains: no graph state sharing, harder fan-out resumption.
- Custom state machine dict: more boilerplate, no built-in interrupt/checkpoint.

---

## Decision 2: State Checkpointing with MemorySaver

**Decision**: Use LangGraph's `MemorySaver` as the checkpointer (in-memory only, keyed by `thread_id = request_id`).

**Rationale**: `MemorySaver` requires no external infrastructure, stores the full graph state keyed by `thread_id`, and supports `interrupt()`/resume seamlessly. Since spec mandates memory-only persistence (clarification Q3: A), this is the correct choice. When the planner restarts, state is lost — acceptable for MVP.

**Alternatives considered**:
- `SqliteSaver` / `PostgresSaver`: adds infra dependency, deferred to future phase (TODO marker).
- Custom dict cache: doesn't integrate with LangGraph's interrupt/resume mechanism.

---

## Decision 3: Fan-out for Teaching Agent via Send API

**Decision**: Use LangGraph's `Send` API for fan-out over user levels — `[Send("teach_node", {"level": lvl}) for lvl in state["user_levels"]]`. Each teaching node execution is independent and processes a single level.

**Rationale**: `Send` is the idiomatic LangGraph pattern for dynamic parallel fan-out where the number of branches is only known at runtime (i.e., the number of user levels). It avoids manually spawning threads and integrates cleanly with the `StateGraph` reducer pattern.

**Alternatives considered**:
- `asyncio.gather` inside a node: requires async graph, adds complexity.
- Multiple static nodes per level: not extensible to variable number of levels.

---

## Decision 4: Level Inference and Quiz Detection via Single LLM Call

**Decision**: A single structured LLM call (JSON response) returns both inferred user level + confidence score and quiz intent flag. Planner uses its own LiteLLM configuration surface (`PLANNER_TEXT_*`) and does not depend on rag_agent runtime configuration.

**Rationale**: Both inferences operate on the same prompt. One JSON-structured call with fields `{"level": "beginner|intermediate|advanced", "confidence": 0.0-1.0, "quiz_requested": true|false}` minimizes latency and branching while preserving determinism. Planner-local config enforces service ownership boundaries and avoids hidden coupling to rag settings.

**Alternatives considered**:
- Two separate LLM calls: doubles latency for no additional accuracy benefit.
- Regex/keyword matching for quiz intent: brittle, low quality, superseded by clarification Q1 response (LLM-based).

---

## Decision 5: Kafka Integration Pattern

**Decision**: Use `kafka-python` producer (same as backend service) for publishing events. Consumer side is **not implemented** in this phase — graph resumption from Kafka is a TODO. The Kafka `producer.send(topic, value=payload)` call happens inside each node before `interrupt()`.

**Rationale**: The user explicitly stated "The consumer flow is not required currently, only plan the lang graph state graph." Producer calls give the downstream agents their trigger payloads. `interrupt()` pauses the graph at that point, and the `thread_id=request_id` checkpoint means state can be resumed when a completion event arrives (in a future phase).

**Alternatives considered**:
- AsyncKafkaProducer: overkill for synchronous node execution.
- REST webhooks: not in current infrastructure.

---

## Decision 6: Directory Structure

**Decision**: Mirror `rag_agent/` layout exactly:

```
planner_agent/
├── __init__.py
├── agent.py          # PlannerAgent class + StateGraph + nodes
├── config.py         # LLMConfig, get_llm_config(), env vars
├── kafka.py          # producer factory (mirrors rag_agent/kafka.py)
├── prompts.py        # LEVEL_QUIZ_INFERENCE_PROMPT template
├── worker.py         # entry point: consume init-planner, invoke agent
└── tests/
    ├── __init__.py
    ├── inputs/
    │   └── sample_input.json
    ├── test_planner_agent.py
    ├── test_level_inference.py
    └── test_worker_runtime.py
```

**Rationale**: Spec FR-013 explicitly requires following the `rag_agent` pattern. Consistent directory structure makes navigation, onboarding, and tooling (pytest, ruff) straightforward.

---

## Decision 7: New Kafka Topics

**Decision**: Add the following topics to `project/topics.py` under a new `PlannerAgentTopics` enum:
- `teaching-request` — planner → teaching agent
- `quiz-request` — planner → quiz agent
- `clarify-user-level` — planner → frontend/websocket
- `workflow-complete` — planner → frontend/websocket

RAG already has `rag` (request) and `rag-complete` (completion). Teaching and quiz completion topics (`teaching-complete`, `quiz-complete`) are defined but consumed by the planner in a future phase.

**Rationale**: Centralised topic registry in `project/topics.py` ensures all topics are bootstrapped at backend startup (existing `get_all_topic_names()` aggregator). Adding a `PlannerAgentTopics` enum follows the existing `PlannerTopics` / `RAGTopics` pattern.

---

## Decision 8: Schema Placement

**Decision**: 
- `PlannerState` (TypedDict) lives in `planner_agent/agent.py` — it is internal graph state, not shared with other agents.
- Shared inter-agent Kafka event schemas (`UserLevelEnum`, `LevelInferenceResult`, `TeachingRequestEvent`, `QuizRequestEvent`, `ClarifyUserLevelEvent`, `WorkflowCompleteEvent`) continue to live in `project/schemas.py` per existing convention.

**Rationale**: `PlannerState` is a LangGraph implementation detail used exclusively within the planner's `StateGraph`. Placing it in `project/schemas.py` would pollute the shared contract layer with internal orchestration state. `AgentState` in `rag_agent/agent.py` follows the same pattern — internal TypedDicts stay in the agent module. Kafka event payloads, by contrast, cross agent boundaries and belong in the shared `project/` layer.

**Alternatives considered**:
- All schemas in `project/schemas.py`: over-shares internal state, couples other agents to planner implementation details.
- Separate `planner_agent/schemas.py`: workable but unnecessary indirection since `agent.py` is the only consumer.

---

## Decision 9: Type-Safety and Schema Boundary Enforcement

**Decision**: Treat all planner message boundaries as strict schema boundaries. Inbound and outbound Kafka payloads are parsed/serialized through `project/schemas.py` models, and planner function signatures are explicitly typed. `Any` is prohibited except unavoidable interop boundaries.

**Rationale**: The planner is an orchestrator and integration hub. Strong typing plus schema-first boundaries reduce runtime contract drift and improve refactor safety.

**Alternatives considered**:
- Dict-only payload handling without model parse/serialize: faster to write, but weak guarantees and higher regression risk.
- Broad `Any` usage in graph nodes: convenient initially, but erodes static guarantees and discoverability.

---

## Decision 10: Stage-Level Observability

**Decision**: Emit logs at every major planner stage with level discipline while keeping existing logger configuration unchanged.

**Rationale**: Fine-grained logging is required for request lifecycle tracing (`request_id`) and debugging of fan-out/interrupt/resume behavior in a memory-only MVP.

**Alternatives considered**:
- Sparse logging only on errors: insufficient for operational debugging.
- Replacing logger configuration: unnecessary for this phase and explicitly out of scope.

---

## Environment Variables (following rag_agent pattern)

| Variable | Default | Purpose |
|---|---|---|
| `PLANNER_TEXT_MODEL` | `gpt-4o-mini` | LLM model for inference |
| `PLANNER_TEXT_API_BASE` | — | LiteLLM api_base override |
| `PLANNER_TEXT_API_KEY` | — | LiteLLM api_key override |
| `PLANNER_TEXT_TEMPERATURE` | `0.1` | Temperature for structured JSON output |
| `PLANNER_TEXT_MAX_TOKENS` | `200` | Low token ceiling (structured JSON response) |
| `PLANNER_LEVEL_CONFIDENCE_THRESHOLD` | `0.75` | Min confidence to finalize level |
| `PLANNER_KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address |
