# Data Model: Planner Agent Orchestrator

**Feature**: `004-planner-agent`  
**Branch**: `005-add-planner-agent`  
**Date**: 2026-06-14

## 1. Internal Workflow State

### `PlannerState` (`TypedDict`, internal to `planner_agent/agent.py`)

| Field | Type | Description |
|---|---|---|
| `request_id` | `str` | Workflow correlation ID generated at init-event ingest |
| `user_prompt` | `str` | Original user request |
| `sid` | `str` | Session identifier |
| `user_levels` | `list[str]` | Final level list (provided or inferred) |
| `file_paths` | `list[str]` | Uploaded file paths |
| `quiz_requested` | `bool` | Whether quiz branch should run |
| `current_level` | `str` | Fan-out helper value for teaching branch |
| `rag_compiled` | `str` | Output material from RAG completion |
| `teaching_materials` | `dict[str, str]` | Aggregated teaching outputs by level |
| `quiz_content` | `str` | Output from quiz completion |
| `workflow_status` | `str` | `active` / `clarifying` / `complete` |

## 2. Inbound Event Models (Consumed by Single Worker)

| Topic | Schema | Handler |
|---|---|---|
| `init-planner` | `PlannerRequestEvent` | `PlannerAgent.run(...)` |
| `rag-complete` | `RAGCompletionEvent` | `PlannerAgent.resume(..., {"rag_compiled": ...})` |
| `teaching-complete` | `TeachingCompletionEvent` | `PlannerAgent.resume(..., {"teaching_materials": {level: content}})` |
| `quiz-complete` | `QuizCompletionEvent` | `PlannerAgent.resume(..., {"quiz_content": ...})` |

## 3. Outbound Event Models (Produced by Planner)

| Topic | Schema | Required Key |
|---|---|---|
| `rag` | `RAGRequestEvent` | `request_id` |
| `teaching-request` | `TeachingRequestEvent` | `request_id` |
| `quiz-request` | `QuizRequestEvent` | `request_id` |
| `clarify-user-level` | `ClarifyUserLevelEvent` | `request_id` |
| `workflow-complete` | `WorkflowCompleteEvent` | `request_id` |

## 4. Workflow Transitions

1. Consume `init-planner` and create `request_id`.
2. Run inference path or clarify path.
3. Dispatch agent request events with key=`request_id`.
4. Pause graph at checkpoint with `interrupt()` semantics.
5. Consume completion topic message.
6. Parse completion payload; derive state delta.
7. Resume graph with `Command(resume=delta)`.
8. Emit `workflow-complete` when terminal conditions are met.

## 5. Validation Rules

- All consumed and produced payloads must be schema-validated through `project/schemas.py`.
- Topic routing must be explicit by `message.topic`.
- `teaching_materials` merge semantics must preserve previously completed levels.
- Unknown topics and malformed payloads are logged and skipped without worker crash.
