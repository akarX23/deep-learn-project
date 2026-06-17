# Contract: Planner Agent Interface

## Purpose

Defines the request and response contract between the application layer (or orchestrator)
and the Planner Agent. The Planner is the single entry point for all user queries in the
AI Tutor multi-agent system.

---

## Request Schema: PlannerInput

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_query": "Explain gradient descent from the uploaded chapter",
  "session_context": null,
  "available_files": [
    "rag_agent/tests/inputs/sample.pdf"
  ],
  "schema_version": "1.0"
}
```

### Field Constraints

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `request_id` | string (UUID) | ✅ | — | Must be a valid UUID v4 string |
| `user_query` | string | ✅ | — | Non-empty after whitespace strip; max 2000 chars |
| `session_context` | string \| null | ❌ | null | Prior turn context as a plain string |
| `available_files` | list[string] \| null | ❌ | null | PDF paths; hint for RAG payload construction |
| `schema_version` | string | ✅ | "1.0" | Must be non-empty |

---

## Response Schema: PlannerOutput

### Successful Routing (status: routed)

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_query": "Explain gradient descent from the uploaded chapter",
  "schema_version": "1.0",
  "routing_decision": {
    "target_agent": "RAG_AGENT",
    "confidence_score": 0.91,
    "reasoning": "Query requests content from an uploaded document, best handled by retrieval.",
    "constructed_payload": {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_prompt": "Explain gradient descent from the uploaded chapter",
      "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
      "include_tables": true,
      "include_images": true,
      "relevance_threshold": 0.6,
      "schema_version": "1.0"
    },
    "candidate_agents": [
      {"agent_type": "RAG_AGENT", "confidence_score": 0.91, "reasoning": "..."},
      {"agent_type": "TEACHING_AGENT", "confidence_score": 0.31, "reasoning": "..."},
      {"agent_type": "QUIZ_EVAL_AGENT", "confidence_score": 0.08, "reasoning": "..."}
    ],
    "query_was_rewritten": false,
    "hyde_applied": false
  },
  "status": "routed",
  "errors": []
}
```

### Ambiguous Intent (status: ambiguous)

```json
{
  "request_id": "...",
  "user_query": "help",
  "schema_version": "1.0",
  "routing_decision": {
    "target_agent": "UNKNOWN",
    "confidence_score": 0.42,
    "reasoning": "No agent exceeded confidence threshold 0.6 after query rewriting.",
    "constructed_payload": null,
    "candidate_agents": [
      {"agent_type": "TEACHING_AGENT", "confidence_score": 0.42, "reasoning": "..."},
      {"agent_type": "RAG_AGENT", "confidence_score": 0.38, "reasoning": "..."},
      {"agent_type": "QUIZ_EVAL_AGENT", "confidence_score": 0.20, "reasoning": "..."}
    ],
    "query_was_rewritten": true,
    "hyde_applied": false
  },
  "status": "ambiguous",
  "errors": ["No agent confidence exceeded threshold 0.6 after 3 attempts."]
}
```

### Failed (status: failed)

```json
{
  "request_id": "...",
  "user_query": "...",
  "schema_version": "1.0",
  "routing_decision": {
    "target_agent": "UNKNOWN",
    "confidence_score": 0.0,
    "reasoning": "Request blocked by guardrail.",
    "constructed_payload": null,
    "candidate_agents": [],
    "query_was_rewritten": false,
    "hyde_applied": false
  },
  "status": "failed",
  "errors": ["Guardrail BLOCKED: query is out of educational scope."]
}
```

---

## Status Semantics

| Status | Meaning | `constructed_payload` | `errors` |
|--------|---------|----------------------|---------|
| `routed` | A target agent was identified with confidence ≥ threshold and payload built | Present (typed agent input dict) | May be empty |
| `ambiguous` | No agent exceeded confidence threshold after retries | null | Non-empty |
| `failed` | Blocked by guardrail, invalid input, or unrecoverable internal error | null | Non-empty |

---

## Constructed Payload Contracts by Agent Type

The `constructed_payload` field contains a typed dict matching the target agent's input contract:

| `target_agent` | Payload schema | Defined in |
|----------------|---------------|-----------|
| `RAG_AGENT` | `RAGAgentInput` | `project/schemas.py` |
| `TEACHING_AGENT` | `TeachingAgentInput` *(stub in v1)* | `project/schemas.py` |
| `QUIZ_EVAL_AGENT` | `QuizAgentInput` *(stub in v1)* | `project/schemas.py` |

Callers must use `routing_decision.target_agent` to determine which schema to deserialize
`constructed_payload` into before invoking the downstream agent.

---

## HyDE Augmentation Note

When `routing_decision.hyde_applied` is `true`, the `user_prompt` field inside `constructed_payload`
(for RAG_AGENT) will be augmented with a hypothetical relevant passage:

```
User query: {original_or_rewritten_query}

Hypothetical relevant content:
{hyde_generated_passage}
```

This augmented prompt provides the RAG Agent's relevance scorer with richer semantic signal
for short or vague queries. The original `user_query` at the top-level output is always the
**unmodified** original query from PlannerInput.

---

## Error Handling Contract

- Non-fatal issues (e.g., guardrail WARN, retry attempt notifications) are accumulated in `errors` and
  do not prevent a `routed` status.
- Fatal errors (guardrail BLOCKED, input validation failure, unrecoverable exception) set `status` to
  `failed` and populate `errors` with a descriptive message.
- The Planner never raises unhandled exceptions to callers — all error paths produce a valid
  `PlannerOutput`.

---

## Determinism and Ordering

- LangGraph node execution order is deterministic and graph-defined; it is **not** LLM-driven.
- Conditional edges are evaluated on `PlannerState` fields (complexity, confidence, attempt_count).
- LLM calls within nodes are non-deterministic by nature, but their **outputs** are validated and
  constrained by structured prompts requiring JSON responses.
- `request_id`, `user_query`, and `schema_version` are always mirrored verbatim from input.
