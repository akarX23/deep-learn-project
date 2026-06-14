# Data Model: Teaching Agent

## Entities

### OutputMode (Enum)
- Description: The target learner level. Determines explanation structure, vocabulary register, diagram rules, and token ceiling.
- Allowed values:
  - `beginner` — no prior knowledge assumed; analogies, required diagram, 512-token ceiling
  - `intermediate` — basics known; technical terminology, optional diagram, 1024-token ceiling
  - `advanced` — practitioner level; formal definitions, internals, optional diagram, 2048-token ceiling

### TeachingAgentInput
- Description: Input payload received from the Planner Agent.
- Fields:
  - `topic`: str — the subject to be explained (e.g., "Binary Trees", "Recursion")
  - `output_mode`: OutputMode — determines explanation register and structure
  - `context`: str — optional prior session summary from Memory Agent; may be empty string
- Validation rules:
  - `topic` must be a non-empty string after stripping whitespace.
  - `output_mode` must be one of the three defined enum values.
  - `context` is always accepted; empty string is valid.

### TeachingContent
- Description: The structured explanation payload returned in the response.
- Fields:
  - `explanation`: str — the full explanation in markdown, following mode-specific structure
  - `diagram`: str | None — valid Mermaid diagram syntax, or null if not applicable or validation failed
  - `notes`: str — summary notes in markdown format
  - `example`: str | None — worked example or code snippet in markdown, or null if not applicable
- Validation rules:
  - `explanation` must be non-empty.
  - `notes` must be non-empty.
  - `diagram` must be null or contain syntactically valid Mermaid syntax (validated before assignment).
  - In beginner mode: `diagram` must not be null; `example` must not be null.
  - In intermediate/advanced mode: `diagram` may be null; `example` must not be null.

### TeachingMetadata
- Description: Audit record for the Teaching Agent response.
- Fields:
  - `topic`: str — mirrored from input
  - `tokens_used`: int — actual token consumption reported by the LLM response
  - `model`: str — model identifier used for the generation (e.g., `claude-sonnet-4-6`)
- Validation rules:
  - `tokens_used` must be >= 0.
  - `model` must be non-empty.

### TeachingAgentOutput
- Description: Output payload returned by the Teaching Agent to the Planner Agent.
- Fields:
  - `status`: str — `"ok"` on success, `"error"` on any failure
  - `output_mode`: OutputMode — mirrored from input
  - `content`: TeachingContent | None — null when `status` is `"error"`
  - `metadata`: TeachingMetadata — always populated, including on error
- Validation rules:
  - `status` must be exactly `"ok"` or `"error"`.
  - `content` must be non-null when `status` is `"ok"`.
  - `content` must be null when `status` is `"error"`.
  - `metadata.topic` mirrors `TeachingAgentInput.topic` in all cases.

### TeachingRequestEvent (Phase 2 — Kafka inbound)

- Description: Inbound Kafka payload published by the Planner Agent to the `"teaching"` topic. Triggers the Teaching Agent worker.
- Fields:
  - `request_id`: str — unique per request, assigned by Planner; non-empty
  - `session_ctx`: dict — user/session tracking metadata (e.g. `session_id`, `user_id`, `trace_id`); may be empty `{}`
  - `topic`: str — maps to `TeachingAgentInput.topic`
  - `output_mode`: str — maps to `TeachingAgentInput.output_mode`
  - `context`: str — maps to `TeachingAgentInput.context`; defaults to `""`
  - `created_at`: str | None — optional ISO 8601 UTC timestamp of when Planner created the event
  - `source`: str | None — optional source identifier (e.g. `"planner-agent"`)
- Validation rules:
  - `request_id` must be non-empty.
  - `session_ctx` must not be null (empty dict is valid).
  - `topic`, `output_mode`, and `context` follow the same rules as `TeachingAgentInput`.

### TeachingCompletionEvent (Phase 2 — Kafka outbound)

- Description: Outbound Kafka payload published by the Teaching Agent to `"teaching-complete"` after every request, including failures.
- Fields:
  - `request_id`: str — passed through verbatim from `TeachingRequestEvent`
  - `session_ctx`: dict — passed through verbatim from `TeachingRequestEvent`
  - `topic`: str — from the request
  - `output_mode`: str — from the request
  - `status`: str — `"ok"` or `"error"`
  - `content`: TeachingContent | None — null when `status: "error"`
  - `tokens_used`: int — from `TeachingMetadata.tokens_used`; `0` on error
  - `model`: str — from `TeachingMetadata.model`
  - `started_at`: str — ISO 8601 UTC; when `TeachingAgent.run()` was invoked
  - `completed_at`: str — ISO 8601 UTC; when the result was ready
  - `duration_ms`: int — `max(0, completed_at - started_at)` in milliseconds
  - `errors`: list[str] — error messages; empty list on success
  - `source`: str — always `"teaching-agent"`
