# Feature Specification: Teaching Agent

**Feature Branch**: `[002-build-teaching-agent]`
**Created**: 2026-05-28
**Status**: In Progress — Core pipeline complete; Kafka integration pending
**Input**: User description: "Build the Teaching Agent component of a multi-agent AI tutoring system."

## Implementation Phases

| Phase | Scope | Status |
|---|---|---|
| Phase 1 — Core pipeline | `TeachingAgent.run()`, schemas, prompts, validators, helpers, LLM client, config | **Complete** |
| Phase 2 — Kafka integration | `kafka.py`, `handlers.py`, `worker.py`, Kafka event schemas, topic registration | **Pending** |

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
response back to the originating request via `request_id` and `session_ctx`.

**Why this priority**: Kafka is the only inter-agent communication bus. Without this layer the
Teaching Agent cannot participate in the system regardless of how well the core pipeline works.

**Independent Test**: Publish a valid `TeachingRequestEvent` payload to the `"teaching"` topic
and verify that a `TeachingCompletionEvent` appears on `"teaching-complete"` with the same
`request_id`, `session_ctx`, and a valid `TeachingAgentOutput` payload.

**Acceptance Scenarios**:

1. **Given** a valid `TeachingRequestEvent` on the `"teaching"` topic, **When** the worker consumes it, **Then** `TeachingAgent.run()` is invoked with the extracted `topic`, `output_mode`, and `context` fields.
2. **Given** the core pipeline returns `status: "ok"`, **When** the result is assembled, **Then** a `TeachingCompletionEvent` with `status: "ok"` is published to `"teaching-complete"` within the same processing cycle.
3. **Given** the core pipeline returns `status: "error"` (invalid input or LLM failure), **When** the result is assembled, **Then** a `TeachingCompletionEvent` with `status: "error"` and null `content` is still published to `"teaching-complete"` — the Planner is always notified.
4. **Given** any `TeachingCompletionEvent`, **When** it is published, **Then** `request_id` and `session_ctx` are copied verbatim from the inbound `TeachingRequestEvent` for downstream correlation.
5. **Given** a malformed or schema-invalid Kafka payload, **When** the worker receives it, **Then** the error is logged and the worker continues processing subsequent messages without crashing.

---

### Edge Cases

