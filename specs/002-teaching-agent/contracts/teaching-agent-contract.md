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
  "sid": "abc123xyz",
  "user_prompt": "Binary Search Tree",
  "user_level": "intermediate",
  "rag_compiled": "User previously studied arrays and linked lists in this session."
}
```

### Field constraints

| Field | Type | Required | Constraints |
|---|---|---|---|
| request_id | string | Yes | Non-empty; unique per request; assigned by Planner |
| sid | string | Yes | Non-empty; Socket.IO session ID for frontend WebSocket routing |
| user_prompt | string | Yes | Non-empty; the question or topic to explain |
| user_level | string | Yes | One of: `"beginner"`, `"intermediate"`, `"advanced"` |
| rag_compiled | string | No | RAG output to use as context; defaults to `""` |

---

## Kafka Outbound: TeachingCompletionEvent

Published by the Teaching Agent to topic `"teaching-complete"` after every request.

### Success variant

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "sid": "abc123xyz",
  "user_level": "intermediate",
  "content": "**Explanation**\nA Binary Search Tree (BST) is a node-based data structure...\n\n**Diagram**\ngraph TD\n  A[Root: 8] --> B[Left: 3]\n  A --> C[Right: 10]\n\n**Notes**\n- BST property: left < node < right\n\n**Example**\n```python\nclass Node:\n    def __init__(self, val):\n        self.val = val\n```"
}
```

### Error variant

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "sid": "abc123xyz",
  "user_level": "beginner",
  "content": ""
}
```

### TeachingCompletionEvent field constraints

| Field | Type | Constraints |
|---|---|---|
| request_id | string | Verbatim from `TeachingRequestEvent`; never modified |
| sid | string | Verbatim from `TeachingRequestEvent`; used for WebSocket routing |
| user_level | string | Verbatim from `TeachingRequestEvent`; non-empty |
| content | string | Complete raw markdown string (all four sections); empty string `""` on error. Phase 4 change: previously carried JSON-serialized `TeachingContent`. |

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
| beginner     | 4096 (default; configurable via `TEACHING_BEGINNER_MAX_TOKENS`) |
| intermediate | 4096 (default; configurable via `TEACHING_INTERMEDIATE_MAX_TOKENS`) |
| advanced     | 4096 (default; configurable via `TEACHING_ADVANCED_MAX_TOKENS`) |

`metadata.tokens_used` MUST NOT exceed the ceiling for the given mode.

---

## Error handling contract

- Input validation failures (empty topic, invalid output_mode): return `status: "error"` immediately, no LLM call made.
- LLM call failure or timeout: return `status: "error"` with `metadata.tokens_used: 0`.
- JSON parse failure from LLM response: return `status: "error"`.
- Mermaid validation failure: set `content.diagram` to null and continue; does NOT trigger `status: "error"` unless the diagram was required (beginner mode). In beginner mode, a failed diagram triggers a retry or fallback to a simple valid diagram.
- The Teaching Agent MUST NOT raise unhandled exceptions to the caller. All failure paths return schema-valid JSON.

---

---

## Streaming Contract (Phase 4)

The Teaching Agent publishes real-time token events to the `"stream-tokens"` Kafka topic
using `StreamTokensEventBody`. These events are consumed by the backend service and forwarded
to the frontend via Socket.IO. Streaming events are published **before** `TeachingCompletionEvent`.

### Token event (explanation, notes, example — one per LLM chunk)

```json
{
  "from_service": "teaching-agent",
  "sid": "abc123xyz",
  "data": { "field": "explanation", "token": "A Binary Search Tree is" }
}
```

### Diagram event (one complete event per request, when diagram is non-null)

```json
{
  "from_service": "teaching-agent",
  "sid": "abc123xyz",
  "data": { "field": "diagram", "token": "graph TD\n  A[Root: 8] --> B[Left: 3]\n  A --> C[Right: 10]" }
}
```

### Stream-complete sentinel (always last, including on error)

```json
{
  "from_service": "teaching-agent",
  "sid": "abc123xyz",
  "data": { "done": true, "tokens_used": 847 }
}
```

### Streaming field constraints

| Event type | `data` keys | Notes |
|---|---|---|
| Token event | `field`, `token` | `field` is one of: `explanation`, `diagram`, `notes`, `example` |
| Diagram event | `field`, `token` | `field` is always `"diagram"`; `token` is the complete Mermaid string |
| Stream-complete | `done`, `tokens_used` | `done` is always `true`; `tokens_used` is the final LLM completion token count |

### Ordering guarantee

For every `TeachingRequestEvent`, the event order on `"stream-tokens"` is:
1. Zero or more token events with `field: "explanation"`
2. Zero or one event with `field: "diagram"` (absent if diagram is null)
3. Zero or more token events with `field: "notes"`
4. Zero or more token events with `field: "example"`
5. Exactly one stream-complete sentinel

The `TeachingCompletionEvent` on `"teaching-complete"` is published after the sentinel.

---

## Caller assumptions

- The Planner Agent always provides `request_id`, `sid`, `user_prompt`, `user_level`, and `rag_compiled` in the `TeachingRequestEvent`; the Teaching Agent never falls back to defaults for missing fields.
- `request_id` is assigned by the Planner before publishing; it is opaque to the Teaching Agent and passed through unchanged.
- `sid` is the Socket.IO session ID assigned by the backend when the user's browser connects. The Teaching Agent never reads or validates its contents — it is passed through unchanged to `TeachingCompletionEvent` so the backend can route the result to the correct WebSocket session.
- The `rag_compiled` field is assembled by the Planner Agent from RAG Agent output; the Teaching Agent treats it as opaque text passed as `context` to the core pipeline.
- The Planner Agent validates `output_mode` before publishing; the Teaching Agent re-validates and returns `status: "error"` (and still publishes a `TeachingCompletionEvent`) if the value is invalid.
- The `"teaching"` and `"teaching-complete"` topics exist before the worker starts — they are bootstrapped by the backend service at startup. `"teaching"` is registered under `PlannerTopics.TEACHING` in `project/topics.py`; `"teaching-complete"` is registered under `TeachingTopics.TEACHING_COMPLETE`.
