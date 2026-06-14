# Contract: Planner Agent Kafka Topics

**Feature**: `004-planner-agent`  
**Version**: 1.0.0  
**Date**: 2026-06-13

This document defines the Kafka topic contracts for all events produced and consumed by the Planner Agent orchestrator.

---

## Topics Overview

| Topic | Direction | Producer | Consumer |
|---|---|---|---|
| `init-planner` | inbound | Backend Service | Planner Agent |
| `rag-request` | outbound | Planner Agent | RAG Worker |
| `teaching-request` | outbound | Planner Agent | Teaching Agent |
| `quiz-request` | outbound | Planner Agent | Quiz Agent (future) |
| `clarify-user-level` | outbound | Planner Agent | Backend / WebSocket |
| `workflow-complete` | outbound | Planner Agent | Backend / WebSocket |
| `rag-complete` | inbound (future) | RAG Worker | Planner Agent (resume) |
| `teaching-complete` | inbound (future) | Teaching Agent | Planner Agent (resume) |
| `quiz-complete` | inbound (future) | Quiz Agent | Planner Agent (resume) |

---

## Inbound: `init-planner`

**Published by**: Backend Service  
**Consumed by**: Planner Agent `worker.py`

```json
{
  "user_prompt": "Explain gradient descent to me",
  "user_level": [],
  "sid": "abc123",
  "file_paths": ["/uploads/notes.pdf"]
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `user_prompt` | string | ✓ | Raw user learning request |
| `user_level` | array[string] | ✓ | Empty → triggers level inference; non-empty → used directly |
| `sid` | string | ✓ | WebSocket session identifier |
| `file_paths` | array[string] | ✓ | Absolute paths; empty → RAG node skipped |

---

## Outbound: `rag-request`

**Published by**: Planner Agent `run_rag` node  
**Consumed by**: RAG Worker

```json
{
  "request_id": "a1b2c3d4e5f6",
  "user_prompt": "Explain gradient descent to me",
  "file_paths": ["/uploads/notes.pdf"],
  "sid": "abc123"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `request_id` | string | ✓ | UUID hex; used to resume graph on completion |
| `user_prompt` | string | ✓ | Forwarded from init-planner event |
| `file_paths` | array[string] | ✓ | Non-empty (conditional edge guarantees files present) |
| `sid` | string | ✓ | Session identifier |

---

## Outbound: `teaching-request`

**Published by**: Planner Agent `teach_node` (one event per user level)  
**Consumed by**: Teaching Agent

```json
{
  "request_id": "a1b2c3d4e5f6",
  "user_prompt": "Explain gradient descent to me",
  "user_level": "beginner",
  "rag_compiled": "## Key Concepts\n...",
  "sid": "abc123"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `request_id` | string | ✓ | Workflow correlation ID |
| `user_prompt` | string | ✓ | Original user prompt |
| `user_level` | string | ✓ | Single level (`beginner`, `intermediate`, `advanced`) |
| `rag_compiled` | string | ✓ | Empty string if RAG was not in workflow |
| `sid` | string | ✓ | Session identifier |

---

## Outbound: `quiz-request`

**Published by**: Planner Agent `run_quiz` node  
**Consumed by**: Quiz Agent (future)

```json
{
  "request_id": "a1b2c3d4e5f6",
  "user_prompt": "Explain gradient descent to me, then quiz me",
  "user_levels": ["beginner", "advanced"],
  "teaching_materials": {
    "beginner": "## Beginner explanation...",
    "advanced": "## Advanced explanation..."
  },
  "sid": "abc123"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `request_id` | string | ✓ | Workflow correlation ID |
| `user_prompt` | string | ✓ | Original user prompt |
| `user_levels` | array[string] | ✓ | All levels that received teaching content |
| `teaching_materials` | object | ✓ | Level → compiled teaching artifact mapping |
| `sid` | string | ✓ | Session identifier |

---

## Outbound: `clarify-user-level`

**Published by**: Planner Agent `infer_level` node (low confidence path)  
**Consumed by**: Backend Service / WebSocket layer

```json
{
  "request_id": "a1b2c3d4e5f6",
  "user_prompt": "teach me stuff",
  "sid": "abc123",
  "reason": "confidence below threshold (0.42 < 0.75)"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `request_id` | string | ✓ | Request that could not be classified |
| `user_prompt` | string | ✓ | Original prompt |
| `sid` | string | ✓ | Session for frontend notification |
| `reason` | string | ✓ | Human-readable explanation for clarification |

---

## Outbound: `workflow-complete`

**Published by**: Planner Agent `finish` node  
**Consumed by**: Backend Service / WebSocket layer

```json
{
  "request_id": "a1b2c3d4e5f6",
  "sid": "abc123",
  "rag_compiled": "## Key Concepts\n...",
  "teaching_materials": {
    "beginner": "## Beginner explanation..."
  },
  "quiz_content": ""
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `request_id` | string | ✓ | Workflow correlation ID |
| `sid` | string | ✓ | Session identifier |
| `rag_compiled` | string | ✓ | Empty string if RAG not in workflow |
| `teaching_materials` | object | ✓ | All teaching artifacts collected |
| `quiz_content` | string | ✓ | Empty string if quiz not requested |

---

## Inbound (Future Phase): Completion Events

These topics are bootstrapped but consumed in a future implementation phase. The planner will use them to resume the LangGraph workflow.

### `rag-complete`

```json
{
  "request_id": "a1b2c3d4e5f6",
  "compiled_material": "## Key Concepts\n...",
  "status": "complete"
}
```

### `teaching-complete`

```json
{
  "request_id": "a1b2c3d4e5f6",
  "user_level": "beginner",
  "teaching_material": "## Beginner explanation...",
  "status": "complete"
}
```

### `quiz-complete`

```json
{
  "request_id": "a1b2c3d4e5f6",
  "quiz_content": "Q1: What is ...",
  "status": "complete"
}
```

---

## Message Encoding

- All messages are JSON-serialized via `producer.send(topic, value=event.model_dump(mode="json"))`.
- Kafka key: not set (default None). Future phase may key by `sid` or `request_id` for partitioning.
- No schema registry in MVP; validation is done at application layer via Pydantic.
