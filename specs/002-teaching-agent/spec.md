# Feature Specification: Teaching Agent

**Feature Branch**: `[002-build-teaching-agent]`
**Created**: 2026-05-28
**Status**: Complete — Core pipeline and Kafka integration implemented
**Input**: User description: "Build the Teaching Agent component of a multi-agent AI tutoring system."

## Implementation Phases

| Phase | Scope | Status |
|---|---|---|
| Phase 1 — Core pipeline | `TeachingAgent.run()`, schemas, prompts, validators, helpers, LLM client, config | **Complete** |
| Phase 2 — Kafka integration | `kafka.py`, `handlers.py`, `worker.py`, Kafka event schemas, topic registration | **Complete** |
| Phase 3 — Reflection pattern | Colleague-owned; not in scope for this feature branch | In progress (separate branch) |
| Phase 4 — Token streaming | Markdown LLM output, `StreamingFieldExtractor`, `stream-tokens` Kafka topic, real-time field-keyed token delivery to frontend | **Complete** |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Beginner-Mode Explanation (Priority: P1)

A learner with no prior knowledge asks about a topic. The Planner Agent sends a request
with `output_mode: "beginner"`. The Teaching Agent returns a jargon-free explanation
structured around a real-world analogy, a step-by-step walkthrough, a visual diagram,
and three memorable key takeaways.

**Why this priority**: The beginner audience is the widest and most likely to abandon a
tool that feels overwhelming. Getting this mode right is the baseline for the product to
be useful at all.

**Independent Test**: Send a valid request with `output_mode: "beginner"` for any topic
and verify that the returned content uses plain language, includes a required Mermaid
diagram, follows the five-part structure, and stays within the 4096-token ceiling.

**Acceptance Scenarios**:

1. **Given** a valid request with `output_mode: "beginner"` and a non-empty topic, **When** the agent processes it, **Then** the response contains a non-empty explanation that begins with a one-sentence plain-English summary and includes a real-world analogy.
2. **Given** a beginner request, **When** the response is produced, **Then** the `diagram` field is always non-null and contains valid Mermaid syntax.
3. **Given** a beginner request, **When** the response is produced, **Then** `notes` contains three bullet-point takeaways with no unexplained jargon, and `example` contains a concrete worked example with plain-English step commentary.
4. **Given** a beginner request, **When** output is generated, **Then** total tokens consumed do not exceed 4096.

---

### User Story 2 - Intermediate-Mode Explanation (Priority: P2)

A learner who knows the basics wants a mechanically accurate explanation with correct
terminology, a Python code example, and a trade-off analysis. The Teaching Agent returns
a structured explanation suitable for practical application.

**Why this priority**: Intermediate learners are the most likely to evaluate whether the
tool is reliable. A technically accurate, well-structured response at this level builds
trust with the broader audience.

**Independent Test**: Send a valid request with `output_mode: "intermediate"` for any
topic and verify that the explanation uses correct technical terms, includes a Python
code snippet, presents trade-offs, and stays within the 4096-token ceiling.

**Acceptance Scenarios**:

1. **Given** a valid request with `output_mode: "intermediate"`, **When** the agent processes it, **Then** the explanation starts with a precise definition and includes a section on mechanics and trade-offs.
2. **Given** an intermediate request for a structurally complex topic, **When** the response is produced, **Then** a Mermaid diagram is included and is more detailed than a beginner diagram would be for the same topic.
3. **Given** an intermediate request for a topic with no structural complexity, **When** the response is produced, **Then** the `diagram` field may be null.
4. **Given** an intermediate request, **When** output is generated, **Then** total tokens consumed do not exceed 4096.

---

### User Story 3 - Advanced-Mode Explanation (Priority: P3)

A practitioner wants depth, internals, complexity analysis, edge cases, and a pointer
to further exploration. The Teaching Agent returns a reference-quality explanation
appropriate for a senior engineer.

**Why this priority**: Advanced users have the highest expectations and will validate the
tool against their existing knowledge. Serving them well builds credibility.