- Topic is a single word vs. a multi-word phrase (e.g., "Trees" vs. "Balanced Binary Search Trees").
- `context` field is empty string — agent must handle gracefully and still produce a complete response.
- `context` field contains a lengthy prior-session summary — agent must incorporate it without exceeding the token ceiling for the mode.
- Two requests with the same topic but different `output_mode` values — responses must be qualitatively different, not just length-adjusted.
- Topic is ambiguous or out of scope of a standard CS curriculum — agent must still return a structured, best-effort response rather than failing.
- LLM call fails or returns an empty response — agent must return `status: "error"` with an appropriate message rather than propagating an exception.
- Generated Mermaid diagram is syntactically invalid — agent must not return the invalid diagram; it must either fix it or set `diagram` to null.
- Kafka payload is missing required fields or has wrong types — worker must log and skip, never crash.
- `session_ctx` is an empty dict `{}` — valid; worker must pass it through to the completion event unchanged.
- Same `request_id` arrives twice (retry) — worker processes it again; idempotency is the Planner's responsibility.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a structured input payload containing `topic` (non-empty string), `output_mode` (one of: `beginner`, `intermediate`, `advanced`), and `context` (string, may be empty).
- **FR-002**: The system MUST return a structured output payload containing `status`, `output_mode`, `content` (with `explanation`, `diagram`, `notes`, `example`), and `metadata` (with `topic`, `tokens_used`, `model`) in every response, including error cases.
- **FR-003**: The system MUST treat `output_mode` as authoritative from input and MUST NOT infer or modify it based on topic or context.
- **FR-004**: The system MUST produce qualitatively distinct explanations for each output mode — the same topic processed at different modes must yield structurally and substantively different responses.
- **FR-005**: In beginner mode, the `diagram` field MUST always be non-null and contain a valid Mermaid flowchart or sequence diagram representing the topic visually.
- **FR-006**: In intermediate and advanced modes, the `diagram` field MUST be included only when the topic has structural or sequential complexity that benefits from visualization; otherwise `diagram` MUST be null.
- **FR-007**: The system MUST validate Mermaid diagram syntax before including it in the response; invalid diagrams MUST NOT be returned.
- **FR-008**: The system MUST enforce per-mode token ceilings: 4096 tokens for beginner, 4096 tokens for intermediate, 4096 tokens for advanced.
- **FR-009**: The system MUST use a dedicated LLM client module scoped to the Teaching Agent. All model configuration (API key, model name, temperature, token limits) MUST be supplied via environment variables and MUST NOT be hardcoded. The client MUST be swappable so the underlying provider (e.g. Gemini for development, Claude for production) can be changed without modifying agent logic.
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
- **FR-020**: The Teaching Agent worker MUST extract `topic`, `output_mode`, and `context` from the inbound `TeachingRequestEvent` and pass them to `TeachingAgent.run()` unchanged. The core pipeline logic MUST NOT be modified.
- **FR-021**: Upon receiving a result from `TeachingAgent.run()` — whether `status: "ok"` or `status: "error"` — the worker MUST publish a `TeachingCompletionEvent` to the Kafka topic `"teaching-complete"`. The Planner is always notified regardless of outcome.
- **FR-022**: `TeachingRequestEvent` MUST include `request_id` (non-empty string, unique per request, assigned by the Planner) and `session_ctx` (dict, may be empty) for request tracing and user/session correlation.
- **FR-023**: `TeachingCompletionEvent` MUST carry back the same `request_id` and `session_ctx` from the originating `TeachingRequestEvent` verbatim, so the Planner can correlate responses to requests.
- **FR-024**: `TeachingCompletionEvent` MUST include `started_at` (ISO 8601 UTC), `completed_at` (ISO 8601 UTC), and `duration_ms` (non-negative integer) for audit and latency tracking.
- **FR-025**: Both `TeachingRequestEvent` and `TeachingCompletionEvent` schemas MUST be defined in `project/schemas.py` in the Teaching Agent section. No schema definitions belong inside `teaching_agent/`.
- **FR-026**: `"teaching"` MUST be added to the existing `PlannerTopics` enum in `project/topics.py` (consistent with `PlannerTopics.RAG`); `"teaching-complete"` MUST be registered as `TeachingTopics.TEACHING_COMPLETE` in a new `TeachingTopics` enum. Both values MUST be included in `get_all_topic_names()` so the backend service bootstraps them at startup.
- **FR-027**: The Kafka integration MUST follow the same three-file structure used by the RAG agent: `teaching_agent/kafka.py` (I/O primitives and Protocol types), `teaching_agent/handlers.py` (business logic, zero Kafka I/O), `teaching_agent/worker.py` (lifecycle, poll loop). All Kafka-facing dependencies MUST be injectable for testing — no real Kafka connection required in tests.
- **FR-028**: A malformed or schema-invalid inbound Kafka message MUST be logged with its `request_id` (or `"unknown"` if absent) and skipped; the worker poll loop MUST continue processing subsequent messages.

### Key Entities

