# Data Model: Planner Agent

## Entities

### PlannerInput
- **Description**: Request payload received by the Planner Agent from the caller (application layer or orchestrator).
- **Fields**:
  - `request_id`: str (UUID string) — unique request identifier, mirrored in output
  - `user_query`: str — raw natural language query from the user
  - `session_context`: str | None — optional prior conversation context to assist intent classification
  - `available_files`: list[str] | None — optional PDF paths; hint for RAG routing payload construction
  - `schema_version`: str (default "1.0") — contract version
- **Validation rules**:
  - `request_id` must be a valid UUID string.
  - `user_query` must be a non-empty string after stripping whitespace.
  - `available_files`, if provided, must be a non-empty list.
  - `schema_version` must be non-empty.

---

### AgentType (Enum)
- **Description**: Identifies the registered specialized agent to route to.
- **Allowed values**:
  - `RAG_AGENT` — retrieval-augmented generation over uploaded PDFs
  - `TEACHING_AGENT` — structured explanation and tutoring
  - `QUIZ_EVAL_AGENT` — quiz generation and learner evaluation
  - `UNKNOWN` — fallback when no agent matches above threshold

---

### QueryComplexity (Enum)
- **Description**: Classifies the user query complexity to determine pipeline path.
- **Allowed values**:
  - `SIMPLE` — direct, unambiguous query with sufficient context; fast path (no rewriting, no guardrails)
  - `COMPLEX` — vague, very short, multi-intent, or potentially unsafe query; triggers rewrite + guardrails

---

### GuardrailResult (Enum)
- **Description**: Outcome of the safety and scope check applied to COMPLEX queries.
- **Allowed values**:
  - `ALLOWED` — query is educational, in-scope, and safe; continue pipeline
  - `WARN` — query is borderline; continue with warning added to errors
  - `BLOCKED` — query is harmful, out-of-scope, or adversarial; halt with `failed` status

---

### IntentCandidate
- **Description**: A single agent candidate produced during LLM-based intent classification.
- **Fields**:
  - `agent_type`: AgentType
  - `confidence_score`: float [0.0, 1.0] — LLM-estimated relevance to this agent's intent description
  - `reasoning`: str — brief explanation from the LLM for this score
- **Validation rules**:
  - `confidence_score` must be in [0.0, 1.0].

---

### RoutingDecision
- **Description**: The Planner's final routing determination, included in PlannerOutput.
- **Fields**:
  - `target_agent`: AgentType — the chosen routing destination (UNKNOWN if ambiguous)
  - `confidence_score`: float [0.0, 1.0] — confidence of the top candidate
  - `reasoning`: str — rationale for the routing decision
  - `constructed_payload`: dict | None — fully-built agent-specific input payload (None when ambiguous/failed)
  - `candidate_agents`: list[IntentCandidate] — all candidates with scores (always populated)
  - `query_was_rewritten`: bool — whether query rewriting was applied
  - `hyde_applied`: bool — whether HyDE augmentation was applied to the payload
- **Validation rules**:
  - `constructed_payload` must be present when `target_agent` is not UNKNOWN.
  - `candidate_agents` must be non-empty.

---

### PlannerOutput
- **Description**: Response contract returned by the Planner Agent to the caller.
- **Fields**:
  - `request_id`: str — mirrored from PlannerInput
  - `user_query`: str — mirrored from PlannerInput (original, pre-rewrite)
  - `schema_version`: str — mirrored from PlannerInput
  - `routing_decision`: RoutingDecision
  - `status`: str — one of `routed` | `ambiguous` | `failed`
  - `errors`: list[str] — non-fatal warnings or fatal error descriptions
- **Validation rules**:
  - `status` is `routed` only when `routing_decision.target_agent` is not UNKNOWN and `constructed_payload` is present.
  - `status` is `ambiguous` when all candidates are below confidence threshold or retry limit is reached.
  - `status` is `failed` when guardrail returns BLOCKED, input validation fails, or an unrecoverable error occurs.
  - `errors` is non-empty when status is `ambiguous` or `failed`.

---

### AgentRegistryEntry
- **Description**: Registration record for a specialized agent in the Planner's registry.
- **Fields**:
  - `agent_type`: AgentType
  - `intent_description`: str — natural language description used in LLM classification prompt
  - `intent_keywords`: list[str] — keywords for heuristic fallback matching
  - `supports_hyde`: bool — whether HyDE augmentation is beneficial for this agent (true for RAG_AGENT)
  - `input_contract_builder`: Callable[[PlannerInput, PlannerState], dict] — constructs the typed agent-specific input payload

---

### PlannerState (LangGraph internal)
- **Description**: Mutable state object carried through the LangGraph StateGraph nodes.
- **Fields**:
  - `input`: PlannerInput
  - `complexity`: QueryComplexity | None
  - `query_rewritten`: str | None — expanded/rewritten query (if applied)
  - `hyde_doc`: str | None — hypothetical document (if HyDE applied)
  - `guardrail_result`: GuardrailResult | None
  - `candidates`: list[IntentCandidate] — populated by classify_intent node
  - `routing_decision`: RoutingDecision | None
  - `output`: PlannerOutput | None
  - `errors`: list[str]
  - `attempt_count`: int — counts retry loop iterations (max = MAX_RETRIES)

---

## Relationships

- One `PlannerInput` maps to exactly one `PlannerOutput`.
- One `PlannerOutput` contains exactly one `RoutingDecision`.
- One `RoutingDecision` contains one or more `IntentCandidate` records.
- The `RoutingDecision.constructed_payload` conforms to the target agent's input contract (e.g., `RAGAgentInput` from `project/schemas.py`).
- Each `AgentRegistryEntry` maps one `AgentType` to its intent description, keywords, HyDE flag, and payload builder.

---

## State Transitions

### Request-level pipeline state

```
received
  → validate_input
    → INVALID: emit failed PlannerOutput
    → VALID: detect_complexity
      → SIMPLE: classify_intent
      → COMPLEX: rewrite_query → classify_intent
        (with guardrail check before build_payload for COMPLEX)

classify_intent
  → all candidates < threshold: emit ambiguous PlannerOutput
  → top candidate ≥ threshold:
    → supports_hyde AND (short query OR confidence < 0.85): generate_hyde_doc → build_payload
    → otherwise: build_payload (with guardrail check if COMPLEX)

build_payload
  → payload valid: emit routed PlannerOutput
  → payload invalid AND attempt_count < MAX_RETRIES: retry → rewrite_query → classify_intent
  → payload invalid AND attempt_count ≥ MAX_RETRIES: emit ambiguous PlannerOutput
```

### Guardrail state (COMPLEX path only)
```
ALLOWED → continue to build_payload
WARN    → continue to build_payload (warning added to errors)
BLOCKED → emit failed PlannerOutput
```

---

## Derived Fields

- `RoutingDecision.query_was_rewritten`: true if `PlannerState.query_rewritten` is not None.
- `RoutingDecision.hyde_applied`: true if `PlannerState.hyde_doc` is not None.
- `PlannerOutput.status`: derived from pipeline terminal state (routed / ambiguous / failed).
- `PlannerOutput.errors`: accumulated across all pipeline nodes.