**Independent Test**: Send a valid request with `output_mode: "advanced"` for any topic
and verify that the explanation includes a formal definition, internal mechanics,
complexity analysis, edge cases, and further-exploration pointers within 4096 tokens.

**Acceptance Scenarios**:

1. **Given** a valid request with `output_mode: "advanced"`, **When** the agent processes it, **Then** the explanation includes a formal or semi-formal definition, a deep-dive into internal mechanics with time/space complexity, and at least one documented edge case or failure mode.
2. **Given** an advanced request, **When** the response is produced, **Then** the `notes` field is a dense technical reference usable as a practitioner cheat sheet.
3. **Given** an advanced request, **When** the response is produced, **Then** the `example` demonstrates non-trivial usage (optimization, edge-case handling, or architectural pattern).
4. **Given** an advanced request, **When** output is generated, **Then** total tokens consumed do not exceed 4096.

---

### User Story 4 - Schema-Safe Output and Error Reporting (Priority: P4)

The Planner Agent and downstream agents (Quiz Agent, Evaluation Agent) consume the
Teaching Agent's output programmatically. Every response — including failures — must be
schema-valid JSON so downstream consumers never receive unexpected structure.

**Why this priority**: A single non-schema-compliant response can crash the downstream
pipeline. Schema safety is a hard contract requirement for the multi-agent system.

**Independent Test**: Send requests with missing fields, unsupported mode values, and
empty topics; verify that every response returns the defined JSON structure with
`status: "error"` and null content fields rather than an exception or plain-text error.

**Acceptance Scenarios**:

1. **Given** a request with an empty topic, **When** the agent processes it, **Then** the response returns `status: "error"` with a non-null, schema-valid JSON body.
2. **Given** a valid request, **When** the response is produced, **Then** `metadata.topic`, `metadata.tokens_used`, and `metadata.model` are all populated.
3. **Given** any request, **When** the response is produced, **Then** `output_mode` in the response mirrors `output_mode` from the input exactly.

---

### User Story 5 - Kafka-Based Invocation and Result Publishing (Priority: P1)

The Teaching Agent is never called directly. The Planner Agent publishes a `TeachingRequestEvent`
to the `"teaching"` Kafka topic. The Teaching Agent worker consumes it, runs the core pipeline,
and publishes a `TeachingCompletionEvent` to `"teaching-complete"`. The Planner correlates the
response back to the originating request via `request_id` and `sid`.

**Why this priority**: Kafka is the only inter-agent communication bus. Without this layer the
Teaching Agent cannot participate in the system regardless of how well the core pipeline works.

**Independent Test**: Publish a valid `TeachingRequestEvent` payload to the `"teaching"` topic
and verify that a `TeachingCompletionEvent` appears on `"teaching-complete"` with the same
`request_id`, `sid`, `user_level`, and a non-empty `content` string.

**Acceptance Scenarios**:

1. **Given** a valid `TeachingRequestEvent` on the `"teaching"` topic, **When** the worker consumes it, **Then** `TeachingAgent.run()` is invoked with `user_prompt` mapped to `topic`, `user_level` mapped to `output_mode`, and `rag_compiled` mapped to `context`.
2. **Given** the core pipeline returns `status: "ok"`, **When** the result is assembled, **Then** a `TeachingCompletionEvent` is published to `"teaching-complete"` with `content` as a JSON-serialized string of the agent output.
3. **Given** the core pipeline returns `status: "error"` (invalid input or LLM failure), **When** the result is assembled, **Then** a `TeachingCompletionEvent` with `content: ""` (empty string) is still published to `"teaching-complete"` — the Planner is always notified.
4. **Given** any `TeachingCompletionEvent`, **When** it is published, **Then** `request_id`, `sid`, and `user_level` are copied verbatim from the inbound `TeachingRequestEvent` for downstream correlation.
5. **Given** a malformed or schema-invalid Kafka payload, **When** the worker receives it, **Then** the error is logged and the worker continues processing subsequent messages without crashing.

---

### User Story 6 - Real-time Token Streaming (Priority: P2)

