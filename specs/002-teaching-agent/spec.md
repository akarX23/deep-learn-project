# Feature Specification: Teaching Agent

**Feature Branch**: `[002-build-teaching-agent]`
**Created**: 2026-05-28
**Status**: Draft
**Input**: User description: "Build the Teaching Agent component of a multi-agent AI tutoring system."

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
diagram, follows the five-part structure, and stays within the 512-token ceiling.

**Acceptance Scenarios**:

1. **Given** a valid request with `output_mode: "beginner"` and a non-empty topic, **When** the agent processes it, **Then** the response contains a non-empty explanation that begins with a one-sentence plain-English summary and includes a real-world analogy.
2. **Given** a beginner request, **When** the response is produced, **Then** the `diagram` field is always non-null and contains valid Mermaid syntax.
3. **Given** a beginner request, **When** the response is produced, **Then** `notes` contains three bullet-point takeaways with no unexplained jargon, and `example` contains a concrete worked example with plain-English step commentary.
4. **Given** a beginner request, **When** output is generated, **Then** total tokens consumed do not exceed 512.

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
code snippet, presents trade-offs, and stays within the 1024-token ceiling.

**Acceptance Scenarios**:

1. **Given** a valid request with `output_mode: "intermediate"`, **When** the agent processes it, **Then** the explanation starts with a precise definition and includes a section on mechanics and trade-offs.
2. **Given** an intermediate request for a structurally complex topic, **When** the response is produced, **Then** a Mermaid diagram is included and is more detailed than a beginner diagram would be for the same topic.
3. **Given** an intermediate request for a topic with no structural complexity, **When** the response is produced, **Then** the `diagram` field may be null.
4. **Given** an intermediate request, **When** output is generated, **Then** total tokens consumed do not exceed 1024.

---

### User Story 3 - Advanced-Mode Explanation (Priority: P3)

A practitioner wants depth, internals, complexity analysis, edge cases, and a pointer
to further exploration. The Teaching Agent returns a reference-quality explanation
appropriate for a senior engineer.

**Why this priority**: Advanced users have the highest expectations and will validate the
tool against their existing knowledge. Serving them well builds credibility.

**Independent Test**: Send a valid request with `output_mode: "advanced"` for any topic
and verify that the explanation includes a formal definition, internal mechanics,
complexity analysis, edge cases, and further-exploration pointers within 2048 tokens.

**Acceptance Scenarios**:

1. **Given** a valid request with `output_mode: "advanced"`, **When** the agent processes it, **Then** the explanation includes a formal or semi-formal definition, a deep-dive into internal mechanics with time/space complexity, and at least one documented edge case or failure mode.
2. **Given** an advanced request, **When** the response is produced, **Then** the `notes` field is a dense technical reference usable as a practitioner cheat sheet.
3. **Given** an advanced request, **When** the response is produced, **Then** the `example` demonstrates non-trivial usage (optimization, edge-case handling, or architectural pattern).
4. **Given** an advanced request, **When** output is generated, **Then** total tokens consumed do not exceed 2048.

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

### Edge Cases

