# Contract: Planner Agent Kafka Topics

**Feature**: `004-planner-agent`  
**Version**: 1.1.0  
**Date**: 2026-06-14

This contract defines all planner-consumed and planner-produced Kafka events for the single-worker, multi-topic consumer runtime.

## 1. Topic Matrix

| Topic | Direction | Producer | Consumer |
|---|---|---|---|
| `init-planner` | inbound | Backend Service | Planner Worker |
| `rag-complete` | inbound | RAG Worker | Planner Worker |
| `teaching-complete` | inbound | Teaching Agent | Planner Worker |
| `quiz-complete` | inbound | Quiz Agent | Planner Worker |
| `rag` | outbound | Planner Agent | RAG Worker |
| `teaching-request` | outbound | Planner Agent | Teaching Agent |
| `quiz-request` | outbound | Planner Agent | Quiz Agent |
| `clarify-user-level` | outbound | Planner Agent | Backend/WebSocket |
| `workflow-complete` | outbound | Planner Agent | Backend/WebSocket |

## 2. Worker Routing Rules

- Single consumer subscribes to all inbound topics.
- Routing key is `message.topic`.
- Topic-specific schema parse is mandatory before handler invocation.
- Handler mapping:
  - `init-planner` -> `PlannerAgent.run(payload)`
  - completion topics -> `PlannerAgent.resume(request_id, outputs)`

## 3. Keying Rule for Produced Events

All planner-produced events MUST set Kafka message key to `request_id`.

## 4. Payload Contracts

### 4.1 `init-planner` (inbound)

Schema: `PlannerRequestEvent`

```json
{
  "user_prompt": "Explain gradient descent",
  "user_level": [],
  "sid": "abc123",
  "file_paths": ["/uploads/notes.pdf"]
}
```

### 4.2 `rag` (outbound)

Schema: `RAGRequestEvent`

```json
{
  "request_id": "a1b2c3d4",
  "session_ctx": {"sid": "abc123"},
  "user_request": "Explain gradient descent",
  "file_paths": ["/uploads/notes.pdf"],
  "source": "planner-agent"
}
```

### 4.3 `teaching-request` (outbound)

Schema: `TeachingRequestEvent`

```json
{
  "request_id": "a1b2c3d4",
  "user_prompt": "Explain gradient descent",
  "user_level": "beginner",
  "rag_compiled": "## Key concepts",
  "sid": "abc123"
}
```

### 4.4 `quiz-request` (outbound)

Schema: `QuizRequestEvent`

```json
{
  "request_id": "a1b2c3d4",
  "user_prompt": "Explain and quiz me",
  "user_levels": ["beginner"],
  "teaching_materials": {"beginner": "lesson"},
  "sid": "abc123"
}
```

### 4.5 Completion Topics (inbound)

- `rag-complete` -> `RAGCompletionEvent`
- `teaching-complete` -> `TeachingCompletionEvent`
- `quiz-complete` -> `QuizCompletionEvent`

Completion payloads are transformed into resume deltas and passed into graph resumption via `Command(resume=...)`.

### 4.6 `clarify-user-level` (outbound)

Schema: `ClarifyUserLevelEvent`

### 4.7 `workflow-complete` (outbound)

Schema: `WorkflowCompleteEvent`

## 5. Error Handling Contract

- Unknown topics: log warning and ignore.
- Schema validation failures: log exception and continue loop.
- Planner handler failures: log exception and continue loop.
- No retries/transactions required in MVP.