A learner submits a question and wants to see the explanation appear progressively —
word by word — rather than waiting for the full response. The Teaching Agent streams
LLM output tokens in real-time to the frontend via the `"stream-tokens"` Kafka topic
while simultaneously delivering the complete structured response via `"teaching-complete"`.

**Why this priority**: Streaming dramatically reduces perceived latency. Users can begin
reading the explanation seconds after submission rather than waiting for the full LLM
response. This is a key UX differentiator for a tutoring product.

**Independent Test**: Publish a valid `TeachingRequestEvent` to `"teaching"` and verify
that `StreamTokensEventBody` messages appear on `"stream-tokens"` before the
`TeachingCompletionEvent` appears on `"teaching-complete"`. Verify the `explanation` field
tokens arrive incrementally, the `diagram` field arrives as a single complete event, and a
`{"done": true}` sentinel arrives last.

**Acceptance Scenarios**:

1. **Given** a valid `TeachingRequestEvent`, **When** the worker processes it, **Then** `StreamTokensEventBody` messages are published to `"stream-tokens"` with `field: "explanation"` tokens before the `TeachingCompletionEvent` is published.
2. **Given** the LLM stream includes a diagram, **When** the `diagram` section is processed, **Then** the diagram is published as a single complete `StreamTokensEventBody` event with `field: "diagram"` — never as partial tokens.
3. **Given** the LLM stream completes, **When** all field tokens have been published, **Then** a sentinel event `{"done": true, "tokens_used": N}` is published to `"stream-tokens"` so the frontend knows the stream is finished.
4. **Given** the core pipeline returns `status: "error"`, **When** the error is handled, **Then** a stream-complete sentinel is still published to `"stream-tokens"` and `TeachingCompletionEvent` is still published to `"teaching-complete"` with `content: ""`.
5. **Given** any `TeachingCompletionEvent`, **When** it is published, **Then** `content` is the complete raw markdown string produced by the LLM (not JSON); empty string `""` on error.

---

### Edge Cases

- Topic is a single word vs. a multi-word phrase (e.g., "Trees" vs. "Balanced Binary Search Trees").
- `context` field is empty string — agent must handle gracefully and still produce a complete response.
- `context` field contains lengthy RAG-compiled study material — agent must use it as the primary source without exceeding the token ceiling for the mode.
- Two requests with the same topic but different `output_mode` values — responses must be qualitatively different, not just length-adjusted.
- Topic is ambiguous or out of scope of a standard CS curriculum — agent must still return a structured, best-effort response rather than failing.
- LLM call fails or returns an empty response — agent must return `status: "error"` with an appropriate message rather than propagating an exception.
- Generated Mermaid diagram is syntactically invalid — agent must not return the invalid diagram; it must either fix it or set `diagram` to null.
- Kafka payload is missing required fields or has wrong types — worker must log and skip, never crash.
- Same `request_id` arrives twice (retry) — worker processes it again; idempotency is the Planner's responsibility.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a structured input payload containing `topic` (non-empty string), `output_mode` (one of: `beginner`, `intermediate`, `advanced`), and `context` (string, may be empty — carries RAG-compiled study material from the user's course documents when provided).
- **FR-002**: The system MUST return a structured output payload containing `status`, `output_mode`, `content` (with `explanation`, `diagram`, `notes`, `example`), and `metadata` (with `topic`, `tokens_used`, `model`) in every response, including error cases.
- **FR-003**: The system MUST treat `output_mode` as authoritative from input and MUST NOT infer or modify it based on topic or context.
- **FR-004**: The system MUST produce qualitatively distinct explanations for each output mode — the same topic processed at different modes must yield structurally and substantively different responses.
- **FR-005**: In beginner mode, the `diagram` field MUST always be non-null and contain a valid Mermaid flowchart or sequence diagram representing the topic visually.
- **FR-006**: In intermediate and advanced modes, the `diagram` field MUST be included only when the topic has structural or sequential complexity that benefits from visualization; otherwise `diagram` MUST be null.
- **FR-007**: The system MUST validate Mermaid diagram syntax before including it in the response; invalid diagrams MUST NOT be returned.
- **FR-008**: The system MUST enforce per-mode token ceilings configurable exclusively via environment variables: `TEACHING_BEGINNER_MAX_TOKENS`, `TEACHING_INTERMEDIATE_MAX_TOKENS`, `TEACHING_ADVANCED_MAX_TOKENS`, each defaulting to 4096 when unset. No ceiling values may be hardcoded in agent Python files — all defaults must be resolvable from environment/configuration files alone.
- **FR-009**: The system MUST use a dedicated LLM client module scoped to the Teaching Agent. All model configuration MUST be supplied via environment variables and MUST NOT be hardcoded in agent Python files. Configuration MUST support both shared and per-mode overrides using the following env var pattern (where `{MODE}` is `BEGINNER`, `INTERMEDIATE`, or `ADVANCED`):
  - **Model**: `TEACHING_{MODE}_MODEL` — falls back to `TEACHING_MODEL` if unset; `TEACHING_MODEL` is required when no per-mode override is provided
  - **API key**: `TEACHING_{MODE}_API_KEY` — falls back to `TEACHING_API_KEY` if unset
  - **Max tokens**: `TEACHING_{MODE}_MAX_TOKENS` — defaults to 4096 if unset (see FR-008)
  - **Temperature**: `TEACHING_{MODE}_TEMPERATURE` — falls back to `TEACHING_TEMPERATURE` if unset; default 0.7
  - **Effort**: `TEACHING_{MODE}_EFFORT` — optional; values: `low | medium | high`; translates to `output_config={"effort": value}` for Claude 4.6 models (Sonnet 4.6, Opus 4.6) via LiteLLM; silently skipped for all other models (Haiku, Groq, etc.) that do not support `output_config`; does NOT enable extended thinking or reasoning tokens
  This allows different providers, models, API quotas, temperature, and output effort per learner level without modifying any agent Python file. `TEACHING_API_BASE` remains a single shared optional override for self-hosted or custom-proxy endpoints only.