- Validation rules:
  - `request_id` and `session_ctx` must match the originating `TeachingRequestEvent` exactly.
  - `status` must be exactly `"ok"` or `"error"`.
  - `duration_ms` must be >= 0.
  - `tokens_used` must be >= 0.

### TeachingTopics (Phase 2 — Kafka topic registry)

- Description: Enum in `project/topics.py` registering the outbound topic owned by the Teaching Agent.
- Values:
  - `TEACHING_COMPLETE = "teaching-complete"` — outbound; Teaching Agent publishes here
- Note: The inbound topic `"teaching"` is registered under `PlannerTopics.TEACHING`, consistent
  with the pattern used by `PlannerTopics.RAG` for the RAG Agent.
- `TeachingTopics.TEACHING_COMPLETE` and `PlannerTopics.TEACHING` are both included in
  `get_all_topic_names()` so the backend service bootstraps them at startup.

## Relationships

- One `TeachingAgentInput` maps to one `TeachingAgentOutput`.
- One `TeachingAgentOutput` contains exactly one `TeachingContent` (when `status: "ok"`) and exactly one `TeachingMetadata`.
- `OutputMode` determines per-mode content rules applied to `TeachingContent`.
- One `TeachingRequestEvent` produces exactly one `TeachingCompletionEvent`. `request_id` and `session_ctx` are invariant across both — the Teaching Agent never modifies them.
- `TeachingRequestEvent` wraps the same fields as `TeachingAgentInput` (`topic`, `output_mode`, `context`) plus Kafka-level tracking fields (`request_id`, `session_ctx`).
- `TeachingCompletionEvent` flattens `TeachingAgentOutput` (status, content) and `TeachingMetadata` (tokens_used, model) into a single event alongside timing and correlation fields.

## State Transitions

### Kafka worker message lifecycle (Phase 2)
1. `consumed` → `parsing` — raw Kafka payload received from `"teaching"` topic
2. `parsing` → `dispatching` — `TeachingRequestEvent` validated successfully; `TeachingAgent.run()` invoked
3. `parsing` → `skipped` — payload malformed or schema-invalid; error logged; poll loop continues
4. `dispatching` → `publishing` — `TeachingAgent.run()` returns (any status); `TeachingCompletionEvent` built
5. `publishing` → `complete` — `TeachingCompletionEvent` published to `"teaching-complete"` and flushed
6. `publishing` → `publish_failed` — Kafka publish error logged; message acknowledged; poll loop continues

### Core pipeline request-level state
1. `received` → `generating` — input is validated and prompt is dispatched to LLM
2. `generating` → `validating_diagram` — LLM response received and JSON parsed
3. `validating_diagram` → `ok` — Mermaid diagram is valid (or null/not required)
4. `validating_diagram` → `ok` — Mermaid diagram failed validation; `diagram` set to null, processing continues
5. `received` → `error` — input validation fails (e.g., empty topic, invalid output_mode)
6. `generating` → `error` — LLM call fails or JSON parse fails

### Diagram field state (TeachingContent)
1. `llm_output_present` → `valid` — structural Mermaid check passes; assigned to `diagram`
2. `llm_output_present` → `null` — structural Mermaid check fails; `diagram` set to null
3. `llm_output_absent` → `null` — LLM returned null or empty for diagram; `diagram` set to null

## Per-Mode Content Rules (summary)

| Field       | Beginner                          | Intermediate                          | Advanced                                   |
|-------------|-----------------------------------|---------------------------------------|--------------------------------------------|
| explanation | 5-part structure with analogy     | 4-part with terminology and trade-offs | 5-part with formal def and edge cases     |
| diagram     | Required; `graph TD` or `sequenceDiagram` | Optional; more detailed than beginner | Optional; only if prose insufficient     |
| notes       | Jargon-free bullet list            | Structured markdown with subheadings   | Dense technical reference / cheat sheet   |
| example     | Concrete worked example (plain English commentary) | Python snippet with inline comments | Non-trivial usage (optimization/arch pattern) |
| max_tokens  | 512                               | 1024                                  | 2048                                       |
