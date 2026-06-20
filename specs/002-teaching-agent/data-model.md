# Data Model: Teaching Agent

## Entities

### OutputMode (Enum)
- Description: The target learner level. Determines explanation structure, vocabulary register, diagram rules, and token ceiling.
- Allowed values:
  - `beginner` — no prior knowledge assumed; analogies, required diagram, 4096-token ceiling (default; configurable via `TEACHING_BEGINNER_MAX_TOKENS`)
  - `intermediate` — basics known; technical terminology, optional diagram, 4096-token ceiling (default; configurable via `TEACHING_INTERMEDIATE_MAX_TOKENS`)
  - `advanced` — practitioner level; formal definitions, internals, optional diagram, 4096-token ceiling (default; configurable via `TEACHING_ADVANCED_MAX_TOKENS`)

### TeachingAgentInput
- Description: Input payload received from the Planner Agent.
- Fields:
  - `topic`: str — the subject to be explained (e.g., "Binary Trees", "Recursion")
  - `output_mode`: OutputMode — determines explanation register and structure
  - `context`: str — optional prior session summary from Memory Agent; may be empty string
  - `chat_history`: list[dict] — (Phase 5) prior conversation turns, oldest→newest,
    EXCLUDING the current query (which is `topic`). Each entry
    `{"role": "user"|"assistant", "content": str}`. Defaults to `[]`; prepended to the
    LLM message list so the current structured prompt stays the final user message.
- Validation rules:
  - `topic` must be a non-empty string after stripping whitespace.
  - `output_mode` must be one of the three defined enum values.
  - `context` is always accepted; empty string is valid.
  - `chat_history` defaults to `[]`; each entry must have `role` ∈ {`user`, `assistant`}
    and a non-empty string `content` (light validator). Empty `chat_history` reproduces
    single-turn behavior exactly.

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
  - `tokens_used`: int — total completion tokens across every LLM call in the request
    lifecycle (generation + each critique + each revision), per SC-013
  - `model`: str — model identifier used for the generation (e.g., `claude-sonnet-4-6`)
  - `reflection_iterations`: int — completed reflection cycles; 0 when disabled or none
    completed; default 0 (Phase 3)
- Validation rules:
  - `tokens_used` must be >= 0.
  - `model` must be non-empty.
  - `reflection_iterations` must be >= 0.

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
  - `sid`: str — Socket.IO session ID for frontend WebSocket routing; passed through unchanged
  - `user_prompt`: str — the question or topic to explain; maps to `TeachingAgentInput.topic`
  - `user_level`: str — learner level; maps to `TeachingAgentInput.output_mode`
  - `rag_compiled`: str — RAG output to use as context; maps to `TeachingAgentInput.context`; defaults to `""`
  - `chat_history`: list[dict] — (Phase 5) prior conversation turns, oldest→newest,
    EXCLUDING the current query (`user_prompt`); maps to `TeachingAgentInput.chat_history`;
    defaults to `[]`. The Planner owns truncation/summarization to fit the model window.
- Validation rules:
  - `request_id` must be non-empty.
  - `user_level` must be non-empty and one of `"beginner"`, `"intermediate"`, `"advanced"`.
  - `chat_history` defaults to `[]`; each entry must have `role` ∈ {`user`, `assistant`}
    and a non-empty string `content`.

### TeachingCompletionEvent (Phase 2 — Kafka outbound; updated Phase 4)

- Description: Outbound Kafka payload published by the Teaching Agent to `"teaching-complete"` after every request, including failures.
- Fields:
  - `request_id`: str — passed through verbatim from `TeachingRequestEvent`
  - `sid`: str — passed through verbatim from `TeachingRequestEvent`; used by backend for WebSocket routing
  - `user_level`: str — passed through verbatim from `TeachingRequestEvent`
  - `content`: str — (Phase 4) complete raw markdown string produced by the LLM (all four sections: `**Explanation**`, `**Diagram**`, `**Notes**`, `**Example**`); empty string `""` on error. Prior to Phase 4, this was a JSON-serialized `TeachingContent` string.
- Validation rules:
  - `request_id` and `user_level` must be non-empty.
  - `content` must not be null (empty string is valid on error).