- **FR-010**: The system MUST return `status: "error"` and a schema-valid JSON body whenever processing fails; it MUST NOT raise unhandled exceptions or return plain text.
- **FR-011**: The system MUST populate `metadata.tokens_used` with the actual token count consumed and `metadata.model` with the model identifier used for the response.
- **FR-012**: In beginner mode, the `explanation` MUST follow this structure: (1) one-sentence plain-English summary, (2) real-world analogy, (3) numbered step-by-step walkthrough, (4) reference to the accompanying diagram, (5) three bullet-point key takeaways. The `notes` MUST be a simplified jargon-free bullet summary. The `example` MUST be a concrete worked example with plain-English commentary on each step.
- **FR-013**: In intermediate mode, the `explanation` MUST include: (1) a precise one-paragraph definition, (2) a mechanical how-it-works explanation with correct terminology, (3) at least one Python code example with inline comments, (4) trade-off analysis (when to use vs. when not to). The `notes` MUST be a structured markdown summary with subheadings. The `example` MUST be a Python code snippet with comments.
- **FR-014**: In advanced mode, the `explanation` MUST include: (1) a formal or semi-formal definition, (2) a deep-dive into internal mechanics covering time/space complexity and implementation considerations, (3) documented edge cases and failure modes, (4) real-world usage with performance or architectural implications, (5) a pointer to further exploration. The `notes` MUST be a dense technical markdown reference. The `example` MUST demonstrate non-trivial usage.
- **FR-015**: The system MUST expose its functionality through a module structure consistent with the project's other agents, with clear separation between schema definitions, agent orchestration, prompt templates, and LLM configuration.
- **FR-016**: The system MUST include automated tests covering: schema validation for all three modes, qualitative difference verification across modes for the same topic, diagram presence/absence rules, Mermaid validity, error response structure, and token ceiling enforcement.
- **FR-017**: The system MUST define UX consistency requirements: explanation structure headings must be stable across requests for the same mode, `notes` and `example` fields must always use markdown formatting, and response shape must remain consistent for programmatic consumers.
- **FR-018**: The system MUST define measurable performance requirements: a single Teaching Agent request must complete synchronously within an acceptable wall-clock budget appropriate for a tutoring interaction, and the agent must handle the full token ceiling for advanced mode without timeout.

