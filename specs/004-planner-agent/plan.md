# Implementation Plan: Planner Agent Orchestrator

**Branch**: `005-add-planner-agent` | **Date**: 2026-06-13 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/004-planner-agent/spec.md`

## Summary

The Planner Agent is a LangGraph-based orchestrator that consumes `init-planner` Kafka events, infers user knowledge level (or uses provided levels), and dispatches work to RAG, Teaching, and Quiz agents via Kafka. The graph uses `MemorySaver` for in-process checkpointing and `interrupt()` to pause after each agent dispatch, ready for future resumption from agent completion events. The implementation mirrors the `rag_agent/` directory structure and reuses the `litellm` + `kafka-python` stack already present in the project.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: `langgraph>=1.2.0` (venv: 1.2.2), `langchain-core>=1.4.0` (venv: 1.4.0), `kafka-python`, `litellm`, `pydantic>=2`  
**Storage**: In-memory only (`MemorySaver`); no external persistence in MVP  
**Testing**: `pytest` (root `pytest.ini`); tests under `planner_agent/tests/`  
**Target Platform**: Linux server (same as other agents)  
**Project Type**: Background worker / Kafka consumer + LangGraph orchestrator  
**Performance Goals**: Level inference < 2s per request; workflow event dispatch < 500ms after level finalized  
**Constraints**: Memory-only state; no retry logic; no async; single LLM call for both inference tasks  
**Scale/Scope**: One LangGraph `thread_id` per request; concurrent requests are separate graph invocations

## Constitution Check

*Pre-design gate — all items pass:*

- **Code Quality Gate**: `ruff check project planner_agent` + `ruff format --check project planner_agent` + `python -m compileall project planner_agent -q`. Failure blocks merge.
- **Testing Gate**: Unit tests for `infer_level` node (confidence routing, level bypass), node Kafka event production (`run_rag`, `teach_node`, `run_quiz`), graph conditional edges, worker consume loop. Monkeypatch `call_llm` and producer — same pattern as `rag_agent/tests/`.
- **UX Consistency Gate**: N/A — no user-facing UI. Event payload shapes documented in `contracts/planner-kafka-contract.md`.
- **Performance Gate**: Level inference validated under 2s by unit test timing (monkeypatched LLM). Workflow dispatch validated under 500ms in integration smoke test.
- **Maintainability Gate**: Deferred concerns (consumer resumption, timeout, persistence, retry) marked with `# TODO:`. Non-obvious LangGraph decisions (Send API, interrupt/resume) documented in `research.md`.

*Post-design gate — all items pass:*
- `PlannerState` TypedDict cleanly scoped; no shared mutable singletons.
- All Kafka topics registered in `project/topics.py` and bootstrapped at backend startup.
- `UserLevelEnum` vs `OutputMode` coexistence documented with TODO for future unification.

## Project Structure

### Documentation (this feature)

```text
specs/004-planner-agent/
├── plan.md                          # This file
├── research.md                      # Phase 0: decisions and rationale
├── data-model.md                    # Phase 1: state schema, event payloads, graph edges
├── quickstart.md                    # Phase 1: dev setup and workflow reference
├── contracts/
│   └── planner-kafka-contract.md   # Phase 1: all Kafka topic contracts
└── tasks.md                         # Phase 2 (/speckit.tasks output)
```

### Source Code (repository root)

```text
planner_agent/
├── __init__.py
├── agent.py        # PlannerAgent: PlannerState TypedDict (internal), StateGraph, all nodes
├── config.py       # get_llm_config() — reads PLANNER_TEXT_* env vars
├── kafka.py        # make_producer() — kafka-python producer factory
├── prompts.py      # LEVEL_QUIZ_INFERENCE_PROMPT
├── worker.py       # Entry point: init-planner consumer loop
└── tests/
    ├── __init__.py
    ├── inputs/
    │   └── sample_input.json
    ├── test_planner_agent.py       # Graph node unit tests
    ├── test_level_inference.py     # infer_level: confidence routing, level bypass
    └── test_worker_runtime.py      # Worker: consume loop, basic error handling

project/
├── schemas.py    # + UserLevelEnum, LevelInferenceResult (shared LLM contract)
│                 #   + TeachingRequestEvent, QuizRequestEvent,
│                 #   + ClarifyUserLevelEvent, WorkflowCompleteEvent
│                 #   (PlannerState TypedDict is in planner_agent/agent.py, NOT here)
└── topics.py     # + PlannerAgentTopics, AgentCompletionTopics enums

requirements.txt  # + langgraph>=1.2.0, langchain-core>=1.4.0 (already in venv)
```

**Structure Decision**: New top-level `planner_agent/` package mirroring `rag_agent/` exactly. Shared schemas and topic registry extended in-place in `project/`.

## Complexity Tracking

*No constitution violations. All design choices follow simplest path:*

| Decision | Rationale |
|---|---|
| `MemorySaver` (in-memory) | No infra dependency; acceptable data loss per clarification Q3 |
| Single LLM call for level + quiz | Reduces latency; both inferences share the same prompt |
| `kafka-python` sync producer | Already in stack; no additional dependency |
| `interrupt()` without consumer resumption | Unblocks graph implementation now; consumer side is future TODO |

---

## Phase 0: Research (Complete)

See [research.md](research.md) for full decision log. Key resolutions:

- LangGraph `StateGraph` + `MemorySaver` + `interrupt()` chosen for orchestration
- `Send` API for teaching fan-out (dynamic, per-level)
- Single JSON-structured LLM call returns `{level, confidence, quiz_requested}`
- `kafka-python` sync producer reused from existing stack
- Directory structure mirrors `rag_agent/`
- New Kafka topics: `teaching-request`, `quiz-request`, `clarify-user-level`, `workflow-complete`
- New schemas: `UserLevelEnum`, `LevelInferenceResult`, `TeachingRequestEvent`, `QuizRequestEvent`, `ClarifyUserLevelEvent`, `WorkflowCompleteEvent`
- New env vars: `PLANNER_TEXT_MODEL`, `PLANNER_TEXT_API_BASE`, `PLANNER_TEXT_API_KEY`, `PLANNER_TEXT_TEMPERATURE`, `PLANNER_TEXT_MAX_TOKENS`, `PLANNER_LEVEL_CONFIDENCE_THRESHOLD`, `PLANNER_KAFKA_BOOTSTRAP_SERVERS`

---

## Phase 1: Design & Contracts (Complete)

### Graph State: `PlannerState` (TypedDict in `planner_agent/agent.py`)

```python
class PlannerState(TypedDict):
    request_id: str              # uuid4().hex — generated at graph entry
    user_prompt: str
    sid: str
    user_levels: list[str]       # finalized after infer_level node
    file_paths: list[str]
    quiz_requested: bool          # set by infer_level
    rag_compiled: str             # filled on RAG resume (future phase)
    teaching_materials: dict[str, str]   # level -> artifact (future phase)
    quiz_content: str             # filled on quiz resume (future phase)
    workflow_status: str          # "active" | "clarifying" | "complete"
```

> **Placement**: `PlannerState` is defined in `planner_agent/agent.py` (internal graph state; not shared with other agents). Compare with `AgentState` in `rag_agent/agent.py` which follows the same pattern.

### LangGraph State Graph

```
[START]
  └─► infer_level
        ├─[low confidence / LLM error]──► clarify_and_end ──► [END]
        └─[finalized]───────────────────► route_rag
              ├─[file_paths non-empty]──► run_rag ──interrupt()──► (resume: future)
              │                               └──► fan_out_teach
              └─[no files]─────────────────────────────────────► fan_out_teach
                                                                        │
                                                            Send(level) × N
                                                                        │
                                                              teach_node(level)
                                                           ──interrupt()──► (resume: future)
                                                                        │
                                                               route_quiz
                                              ├─[quiz_requested=True]──► run_quiz ──interrupt()──► (resume: future)
                                              └─[quiz_requested=False]─────────────────────────► finish
                                                                                                       │
                                                                                                    [END]
```

### Node Implementation Summary

| Node | Core Action | Kafka Topic Produced | Interrupt? |
|---|---|---|---|
| `infer_level` | LLM call → set `user_levels`, `quiz_requested` | `clarify-user-level` (low conf path only) | No |
| `run_rag` | Produce rag event → interrupt | `rag-request` | Yes |
| `teach_node` (×N via Send) | Produce teaching event per level → interrupt | `teaching-request` | Yes |
| `run_quiz` | Produce quiz event → interrupt | `quiz-request` | Yes |
| `finish` | Produce workflow-complete event | `workflow-complete` | No |

### Graph Resumption (Future Phase)

Each interrupted node is resumed via the `Command` API:

```python
from langgraph.types import Command

graph.invoke(
    Command(resume=completion_payload),
    config={"configurable": {"thread_id": request_id}},
)
```

`Command(resume=...)` delivers the agent's completion payload directly back into the interrupted node without re-running prior nodes. The Kafka consumer (future phase) will call this after receiving `rag-complete`, `teaching-complete`, or `quiz-complete` events.

### Schemas in `project/schemas.py` (Shared Kafka contracts)

- `UserLevelEnum(str, Enum)`: `BEGINNER`, `INTERMEDIATE`, `ADVANCED`
- `LevelInferenceResult(BaseModel)`: `level`, `confidence`, `quiz_requested`
- `TeachingRequestEvent(BaseModel)`: `request_id`, `user_prompt`, `user_level`, `rag_compiled`, `sid`
- `QuizRequestEvent(BaseModel)`: `request_id`, `user_prompt`, `user_levels`, `teaching_materials`, `sid`
- `ClarifyUserLevelEvent(BaseModel)`: `request_id`, `user_prompt`, `sid`, `reason`
- `WorkflowCompleteEvent(BaseModel)`: `request_id`, `sid`, `rag_compiled`, `teaching_materials`, `quiz_content`

> **Note**: `PlannerState` (TypedDict) is **not** in `project/schemas.py` — it lives in `planner_agent/agent.py` as internal graph state, same as `AgentState` in `rag_agent/agent.py`.

### `LEVEL_QUIZ_INFERENCE_PROMPT` (in `planner_agent/prompts.py`)

```
Given the user prompt below, determine:
1. The user's knowledge level: one of "beginner", "intermediate", or "advanced"
2. A confidence score between 0.0 and 1.0
3. Whether the user is requesting a quiz/test/assessment

Respond ONLY with a JSON object:
{{"level": "...", "confidence": 0.0, "quiz_requested": false}}

User prompt: {user_prompt}
```

### Artifacts Generated

- [data-model.md](data-model.md) — `PlannerState`, all event schemas, topic registry additions, graph edge diagram
- [contracts/planner-kafka-contract.md](contracts/planner-kafka-contract.md) — all inbound/outbound topic contracts with example payloads
- [quickstart.md](quickstart.md) — env vars, run commands, manual test examples, module responsibilities
