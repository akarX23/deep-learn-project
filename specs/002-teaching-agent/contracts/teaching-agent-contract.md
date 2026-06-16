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
  "sid": "sess-abc-123",
  "user_prompt": "Binary Search Tree",
  "user_level": "intermediate",
  "rag_compiled": "User previously studied arrays and linked lists in this session."
}
```

### Field constraints

| Field | Type | Required | Constraints |
|---|---|---|---|
| request_id | string | Yes | Non-empty; unique per request; assigned by Planner |
| sid | string | Yes | Session identifier for correlation |
| user_prompt | string | Yes | The topic; maps to `TeachingAgentInput.topic` |
| user_level | string | Yes | One of `"beginner"`/`"intermediate"`/`"advanced"`; maps to `output_mode` |
| rag_compiled | string | Yes | RAG context; maps to `context`; may be empty; default `""` |

---

## Kafka Outbound: TeachingCompletionEvent

Published by the Teaching Agent to topic `"teaching-complete"` after every request.

### Success variant

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "sid": "sess-abc-123",
  "user_level": "intermediate",
  "content": "{\"explanation\": \"## Binary Search Tree...\", \"diagram\": \"graph TD\\n  A[Root: 8] --> B[Left: 3]\", \"notes\": \"## Key Properties...\", \"example\": \"```python\\nclass Node: ...\\n```\"}"
}
```

### Error variant

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "sid": "sess-abc-123",
  "user_level": "beginner",
  "content": ""
}
```

### TeachingCompletionEvent field constraints

| Field | Type | Constraints |
|---|---|---|
| request_id | string | Verbatim from `TeachingRequestEvent`; non-empty |
| sid | string | Verbatim from `TeachingRequestEvent` |
| user_level | string | From request; non-empty |
| content | string | Serialized `TeachingContent` JSON on success; empty string on error |

No `status` / timing / `tokens_used` / `model` / `errors` fields — an error outcome is
conveyed as empty `content`. Reflection is internal and does not change this contract.

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
    "model": "claude-sonnet-4-6",
    "reflection_iterations": 1
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
    "model": "claude-sonnet-4-6",
    "reflection_iterations": 0
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
| metadata.tokens_used    | integer           | >= 0; total LLM consumption (generation + critiques + revisions) |
| metadata.model          | string            | Non-empty model identifier                                     |
| metadata.reflection_iterations | integer    | >= 0; completed reflection cycles (Phase 3)                    |

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
| beginner     | 4096 (default) |
| intermediate | 4096 (default) |
| advanced     | 4096 (default) |

Each LLM call's completion is capped at the per-mode ceiling (`max_tokens` at the call
boundary). With reflection enabled, `metadata.tokens_used` aggregates across all calls
(generation + critiques + revisions) and may exceed a single-call ceiling.

---

## Error handling contract

- Input validation failures (empty topic, invalid output_mode): return `status: "error"` immediately, no LLM call made.
- LLM call failure or timeout: return `status: "error"` with `metadata.tokens_used: 0`.
- JSON parse failure from LLM response: return `status: "error"`.
- Mermaid validation failure: set `content.diagram` to null and continue; does NOT trigger `status: "error"` unless the diagram was required (beginner mode). In beginner mode, a failed diagram triggers a retry or fallback to a simple valid diagram.
- The Teaching Agent MUST NOT raise unhandled exceptions to the caller. All failure paths return schema-valid JSON.

---

## Caller assumptions

- The Planner Agent always provides `request_id`, `sid`, `user_prompt`, `user_level`, and `rag_compiled` in the `TeachingRequestEvent`; the worker maps the latter three onto the core pipeline (`topic`/`output_mode`/`context`).
- `request_id` is assigned by the Planner before publishing; it is opaque to the Teaching Agent and passed through unchanged.
- `sid` is the Planner's session identifier; the Teaching Agent never interprets it — it is passed through unchanged.
- `rag_compiled` is assembled by the Planner Agent (from RAG / Memory output) and maps to the pipeline's `context`; the Teaching Agent treats it as opaque text.
- The Planner Agent validates `user_level` before publishing; the Teaching Agent re-validates the mapped `output_mode` and, on an invalid value, still publishes a `TeachingCompletionEvent` (with empty `content`).
- Reflection (Phase 3) is internal to `TeachingAgent.run()` and invisible to the Planner: the external event contract is unchanged and exactly one completion event is published per request.
- The `"teaching"` and `"teaching-complete"` topics exist before the worker starts — they are bootstrapped by the backend service at startup. `"teaching"` is registered under `PlannerTopics.TEACHING` in `project/topics.py`; `"teaching-complete"` is registered under `TeachingTopics.TEACHING_COMPLETE`.