- Topic is a single word vs. a multi-word phrase (e.g., "Trees" vs. "Balanced Binary Search Trees").
- `context` field is empty string — agent must handle gracefully and still produce a complete response.
- `context` field contains a lengthy prior-session summary — agent must incorporate it without exceeding the token ceiling for the mode.
- Two requests with the same topic but different `output_mode` values — responses must be qualitatively different, not just length-adjusted.
- Topic is ambiguous or out of scope of a standard CS curriculum — agent must still return a structured, best-effort response rather than failing.
- LLM call fails or returns an empty response — agent must return `status: "error"` with an appropriate message rather than propagating an exception.
- Generated Mermaid diagram is syntactically invalid — agent must not return the invalid diagram; it must either fix it or set `diagram` to null.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a structured input payload containing `topic` (non-empty string), `output_mode` (one of: `beginner`, `intermediate`, `advanced`), and `context` (string, may be empty).
- **FR-002**: The system MUST return a structured output payload containing `status`, `output_mode`, `content` (with `explanation`, `diagram`, `notes`, `example`), and `metadata` (with `topic`, `tokens_used`, `model`) in every response, including error cases.
- **FR-003**: The system MUST treat `output_mode` as authoritative from input and MUST NOT infer or modify it based on topic or context.
- **FR-004**: The system MUST produce qualitatively distinct explanations for each output mode — the same topic processed at different modes must yield structurally and substantively different responses.
- **FR-005**: In beginner mode, the `diagram` field MUST always be non-null and contain a valid Mermaid flowchart or sequence diagram representing the topic visually.
- **FR-006**: In intermediate and advanced modes, the `diagram` field MUST be included only when the topic has structural or sequential complexity that benefits from visualization; otherwise `diagram` MUST be null.
- **FR-007**: The system MUST validate Mermaid diagram syntax before including it in the response; invalid diagrams MUST NOT be returned.
- **FR-008**: The system MUST enforce per-mode token ceilings: 512 tokens for beginner, 1024 tokens for intermediate, 2048 tokens for advanced.
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

### Key Entities

- **TeachingAgentInput**: The input contract. Contains `topic` (the subject to be explained), `output_mode` (the target learner level), and `context` (optional prior session summary passed by the Planner Agent).
- **TeachingAgentOutput**: The output contract. Contains `status` (`ok` or `error`), `output_mode` (mirrored from input), `content` (the explanation payload), and `metadata` (audit information).
- **TeachingContent**: The structured explanation payload. Contains `explanation` (full markdown explanation), `diagram` (Mermaid syntax or null), `notes` (summary markdown), and `example` (worked example or code snippet, or null).
- **OutputMode**: Enum of `beginner`, `intermediate`, `advanced`. Determines explanation structure, diagram rules, token ceiling, and language register.
- **TeachingMetadata**: Audit record. Contains `topic` (mirrored from input), `tokens_used` (actual consumption), and `model` (model identifier).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid requests return a schema-valid `TeachingAgentOutput` matching the defined contract.
- **SC-002**: For any topic processed at all three modes, automated comparison confirms the responses are qualitatively different in structure and vocabulary in 100% of runs.
- **SC-003**: 100% of beginner-mode responses include a non-null `diagram` field containing valid Mermaid syntax.
- **SC-004**: 100% of generated Mermaid diagrams (across all modes) pass syntax validation before being included in the response.
- **SC-005**: Token consumption stays within the per-mode ceiling (512 / 1024 / 2048) in 100% of runs.
- **SC-006**: Error conditions (empty topic, LLM failure, invalid diagram) always produce a schema-valid `status: "error"` response with no unhandled exceptions in 100% of runs.
- **SC-007**: A single Teaching Agent request for any mode completes within a time budget suitable for a live tutoring interaction, with no fatal crash on LLM or diagram validation failures.

## Assumptions

- Input always arrives from the Planner Agent; the Teaching Agent is never called directly from the Streamlit UI or any other source.
- The `context` field carries a prior session summary generated by a Memory Agent; the Memory Agent is a separate system component not implemented in this feature.
- When `context` is empty, the agent produces a complete response without prior-session context.
- LLM connection parameters (API key, model name, temperature, token limits) are provided through environment variables. During development, a free-tier provider (e.g. Google Gemini) may be used. In production, the target provider is Anthropic Claude. The agent logic MUST NOT depend on any provider-specific SDK directly — all LLM calls MUST go through the Teaching Agent's own LLM client module, making the provider swappable via config.
- Output format is always JSON; no plain-text or streaming responses are produced in this version.
- OCR, PDF processing, and direct retrieval are out of scope; that responsibility belongs to the RAG Agent.
- Downstream consumers (Quiz Agent, Evaluation Agent) expect the output JSON structure to remain stable; breaking schema changes require coordination with those teams.
- Python code examples are the expected language for intermediate and advanced `example` fields; this is a product-level assumption aligned with the CS curriculum focus.
