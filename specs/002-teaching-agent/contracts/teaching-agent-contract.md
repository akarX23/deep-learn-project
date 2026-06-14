# Contract: Teaching Agent — Planner–Teaching Kafka Interface

## Purpose
Defines the full contract between the Planner Agent and the Teaching Agent.

At runtime, all communication flows through Kafka — the Planner publishes a
`TeachingRequestEvent` to the `"teaching"` topic; the Teaching Agent worker consumes it,
runs the core pipeline, and publishes a `TeachingCompletionEvent` to `"teaching-complete"`.
The core agent I/O schemas (`TeachingAgentInput` / `TeachingAgentOutput`) are the internal
contract used within the agent itself. All Pydantic v2 models live in `project/schemas.py`.

---

## Kafka Inbound: TeachingRequestEvent

Published by the Planner Agent to topic `"teaching"`.

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_ctx": {
    "session_id": "sess-abc-123",
    "user_id": "user-456",
    "trace_id": "trace-789"
  },
  "topic": "Binary Search Tree",
  "output_mode": "intermediate",
  "context": "User previously studied arrays and linked lists in this session.",
  "created_at": "2026-06-13T10:00:00Z",
  "source": "planner-agent"
}
```

### Field constraints

| Field | Type | Required | Constraints |
|---|---|---|---|
| request_id | string | Yes | Non-empty; unique per request; assigned by Planner |
| session_ctx | object | Yes | May be empty `{}`; never null |
| topic | string | Yes | Non-empty after whitespace strip |
| output_mode | string | Yes | One of: `"beginner"`, `"intermediate"`, `"advanced"` |
| context | string | Yes | May be empty string; never null |
| created_at | string or null | No | ISO 8601 UTC timestamp |
| source | string or null | No | Source identifier |

---

## Kafka Outbound: TeachingCompletionEvent

Published by the Teaching Agent to topic `"teaching-complete"` after every request.

### Success variant

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_ctx": {
    "session_id": "sess-abc-123",
    "user_id": "user-456",
    "trace_id": "trace-789"
  },
  "topic": "Binary Search Tree",
  "output_mode": "intermediate",
  "status": "ok",
  "content": {
    "explanation": "## Binary Search Tree\n\nA BST is a node-based data structure...",
    "diagram": "graph TD\n  A[Root: 8] --> B[Left: 3]\n  A --> C[Right: 10]",
    "notes": "## Key Properties\n\n- BST property: left < node < right\n- Average search: O(log n)",
    "example": "```python\nclass Node:\n    def __init__(self, val):\n        self.val = val\n```"
  },
  "tokens_used": 847,
  "model": "groq/llama-3.3-70b-versatile",
  "started_at": "2026-06-13T10:00:00Z",
  "completed_at": "2026-06-13T10:00:03Z",
  "duration_ms": 3012,
  "errors": [],
  "source": "teaching-agent"
}
```