### StreamTokensEventBody (Phase 4 — Kafka streaming outbound)

- Description: Outbound Kafka payload published by the Teaching Agent to `"stream-tokens"` for every token chunk during LLM generation. Consumed by the backend service and forwarded to the frontend via Socket.IO.
- Fields:
  - `from_service`: str — always `"teaching-agent"`
  - `sid`: str — passed through from `TeachingRequestEvent`; used by backend to route to the correct WebSocket session
  - `data`: dict — payload varies by event type:
    - Token event: `{"field": "<section>", "token": "<chunk>"}` where `field` is one of `explanation`, `diagram`, `notes`, `example`
    - Stream-complete sentinel: `{"done": true, "tokens_used": N}`
- Streaming rules:
  - `explanation`, `notes`, `example`: emitted chunk by chunk as tokens arrive from the LLM stream
  - `diagram`: buffered until the section is complete; emitted as a single event with the complete Mermaid string
  - Stream-complete sentinel: always the last event published per request, including on error paths

### TeachingTopics (Phase 2 — Kafka topic registry)

- Description: Enum in `project/topics.py` registering the outbound topic owned by the Teaching Agent.
- Values:
  - `TEACHING_COMPLETE = "teaching-complete"` — outbound; Teaching Agent publishes here
- Note: The inbound topic `"teaching"` is registered under `PlannerTopics.TEACHING`, consistent
  with the pattern used by `PlannerTopics.RAG` for the RAG Agent.
- `TeachingTopics.TEACHING_COMPLETE` and `PlannerTopics.TEACHING` are both included in
  `get_all_topic_names()` so the backend service bootstraps them at startup.

### ReflectionIssue (Phase 3 — internal)

- Description: One weakness flagged by the critique step. Internal to the reflection
  loop; never serialized into `TeachingAgentOutput` or `TeachingCompletionEvent`.
- Fields:
  - `field`: str — one of `explanation`, `diagram`, `notes`, `example`
  - `issue`: str — the specific weakness
  - `severity`: str — one of `low`, `medium`, `high`

### ReflectionCritique (Phase 3 — internal)

- Description: Structured self-critique produced between generation and revision.
  Internal only; defined in `project/schemas.py`.
- Fields:
  - `quality_score`: int — holistic score, 1–10
  - `issues`: list[ReflectionIssue] — may be empty
  - `revision_instructions`: str — instructions passed to the revision call
- Validation rules:
  - `quality_score` within [1, 10].
  - `revision_instructions` non-empty when `issues` is non-empty.

## Relationships

- One `TeachingAgentInput` maps to one `TeachingAgentOutput`.
- One `TeachingAgentOutput` contains exactly one `TeachingContent` (when `status: "ok"`) and exactly one `TeachingMetadata`.
- `OutputMode` determines per-mode content rules applied to `TeachingContent`.
- One `TeachingRequestEvent` produces exactly one `TeachingCompletionEvent`. `request_id`, `sid`, and `user_level` are invariant across both — the Teaching Agent never modifies them.
- `TeachingRequestEvent` carries `user_prompt` (→`topic`), `user_level` (→`output_mode`), `rag_compiled` (→`context`), `chat_history` (→`chat_history`, Phase 5) plus Kafka tracking fields `request_id` and `sid`. The handler maps these before calling `TeachingAgent.run()`.
- `TeachingCompletionEvent` carries `request_id`, `sid`, `user_level` (correlation/routing) and `content` (Phase 4: complete raw markdown string; empty string on error).
- One `TeachingRequestEvent` also produces N `StreamTokensEventBody` events (one per LLM token chunk) plus one stream-complete sentinel, all published to `"stream-tokens"` before the `TeachingCompletionEvent` is published. `TeachingContent` is assembled internally in `agent.py` for Mermaid validation only — it is not serialized to any Kafka event in Phase 4.

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
| max_tokens  | 4096 (`TEACHING_BEGINNER_MAX_TOKENS`) | 4096 (`TEACHING_INTERMEDIATE_MAX_TOKENS`) | 4096 (`TEACHING_ADVANCED_MAX_TOKENS`) |