- **TeachingAgentInput**: The input contract. Contains `topic` (the subject to be explained), `output_mode` (the target learner level), and `context` (optional prior session summary passed by the Planner Agent).
- **TeachingAgentOutput**: The output contract. Contains `status` (`ok` or `error`), `output_mode` (mirrored from input), `content` (the explanation payload), and `metadata` (audit information).
- **TeachingContent**: The structured explanation payload. Contains `explanation` (full markdown explanation), `diagram` (Mermaid syntax or null), `notes` (summary markdown), and `example` (worked example or code snippet, or null).
- **OutputMode**: Enum of `beginner`, `intermediate`, `advanced`. Determines explanation structure, diagram rules, token ceiling, and language register.
- **TeachingMetadata**: Audit record. Contains `topic` (mirrored from input), `tokens_used` (actual consumption), and `model` (model identifier).
- **TeachingRequestEvent**: Inbound Kafka payload published by the Planner to the `"teaching"` topic. Contains `request_id` (unique per request), `session_ctx` (user/session tracking dict), `topic`, `output_mode`, `context`, and optional `created_at` / `source` fields. Defined in `project/schemas.py`.
- **TeachingCompletionEvent**: Outbound Kafka payload published by the Teaching Agent to `"teaching-complete"`. Contains `request_id` and `session_ctx` (passed through verbatim from the request), `topic`, `output_mode`, `status`, `content` (null on error), `tokens_used`, `model`, `started_at`, `completed_at`, `duration_ms`, and `errors`. Defined in `project/schemas.py`.
- **TeachingTopics**: Enum in `project/topics.py` with value `TEACHING_COMPLETE = "teaching-complete"` — the outbound topic owned by the Teaching Agent. The inbound topic `"teaching"` is registered under `PlannerTopics.TEACHING`, consistent with the pattern used by `PlannerTopics.RAG`. Both `PlannerTopics.TEACHING` and `TeachingTopics.TEACHING_COMPLETE` are included in `get_all_topic_names()` so the backend service bootstraps both topics at startup.
- **TeachingWorker**: Owns the Kafka consume → dispatch → publish lifecycle. Lives in `teaching_agent/worker.py`. Follows the same structure as `RAGWorker`: injectable factories for consumer, producer, and handler; background poll thread; `start()` / `stop()` / `get_state()` interface.
- **TeachingRequestEventHandler**: Business logic bridge between Kafka and the core pipeline. Lives in `teaching_agent/handlers.py`. Parses `TeachingRequestEvent`, calls `TeachingAgent.run()`, builds `TeachingCompletionEvent`, and publishes it. Has injectable `agent_factory`, `publisher`, and `clock` dependencies so it can be tested without Kafka.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid requests return a schema-valid `TeachingAgentOutput` matching the defined contract.
- **SC-002**: For any topic processed at all three modes, automated comparison confirms the responses are qualitatively different in structure and vocabulary in 100% of runs.
- **SC-003**: 100% of beginner-mode responses include a non-null `diagram` field containing valid Mermaid syntax.
- **SC-004**: 100% of generated Mermaid diagrams (across all modes) pass syntax validation before being included in the response.
- **SC-005**: Token consumption stays within the per-mode ceiling (4096 beginner / 4096 intermediate / 4096 advanced) in 100% of runs.
- **SC-006**: Error conditions (empty topic, LLM failure, invalid diagram) always produce a schema-valid `status: "error"` response with no unhandled exceptions in 100% of runs.
- **SC-007**: A single Teaching Agent request for any mode completes within a time budget suitable for a live tutoring interaction, with no fatal crash on LLM or diagram validation failures.
- **SC-008**: 100% of `TeachingCompletionEvent` messages published to `"teaching-complete"` carry the same `request_id` and `session_ctx` as the originating `TeachingRequestEvent`.
- **SC-009**: 100% of processed requests — including error cases — result in a `TeachingCompletionEvent` being published. The Planner is never left waiting without a response.
- **SC-010**: A malformed inbound Kafka message never crashes the worker poll loop; subsequent messages continue to be processed in 100% of cases.

## Assumptions

- The Teaching Agent is invoked exclusively via Kafka. The Planner Agent publishes a `TeachingRequestEvent` to the `"teaching"` topic; the Teaching Agent worker consumes it. No direct Python calls, REST calls, or UI calls are made to the Teaching Agent at runtime.
- The `"teaching"` and `"teaching-complete"` Kafka topics are bootstrapped by the backend service at startup via `project/topics.py`. The Teaching Agent worker does not create topics; it assumes they exist.
- The `context` field carries a prior session summary generated by a Memory Agent; the Memory Agent is a separate system component not implemented in this feature.
- When `context` is empty, the agent produces a complete response without prior-session context.
- `request_id` is assigned by the Planner Agent before publishing to Kafka. The Teaching Agent treats it as an opaque string and passes it through unchanged.
- `session_ctx` is a free-form dict assigned by the Planner. The Teaching Agent passes it through unchanged in `TeachingCompletionEvent`. The Teaching Agent never reads or validates its contents.
- LLM connection parameters (API key, model name, temperature, token limits) are provided through environment variables. During development, a free-tier provider (e.g. Groq, Gemini) may be used. In production, the target provider may differ. The agent logic MUST NOT depend on any provider-specific SDK — all LLM calls go through `teaching_agent/llm_client.py`.
- Output format is always JSON; no plain-text or streaming responses are produced in this version.
- OCR, PDF processing, and direct retrieval are out of scope; that responsibility belongs to the RAG Agent.
- Downstream consumers (Quiz Agent, Evaluation Agent) read from `"teaching-complete"`. Breaking schema changes to `TeachingCompletionEvent` require coordination with those teams.
- Python code examples are the expected language for intermediate and advanced `example` fields; this is a product-level assumption aligned with the CS curriculum focus.
