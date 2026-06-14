# Data Model: Planner Agent Orchestrator

**Feature**: `004-planner-agent`  
**Branch**: `005-add-planner-agent`  
**Date**: 2026-06-13

---

## 1. LangGraph State Schema

### `PlannerState` (TypedDict — `planner_agent/agent.py`)

The shared mutable state flowing through all graph nodes. Keyed in `MemorySaver` by `thread_id = request_id`. Defined in `planner_agent/agent.py` (internal to the planner; not shared with other agents).

| Field | Type | Description |
|---|---|---|
| `request_id` | `str` | Auto-generated UUID4 assigned at graph entry |
| `user_prompt` | `str` | Raw user prompt from `PlannerRequestEvent` |
| `sid` | `str` | Session ID from `PlannerRequestEvent` |
| `user_levels` | `list[str]` | Finalized list of user levels (post-inference or provided) |
| `file_paths` | `list[str]` | Absolute paths to uploaded files (from event) |
| `quiz_requested` | `bool` | Whether quiz was detected (LLM inference result) |
| `rag_compiled` | `str` | Compiled material returned by RAG agent (filled after RAG completes) |
| `teaching_materials` | `dict[str, str]` | Level → teaching artifact mapping (filled as teaching nodes complete) |
| `quiz_content` | `str` | Quiz content (filled after quiz agent completes) |
| `workflow_status` | `str` | One of: `"active"`, `"clarifying"`, `"complete"` |

**Initialization**: Created at entry node; `request_id` generated with `uuid.uuid4().hex`, all output fields default to empty.

---

## 2. Kafka Event Payloads (Pydantic models — `project/schemas.py`)

### `PlannerRequestEvent` *(existing — consumed by planner)*

| Field | Type | Description |
|---|---|---|
| `user_prompt` | `str` | User's learning request |
| `user_level` | `List[str]` | Pre-defined levels (empty → trigger inference) |
| `sid` | `str` | Session ID for WebSocket routing |
| `file_paths` | `List[str]` | Uploaded file paths (empty → skip RAG) |

### `TeachingRequestEvent` *(new)*

| Field | Type | Description |
|---|---|---|
| `request_id` | `str` | Workflow correlation ID |
| `user_prompt` | `str` | Original user prompt |
| `user_level` | `str` | Single target level (one event per level) |
| `rag_compiled` | `str` | RAG material to inform teaching (empty string if no RAG) |
| `sid` | `str` | Session ID |

### `QuizRequestEvent` *(new)*

| Field | Type | Description |
|---|---|---|
| `request_id` | `str` | Workflow correlation ID |
| `user_prompt` | `str` | Original user prompt |
| `user_levels` | `List[str]` | All levels that received teaching content |
| `teaching_materials` | `dict[str, str]` | Level → compiled teaching material |
| `sid` | `str` | Session ID |

### `ClarifyUserLevelEvent` *(new)*

| Field | Type | Description |
|---|---|---|
| `request_id` | `str` | Workflow correlation ID |
| `user_prompt` | `str` | Original user prompt |
| `sid` | `str` | Session ID |
| `reason` | `str` | Brief explanation (e.g., "confidence below threshold") |

### `WorkflowCompleteEvent` *(new)*

| Field | Type | Description |
|---|---|---|
| `request_id` | `str` | Workflow correlation ID |
| `sid` | `str` | Session ID |
| `rag_compiled` | `str` | Final RAG material (empty if RAG not in workflow) |
| `teaching_materials` | `dict[str, str]` | Level → teaching artifact |
| `quiz_content` | `str` | Quiz content (empty if quiz not requested) |

---

## 3. LLM Inference Schemas

### `LevelInferenceResult` *(Pydantic — `project/schemas.py`)* Lives in `project/schemas.py` as it crosses the LLM→planner boundary.

| Field | Type | Description |
|---|---|---|
| `level` | `UserLevelEnum` | Inferred user knowledge level |
| `confidence` | `float` | Confidence score in [0.0, 1.0] |
| `quiz_requested` | `bool` | Whether LLM detected quiz intent in prompt |

---

## 4. Enums (additions to `project/schemas.py`)

### `UserLevelEnum(str, Enum)`

```
BEGINNER     = "beginner"
INTERMEDIATE = "intermediate"
ADVANCED     = "advanced"
```

**Note**: `OutputMode` in `TeachingAgentInput` already has equivalent values. `UserLevelEnum` is the planner-side enum used in inference results and Kafka event payloads. Both enums coexist; they can be unified in a future refactor (TODO marker).

---

## 5. Kafka Topic Registry (additions to `project/topics.py`)

### `PlannerAgentTopics(str, Enum)` *(new enum)*

| Enum Value | Topic String | Direction |
|---|---|---|
| `TEACHING_REQUEST` | `teaching-request` | planner → teaching agent |
| `QUIZ_REQUEST` | `quiz-request` | planner → quiz agent |
| `CLARIFY_USER_LEVEL` | `clarify-user-level` | planner → frontend |
| `WORKFLOW_COMPLETE` | `workflow-complete` | planner → frontend |

### Completion topics *(consumed in future phase — defined now for bootstrap)*

| Enum | Topic String | Direction |
|---|---|---|
| `AgentCompletionTopics.TEACHING_COMPLETE` | `teaching-complete` | teaching agent → planner |
| `AgentCompletionTopics.QUIZ_COMPLETE` | `quiz-complete` | quiz agent → planner |

---

## 6. Graph Node Summary

| Node Name | Input State Fields | Output State Fields | Kafka Event Produced |
|---|---|---|---|
| `infer_level` | `user_prompt`, `user_level` (from event) | `user_levels`, `quiz_requested` | `clarify-user-level` (if low confidence) |
| `run_rag` | `request_id`, `user_prompt`, `file_paths`, `sid` | — (awaits resume) | `rag-request` |
| `teach_node` (fan-out per level) | `request_id`, `user_prompt`, `user_level`, `rag_compiled`, `sid` | — (awaits resume) | `teaching-request` |
| `run_quiz` | `request_id`, `user_prompt`, `user_levels`, `teaching_materials`, `sid` | — (awaits resume) | `quiz-request` |
| `finish` | all state fields | `workflow_status = "complete"` | `workflow-complete` |

---

## 7. Graph Edges & Conditional Logic

```
[START]
  └─► infer_level
        ├─[confidence < threshold OR error]─► clarify_and_end ──► [END]
        └─[confidence ≥ threshold]──────────► has_files?
              ├─[True]──► run_rag  ──interrupt──► (resume) ──► fan_out_teach
              └─[False]─────────────────────────────────────► fan_out_teach
                                                                    │
                                            (Send per level) ──► teach_node x N
                                                                    │
                                                              quiz_requested?
                                                   ├─[True]─► run_quiz ──interrupt──► (resume) ──► finish
                                                   └─[False]────────────────────────────────────► finish
                                                                                                    │
                                                                                                 [END]
```

**LangGraph mechanism**:
- `interrupt()` is called inside `run_rag`, `teach_node`, and `run_quiz` after publishing the Kafka event.
- State is checkpointed in `MemorySaver` under `thread_id = request_id`.
- Graph resumes via `graph.invoke(Command(resume=completion_payload), config={"configurable": {"thread_id": request_id}})` when a completion event arrives (consumer side — future phase). The `Command(resume=...)` payload delivers the agent's output directly back into the interrupted node without re-running prior nodes.
- `Command` is imported from `langgraph.types`.
