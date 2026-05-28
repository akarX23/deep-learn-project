# Contract: Teaching Agent — Planner Interface

## Purpose
Defines the request and response contract between the Planner Agent and the Teaching Agent.
All fields are validated by Pydantic v2 models in `project/schemas.py`.

---

## Request Schema: TeachingAgentInput

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

- The Planner Agent always provides all three fields; the Teaching Agent never falls back to defaults for missing input fields.
- The `context` field is assembled by the Planner Agent from Memory Agent output; the Teaching Agent treats it as opaque text.
- The Planner Agent validates `output_mode` before forwarding; the Teaching Agent re-validates and returns `status: "error"` if the value is invalid.