### Kafka Integration Requirements (Phase 2)

- **FR-019**: The Teaching Agent MUST consume requests from the Kafka topic `"teaching"`. This topic is published to by the Planner Agent and is the sole entry point into the Teaching Agent at runtime.
- **FR-020**: The Teaching Agent worker MUST extract `user_prompt` (passed as `topic`), `user_level` (passed as `output_mode`), and `rag_compiled` (passed as `context`) from the inbound `TeachingRequestEvent` and pass them to `TeachingAgent.run()`. The core pipeline logic MUST NOT be modified.
- **FR-021**: Upon receiving a result from `TeachingAgent.run()` — whether `status: "ok"` or `status: "error"` — the worker MUST publish a `TeachingCompletionEvent` to the Kafka topic `"teaching-complete"` with `content` set to the JSON-serialized agent output (empty string on failure). The Planner is always notified regardless of outcome.
- **FR-022**: `TeachingRequestEvent` MUST include `request_id` (non-empty string, unique per request, assigned by the Planner) and `sid` (non-empty string — the Socket.IO session ID) for request tracing and frontend WebSocket routing.
- **FR-023**: `TeachingCompletionEvent` MUST carry back the same `request_id`, `sid`, and `user_level` from the originating `TeachingRequestEvent` verbatim, so the Planner can correlate responses to requests and the backend can route the completion event to the correct WebSocket session.
- **FR-025**: Both `TeachingRequestEvent` and `TeachingCompletionEvent` schemas MUST be defined in `project/schemas.py` in the Teaching Agent section. No schema definitions belong inside `teaching_agent/`.
- **FR-026**: `"teaching"` MUST be added to the existing `PlannerTopics` enum in `project/topics.py` (consistent with `PlannerTopics.RAG`); `"teaching-complete"` MUST be registered as `TeachingTopics.TEACHING_COMPLETE` in a new `TeachingTopics` enum. Both values MUST be included in `get_all_topic_names()` so the backend service bootstraps them at startup.
- **FR-027**: The Kafka integration MUST follow the same three-file structure used by the RAG agent: `teaching_agent/kafka.py` (I/O primitives and Protocol types), `teaching_agent/handlers.py` (business logic, zero Kafka I/O), `teaching_agent/worker.py` (lifecycle, poll loop). All Kafka-facing dependencies MUST be injectable for testing — no real Kafka connection required in tests.
- **FR-028**: A malformed or schema-invalid inbound Kafka message MUST be logged with its `request_id` (or `"unknown"` if absent) and skipped; the worker poll loop MUST continue processing subsequent messages.

### Token Streaming Requirements (Phase 4)

- **FR-029**: The LLM MUST be prompted to return output in markdown format using bold section headers — `**Explanation**`, `**Diagram**`, `**Notes**`, `**Example**` — as unambiguous section delimiters. `response_format={"type": "json_object"}` MUST be removed from the LLM call.
- **FR-030**: The Teaching Agent MUST publish per-field streaming tokens to the `"stream-tokens"` Kafka topic using the existing `StreamTokensEventBody` schema (`from_service`, `sid`, `data`). The `data` dict MUST carry `{"field": "<section>", "token": "<content>"}` for token events and `{"done": true, "tokens_used": N}` for the stream-complete sentinel.
- **FR-031**: `explanation`, `notes`, and `example` sections MUST be published token by token as chunks arrive from the LLM stream. The `diagram` section MUST be buffered until the section is complete and published as a single event — partial Mermaid syntax MUST NOT be published.
- **FR-032**: A stream-complete sentinel event (`{"done": true, "tokens_used": N}`) MUST be published to `"stream-tokens"` after all field tokens are published, including on error paths. This is the frontend's signal that the stream for this `request_id` has ended.
- **FR-033**: The `StreamingFieldExtractor` component MUST detect section boundaries by watching for `**SectionName**` bold headers in the LLM delta stream. It MUST handle chunks that span a header boundary (i.e. a header may arrive split across two consecutive chunks).
- **FR-034**: `TeachingCompletionEvent.content` MUST carry the complete raw markdown string produced by the LLM when the pipeline succeeds; empty string `""` on failure. Downstream agents (Planner, Quiz Agent) receive markdown — no longer JSON-serialized `TeachingContent`.
- **FR-035**: The existing `parse_markdown_response()` parser (replacing `parse_llm_response()`) MUST be used internally in `agent.py` for Mermaid diagram validation and `TeachingAgentOutput` construction. It is not exposed to Kafka consumers.
- **FR-036**: When `context` is non-empty, the LLM prompt MUST explicitly instruct the model to treat it as the primary reference source and ground the explanation in the provided material. General knowledge MAY be used only to supplement where the material is silent or incomplete. The prompt label for `context` MUST NOT describe it as a "prior session" summary — it is course reference material compiled by the RAG Agent.