### Error variant

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_ctx": {
    "session_id": "sess-abc-123",
    "user_id": "user-456"
  },
  "topic": "",
  "output_mode": "beginner",
  "status": "error",
  "content": null,
  "tokens_used": 0,
  "model": "groq/llama-3.3-70b-versatile",
  "started_at": "2026-06-13T10:00:00Z",
  "completed_at": "2026-06-13T10:00:00Z",
  "duration_ms": 0,
  "errors": ["topic cannot be empty"],
  "source": "teaching-agent"
}
```

### TeachingCompletionEvent field constraints

| Field | Type | Constraints |
|---|---|---|
| request_id | string | Verbatim from `TeachingRequestEvent`; never modified |
| session_ctx | object | Verbatim from `TeachingRequestEvent`; never modified |
| topic | string | From request |
| output_mode | string | From request |
| status | string | Exactly `"ok"` or `"error"` |
| content | object or null | Non-null when `status: "ok"`; null when `status: "error"` |
| tokens_used | integer | >= 0; `0` on error |
| model | string | Non-empty model identifier |
| started_at | string | ISO 8601 UTC |
| completed_at | string | ISO 8601 UTC |
| duration_ms | integer | >= 0 |
| errors | array | Empty on success; one or more messages on error |
| source | string | Always `"teaching-agent"` |

---

## Core Agent I/O (internal — used inside the worker)

### Request Schema: TeachingAgentInput

```json
{
  "topic": "Binary Search Tree",
  "output_mode": "intermediate",
  "context": "User previously studied arrays and linked lists in this session."
}
```

### Field constraints

| Field        | Type   | Required | Constraints                                      |
|--------------|--------|----------|--------------------------------------------------|
| topic        | string | Yes      | Non-empty after whitespace strip                 |
| output_mode  | string | Yes      | One of: `"beginner"`, `"intermediate"`, `"advanced"` |
| context      | string | Yes      | May be empty string; never null                  |

---

## Response Schema: TeachingAgentOutput — Success

```json
{
  "status": "ok",
  "output_mode": "intermediate",
  "content": {
    "explanation": "## Binary Search Tree\n\nA Binary Search Tree (BST) is a node-based data structure...",
    "diagram": "graph TD\n  A[Root: 8] --> B[Left: 3]\n  A --> C[Right: 10]\n  B --> D[Left: 1]\n  B --> E[Right: 6]",
    "notes": "## Key Properties\n\n- BST property: left < node < right\n- Average search: O(log n)\n- Worst case (sorted input): O(n)",
    "example": "```python\nclass Node:\n    def __init__(self, val):\n        self.val = val\n        self.left = self.right = None\n```"
  },
  "metadata": {
    "topic": "Binary Search Tree",
    "tokens_used": 847,
    "model": "claude-sonnet-4-6"
  }
}
```

## Response Schema: TeachingAgentOutput — Error

```json
{
  "status": "error",
  "output_mode": "intermediate",
  "content": null,
  "metadata": {
    "topic": "Binary Search Tree",
    "tokens_used": 0,
    "model": "claude-sonnet-4-6"
  }
}
```

### Response field constraints

| Field                   | Type              | Constraints                                                    |
|-------------------------|-------------------|----------------------------------------------------------------|
| status                  | string            | Exactly `"ok"` or `"error"`                                    |
| output_mode             | string            | Mirrors input `output_mode`                                    |
| content                 | object or null    | Non-null when `status: "ok"`; null when `status: "error"`      |
| content.explanation     | string            | Non-empty markdown; structure varies by mode                   |
| content.diagram         | string or null    | Valid Mermaid syntax or null; always non-null in beginner mode |
| content.notes           | string            | Non-empty markdown                                             |
| content.example         | string or null    | Non-null in all three modes; markdown with code or plain prose |
| metadata.topic          | string            | Mirrors input `topic`                                          |
| metadata.tokens_used    | integer           | >= 0; actual LLM consumption for this request                  |
| metadata.model          | string            | Non-empty model identifier                                     |

---

## Mode-specific diagram rules

| output_mode  | diagram field                                                             |
|--------------|---------------------------------------------------------------------------|
| beginner     | Always non-null; `graph TD` or `sequenceDiagram`; required by contract    |
| intermediate | Non-null only for structurally complex topics; null is valid               |
| advanced     | Non-null only when visualization communicates more than prose; null is valid |

---

## Token ceiling contract

| output_mode  | max tokens |
|--------------|------------|
| beginner     | 512        |
| intermediate | 1024       |
| advanced     | 2048       |

`metadata.tokens_used` MUST NOT exceed the ceiling for the given mode.

---

## Error handling contract

- Input validation failures (empty topic, invalid output_mode): return `status: "error"` immediately, no LLM call made.
- LLM call failure or timeout: return `status: "error"` with `metadata.tokens_used: 0`.
- JSON parse failure from LLM response: return `status: "error"`.
- Mermaid validation failure: set `content.diagram` to null and continue; does NOT trigger `status: "error"` unless the diagram was required (beginner mode). In beginner mode, a failed diagram triggers a retry or fallback to a simple valid diagram.
- The Teaching Agent MUST NOT raise unhandled exceptions to the caller. All failure paths return schema-valid JSON.

---

## Caller assumptions

- The Planner Agent always provides `request_id`, `session_ctx`, `topic`, `output_mode`, and `context` in the `TeachingRequestEvent`; the Teaching Agent never falls back to defaults for missing fields.
- `request_id` is assigned by the Planner before publishing; it is opaque to the Teaching Agent and passed through unchanged.
- `session_ctx` is assembled by the Planner from session state; the Teaching Agent never reads or validates its contents — it is passed through unchanged.
- The `context` field is assembled by the Planner Agent from Memory Agent output; the Teaching Agent treats it as opaque text.
- The Planner Agent validates `output_mode` before publishing; the Teaching Agent re-validates and returns `status: "error"` (and still publishes a `TeachingCompletionEvent`) if the value is invalid.
- The `"teaching"` and `"teaching-complete"` topics exist before the worker starts — they are bootstrapped by the backend service at startup. `"teaching"` is registered under `PlannerTopics.TEACHING` in `project/topics.py`; `"teaching-complete"` is registered under `TeachingTopics.TEACHING_COMPLETE`.