### Key Entities

- **TeachingAgentInput**: The input contract. Contains `topic` (the subject to be explained), `output_mode` (the target learner level), and `context` (RAG-compiled study material from the user's course documents; used as the primary LLM reference source when non-empty).
- **TeachingAgentOutput**: The output contract. Contains `status` (`ok` or `error`), `output_mode` (mirrored from input), `content` (the explanation payload), and `metadata` (audit information).
- **TeachingContent**: The structured explanation payload. Contains `explanation` (full markdown explanation), `diagram` (Mermaid syntax or null), `notes` (summary markdown), and `example` (worked example or code snippet, or null).
- **OutputMode**: Enum of `beginner`, `intermediate`, `advanced`. Determines explanation structure, diagram rules, token ceiling, and language register.
- **TeachingMetadata**: Audit record. Contains `topic` (mirrored from input), `tokens_used` (actual consumption), and `model` (model identifier).
- **TeachingRequestEvent**: Inbound Kafka payload published by the Planner to the `"teaching"` topic. Contains `request_id` (unique per request), `user_prompt` (the question to explain), `user_level` (beginner/intermediate/advanced), `rag_compiled` (RAG output string, default `""`), and `sid` (Socket.IO session ID for frontend routing). Defined in `project/schemas.py`.
- **TeachingCompletionEvent**: Outbound Kafka payload published by the Teaching Agent to `"teaching-complete"`. Contains `request_id`, `sid`, and `user_level` (all passed through verbatim from the request), and `content` (JSON-serialized `TeachingContent` string; empty string on error). Defined in `project/schemas.py`.
- **TeachingTopics**: Enum in `project/topics.py` with value `TEACHING_COMPLETE = "teaching-complete"` — the outbound topic owned by the Teaching Agent. The inbound topic `"teaching"` is registered under `PlannerTopics.TEACHING`, consistent with the pattern used by `PlannerTopics.RAG`. Both `PlannerTopics.TEACHING` and `TeachingTopics.TEACHING_COMPLETE` are included in `get_all_topic_names()` so the backend service bootstraps both topics at startup.
- **TeachingWorker**: Owns the Kafka consume → dispatch → publish lifecycle. Lives in `teaching_agent/worker.py`. Follows the same structure as `RAGWorker`: injectable factories for consumer, producer, and handler; background poll thread; `start()` / `stop()` / `get_state()` interface.
- **TeachingRequestEventHandler**: Business logic bridge between Kafka and the core pipeline. Lives in `teaching_agent/handlers.py`. Parses `TeachingRequestEvent`, maps `user_prompt`→`topic` / `user_level`→`output_mode` / `rag_compiled`→`context`, calls `TeachingAgent.run()`, builds `TeachingCompletionEvent`, and publishes it. Has injectable `agent_factory` and `publisher` dependencies so it can be tested without Kafka.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid requests return a schema-valid `TeachingAgentOutput` matching the defined contract.
- **SC-002**: For any topic processed at all three modes, automated comparison confirms the responses are qualitatively different in structure and vocabulary in 100% of runs.
- **SC-003**: 100% of beginner-mode responses include a non-null `diagram` field containing valid Mermaid syntax.
- **SC-004**: 100% of generated Mermaid diagrams (across all modes) pass syntax validation before being included in the response.
- **SC-005**: Token consumption stays within the per-mode ceiling set via `TEACHING_{MODE}_MAX_TOKENS` (default 4096 each) in 100% of runs.
- **SC-006**: Error conditions (empty topic, LLM failure, invalid diagram) always produce a schema-valid `status: "error"` response with no unhandled exceptions in 100% of runs.
- **SC-007**: A single Teaching Agent request for any mode completes within a time budget suitable for a live tutoring interaction, with no fatal crash on LLM or diagram validation failures.
- **SC-008**: 100% of `TeachingCompletionEvent` messages published to `"teaching-complete"` carry the same `request_id`, `sid`, and `user_level` as the originating `TeachingRequestEvent`.
- **SC-009**: 100% of processed requests — including error cases — result in a `TeachingCompletionEvent` being published. The Planner is never left waiting without a response.
- **SC-010**: A malformed inbound Kafka message never crashes the worker poll loop; subsequent messages continue to be processed in 100% of cases.
- **SC-011**: 100% of successful requests publish at least one `StreamTokensEventBody` event with `field: "explanation"` to `"stream-tokens"` before the `TeachingCompletionEvent` is published to `"teaching-complete"`.
- **SC-012**: 100% of requests — including error cases — result in a stream-complete sentinel (`{"done": true}`) published to `"stream-tokens"`. The frontend is never left waiting without an end signal.
- **SC-013**: 100% of diagram tokens published to `"stream-tokens"` are complete valid Mermaid strings. No partial diagram tokens are ever published.
- **SC-014**: When `context` is non-empty, the generated explanation MUST demonstrably draw from the provided reference material rather than defaulting to generic general-knowledge content about the topic.

## Assumptions

- The Teaching Agent is invoked exclusively via Kafka. The Planner Agent publishes a `TeachingRequestEvent` to the `"teaching"` topic; the Teaching Agent worker consumes it. No direct Python calls, REST calls, or UI calls are made to the Teaching Agent at runtime.
- The `"teaching"` and `"teaching-complete"` Kafka topics are bootstrapped by the backend service at startup via `project/topics.py`. The Teaching Agent worker does not create topics; it assumes they exist.
- The `context` field carries study material compiled by the RAG Agent from the user's course documents. It is the primary reference source for the LLM — prompts MUST instruct the model to prioritize this content over general knowledge when it is non-empty. When `context` is empty, the agent generates a complete response from general knowledge.
- `request_id` is assigned by the Planner Agent before publishing to Kafka. The Teaching Agent treats it as an opaque string and passes it through unchanged.
- `sid` is the Socket.IO session ID assigned by the backend when the user's browser connects. It is threaded through the Planner via `TeachingRequestEvent` and echoed back in `TeachingCompletionEvent` so the backend can route the completion event to the correct WebSocket session. The Teaching Agent never reads or validates its contents.
- LLM connection parameters (API key, model name, temperature, token limits) are provided through environment variables. During development, a free-tier provider (e.g. Groq, Gemini) may be used. In production, the target provider may differ. The agent logic MUST NOT depend on any provider-specific SDK — all LLM calls go through `teaching_agent/llm_client.py`.
- The LLM is prompted to return markdown output with bold section headers (`**Explanation**`, `**Diagram**`, `**Notes**`, `**Example**`). This markdown is streamed token-by-token to the frontend via `"stream-tokens"` and delivered in full as `TeachingCompletionEvent.content` on `"teaching-complete"`. JSON mode (`response_format`) is not used for the LLM call.
- OCR, PDF processing, and direct retrieval are out of scope; that responsibility belongs to the RAG Agent.
- Downstream consumers (Quiz Agent, Evaluation Agent) read from `"teaching-complete"`. Breaking schema changes to `TeachingCompletionEvent` require coordination with those teams.
- Python code examples are the expected language for intermediate and advanced `example` fields; this is a product-level assumption aligned with the CS curriculum focus.
