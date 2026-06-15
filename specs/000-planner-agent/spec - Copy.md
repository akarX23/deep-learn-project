# Feature Specification: Planner Agent
**Owner**: 'Himanshu5@iisc.ac.in'
**Feature Branch**: `[000-build-planner-agent]`
**Created**: 2026-05-30
**Status**: Draft
**Input**: User description: "Implement the Planner Agent as the central async orchestrator for a multi-agent AI Tutor application. The Planner receives user queries via Kafka, assesses learner level, engages in multi-turn clarification if needed, decomposes the learning task, dispatches RAG / Teaching / Quiz agents in parallel via Kafka topics, collects and validates their responses, and synthesizes a final answer."

## Architecture Context

The Planner Agent is the **central async orchestrator** of the AI Tutor system. It does not return a payload to a synchronous caller — it participates in a **Kafka-based event loop**:

| Direction | Topic | Purpose |
|-----------|-------|---------|
| Consume | `init-planner` | Receive incoming user query |
| Produce | `clarify-user-level` | Ask learner a clarification question |
| Consume | `user-clarification-response` | Receive learner's answer |
| Produce | `rag` | Dispatch RAG Agent task |
| Produce | `teaching` | Dispatch Teaching Agent task |
| Produce | `quiz` | Dispatch Quiz & Eval Agent task |
| Consume | `rag-complete` | Receive RAG Agent output |
| Consume | `material-compiled` | Receive Teaching Agent output |
| Consume | `quiz-complete` | Receive Quiz Agent output |
| Produce | `planner-response` | Publish final synthesized response to caller |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand Query, Assess Learner Level, and Orchestrate Agents (Priority: P1)

As the AI Tutor system, I need the Planner Agent to receive a learner's query, understand their proficiency level (naive / intermediate / advanced), decompose the task, and dispatch the appropriate specialized agents so the learner receives a tailored, coherent learning response.

**Why this priority**: Learner-level awareness is what makes the tutor personalised. Without it, all responses default to a generic difficulty — defeating the purpose of an AI Tutor.

**Independent Test**: Submit a query with rich context signals (e.g., "I just started learning ML, what is a neural network?") and verify the output includes: learner_level=naive, both RAG and Teaching agents dispatched, and a synthesized response calibrated to a beginner audience.

**Acceptance Scenarios**:

1. **Given** a query containing strong level signals (e.g., "I'm a beginner…"), **When** the Planner processes it, **Then** learner_level is set to `naive` with confidence ≥ 0.75 and agent payloads include learner_level in their input.
2. **Given** a query with technical vocabulary and depth (e.g., "Derive the backpropagation equations for a multi-layer perceptron"), **When** processed, **Then** learner_level is set to `advanced`.
3. **Given** a query requiring both retrieval and explanation (e.g., "Explain gradient descent from Chapter 3"), **When** processed, **Then** both RAG Agent and Teaching Agent are dispatched and their payloads are published to the respective Kafka topics.
4. **Given** all dispatched agents complete successfully, **When** responses are received, **Then** a synthesized PlannerResponse is published to `planner-response` with status `complete`.

---

### User Story 2 - Multi-Turn Learner Clarification via Kafka (Priority: P2)

As the AI Tutor system, I need the Planner Agent to ask the learner a targeted clarification question when their level or intent is unclear, wait for the response, and then proceed with planning — so that the learning path is accurate even for vague or ambiguous queries.

**Why this priority**: Learner-level cannot always be inferred from a single short query. Asking one focused question dramatically improves personalisation without disrupting the flow.

**Independent Test**: Submit a one-word query ("backpropagation"), verify a clarification message is produced on `clarify-user-level`, simulate a response on `user-clarification-response`, and confirm the final response is calibrated to the stated level.

**Acceptance Scenarios**:

1. **Given** a query that is too short or level-ambiguous, **When** the Planner cannot infer learner_level with confidence ≥ 0.65, **Then** exactly one clarification question is produced on `clarify-user-level` and processing pauses.
2. **Given** a clarification response is received on `user-clarification-response`, **When** the Planner resumes, **Then** learner_level is updated and agent dispatch proceeds normally.
3. **Given** no clarification response arrives within the configured timeout (default 120 seconds), **When** timeout elapses, **Then** the Planner defaults to `intermediate` level, logs a warning, and continues.
4. **Given** clarification has already been asked once in this session, **When** the learner submits another ambiguous query, **Then** no second clarification is issued — the Planner uses the previously established level.

---

### User Story 3 - Parallel Agent Dispatch and Response Collection (Priority: P2)

As the AI Tutor system, I need the Planner Agent to dispatch multiple specialist agents concurrently via Kafka and collect their responses before synthesizing a final answer, so the overall response time is minimised.

**Why this priority**: Sequential dispatch would double or triple end-to-end latency. Parallel execution is essential for a responsive learning experience.

**Independent Test**: Submit a query that requires both RAG and Teaching agents. Verify messages appear on both `rag` and `teaching` topics within the same processing cycle, and that the Planner waits for both `rag-complete` and `material-compiled` before synthesizing.

**Acceptance Scenarios**:

1. **Given** the learning plan requires RAG + Teaching, **When** dispatch runs, **Then** both Kafka produce calls happen before either consume wait begins.
2. **Given** one agent (e.g., RAG) completes and another (Teaching) has not, **When** the Planner is waiting, **Then** it does not emit a partial or premature response — it waits for all dispatched agents up to the configured timeout.
3. **Given** one agent returns a failed status, **When** the Planner collects responses, **Then** it continues with available results, marks partial failure in errors, and still synthesizes a best-effort response.

---

### User Story 4 - Validate All Agent Responses Before Synthesis (Priority: P3)

As the AI Tutor system, I need the Planner Agent to validate every agent response for completeness and quality before incorporating it into the final answer, so learners never receive blank, vague, or potentially incorrect content.

**Why this priority**: Agent responses can be empty, truncated, or hallucinated. Unvalidated content reaching the learner directly damages trust and learning outcomes.

**Independent Test**: Inject a mock RAG response with an empty `compiled_material` field and verify the Planner marks it as invalid, logs the validation failure, retries or substitutes, and does not include empty content in the final synthesized response.

**Acceptance Scenarios**:

1. **Given** an agent response with an empty or whitespace-only primary field (e.g., `compiled_material = ""`), **When** validation runs, **Then** the response is rejected, a retry is dispatched (up to MAX_RETRIES), and the failure is recorded in errors.
2. **Given** an agent response whose content is shorter than MIN_CONTENT_LENGTH characters, **When** validation runs, **Then** it is flagged as `vague` and the agent is re-dispatched with an augmented prompt requesting more detail.
3. **Given** an agent returns `status: failed` or a non-200 equivalent, **When** the Planner collects it, **Then** no content from that agent is included in the synthesis and the final status is `partial` (not `complete`).
4. **Given** all agent responses pass validation, **When** synthesis runs, **Then** the final `planner-response` is published with `status: complete` and non-empty synthesized content.

---

### User Story 5 - Extend the Registry with New Agent Types (Priority: P3)

As a project contributor, I need to add a new specialist agent to the AI Tutor system by registering it in the Planner's agent registry without modifying any existing Planner logic, so the system stays extensible as the team grows.

**Acceptance Scenarios**:

1. **Given** a new agent type (e.g., `SUMMARISE_AGENT`) is added to `registry.py` with its Kafka produce topic, intent description, and response consumer topic, **When** a matching query arrives, **Then** the Planner dispatches it with zero changes to `agent.py`, `classifier.py`, or any other core file.
2. **Given** the registry is listed, **When** all entries are enumerated, **Then** every registered agent's produce/consume topics and input contract are visible.

---

### Edge Cases

**Query validation:**
- User query is empty, null, or contains only whitespace → reject immediately with `failed` status.
- User query exceeds 2000 characters → truncate and log warning, or reject if over hard limit.
- Query contains prompt injection attempts (e.g., "Ignore previous instructions and…") → guardrail must catch and block.
- Schema version in incoming Kafka message does not match supported version → reject with versioning error.
- `request_id` is missing or not a valid UUID → reject immediately.

**Learner level assessment:**
- Query contains contradictory level signals ("I'm a beginner but I know about backprop gradients") → default to `intermediate`, log ambiguity.
- Learner responds to clarification with another question instead of answering → re-ask once, then default to `intermediate`.
- session_context shows prior level was `advanced` but current query is extremely basic → flag regression, use prior level as fallback.

**Agent dispatch and response:**
- All agents time out without responding → emit `failed` status with timeout errors for each agent.
- RAG agent returns `compiled_material` that is non-empty but contains only error messages → treat as vague/invalid.
- Teaching agent returns content in a language different from the user's query language → flag as inconsistent content.
- Agent response JSON is malformed or fails pydantic schema validation → treat as failed response, retry dispatch.
- Agent response `request_id` does not match the dispatched `request_id` → discard as stale/misrouted message.
- Kafka broker is unavailable when producing → fail the request immediately with `broker_unavailable` error.
- Duplicate Kafka messages arrive for the same `request_id` and topic → deduplicate by request_id + agent_type.

**Synthesis:**
- All agents fail or produce invalid content → emit `failed` status with no synthesized content.
- Synthesized content from multiple agents contains contradictory information → include both and flag conflict in metadata.
- Final synthesized response exceeds max payload size → truncate gracefully with summary note.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST consume user queries from the Kafka topic `init-planner`, where each message is a valid `PlannerMessage` JSON payload.
- **FR-002**: The system MUST validate the incoming `PlannerMessage` for schema correctness, non-empty `user_query`, valid UUID `request_id`, and supported `schema_version` before any processing begins.
- **FR-003**: The system MUST assess the learner's proficiency level (naive / intermediate / advanced) from the query and session_context using LLM reasoning.
- **FR-004**: The system MUST produce a clarification question to the Kafka topic `clarify-user-level` when learner level confidence is below 0.65, and pause processing until a response arrives on `user-clarification-response` or the timeout elapses.
- **FR-005**: The system MUST use session_context to avoid re-asking clarification if learner level was established in a prior turn.
- **FR-006**: The system MUST decompose the learning task into a `LearningPlan` specifying which agents are required and whether they run in parallel or sequentially.
- **FR-007**: The system MUST dispatch RAG Agent tasks by producing a valid `RAGAgentInput` JSON message to the Kafka topic `rag`.
- **FR-008**: The system MUST dispatch Teaching Agent tasks by producing a valid `TeachingAgentInput` JSON message to the Kafka topic `teaching`.
- **FR-009**: The system MUST dispatch Quiz Agent tasks by producing a valid `QuizAgentInput` JSON message to the Kafka topic `quiz`.
- **FR-010**: The system MUST support parallel dispatch — producing to multiple agent topics before waiting on any response.
- **FR-011**: The system MUST consume agent responses from `rag-complete`, `material-compiled`, and `quiz-complete`, correlating each to the originating request by `request_id`.
- **FR-012**: The system MUST validate every agent response: reject blank/empty primary content fields, reject responses shorter than MIN_CONTENT_LENGTH, reject mismatched `request_id`, and reject malformed JSON.
- **FR-013**: The system MUST retry a failed or invalid agent dispatch up to MAX_RETRIES times with an augmented prompt before marking that agent as failed.
- **FR-014**: The system MUST synthesize a coherent final response from all valid agent outputs, calibrated to the learner's assessed level.
- **FR-015**: The system MUST publish the final synthesized response to the Kafka topic `planner-response` as a valid `PlannerResponse` JSON message.
- **FR-016**: The system MUST set response status to `complete` (all agents succeeded), `partial` (some failed but usable content exists), or `failed` (no usable content produced).
- **FR-017**: The system MUST mirror `request_id`, `user_id`, `session_id`, and `schema_version` from the incoming message into all produced messages and the final response.
- **FR-018**: The system MUST implement an agent registry that allows new agents to be added by contributing one `AgentRegistryEntry` (produce topic, consume topic, intent description, input builder) with zero changes to any existing core file.
- **FR-019**: The system MUST apply guardrails to detect and block prompt injection, out-of-scope, and harmful content before any agent is dispatched.
- **FR-020**: The system MUST emit structured per-step diagnostic logs (validate, assess-level, plan, dispatch, collect, validate-response, synthesize) for every request.
- **FR-021**: The system MUST handle Kafka broker unavailability gracefully by failing the request immediately with a `broker_unavailable` error rather than blocking indefinitely.
- **FR-022**: The system MUST deduplicate Kafka response messages by `request_id` + `agent_type` to guard against duplicate delivery.
- **FR-023**: The system MUST provide standalone test fixtures and automated tests covering: level assessment, clarification flow, parallel dispatch, response validation, retry logic, guardrails, registry extensibility, and synthesis.
- **FR-024**: The system MUST define measurable performance budgets: end-to-end orchestration (from `init-planner` consume to `planner-response` produce) to complete within 60 seconds under standard LLM and Kafka latency.

### Key Entities

- **PlannerMessage**: Kafka message consumed from `init-planner`. Contains request_id, session_id, user_id, user_query, session_context, available_files, schema_version.
- **LearnerLevel**: Enum — `naive`, `intermediate`, `advanced`.
- **LearnerProfile**: Assessed profile for this request. Contains learner_level, confidence_score, level_reasoning, clarification_asked (bool).
- **LearningPlan**: Decomposed task plan. Contains required_agents (list[AgentType]), parallel_groups (list of sets that can run concurrently), reasoning.
- **RAGAgentInput**: Input dispatched to `rag` topic. Contains request_id, user_prompt, file_paths, include_tables, include_images, relevance_threshold, schema_version.
- **TeachingAgentInput**: Input dispatched to `teaching` topic. Contains request_id, user_query, learner_level, learning_path, rag_material (optional), session_context, schema_version.
- **QuizAgentInput**: Input dispatched to `quiz` topic. Contains request_id, topic, learner_level, num_questions, question_types, rag_material (optional), schema_version.
- **RAGAgentOutput**: Response consumed from `rag-complete`. Contains request_id, compiled_material, extracted_pages, total_pages_processed, total_pages_included, status, errors, schema_version.
- **TeachingAgentOutput**: Response consumed from `material-compiled`. Contains request_id, teaching_content, learner_level, sections, status, errors, schema_version.
- **QuizAgentOutput**: Response consumed from `quiz-complete`. Contains request_id, questions, learner_level, total_questions, status, errors, schema_version.
- **PlannerResponse**: Final message produced to `planner-response`. Contains request_id, session_id, user_id, user_query, learner_level, learning_plan, synthesized_content, study_material, quiz, status, errors, schema_version.
- **AgentRegistryEntry**: Per-agent record: agent_type, produce_topic, consume_topic, intent_description, intent_keywords, supports_hyde, input_contract_builder (callable).

---

## Agent I/O Contracts

### PlannerMessage — consumed from `init-planner`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id":  "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id":     "usr-001",
  "user_query":  "Explain gradient descent from the uploaded chapter",
  "session_context": [
    {"role": "user",      "content": "I just started learning ML"},
    {"role": "assistant", "content": "Great! Let me know what topic you want to explore."}
  ],
  "available_files": ["rag_agent/tests/inputs/sample.pdf"],
  "schema_version": "1.0"
}
```

### ClarifyUserLevelMessage — produced to `clarify-user-level`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id":  "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "clarification_question": "To give you the best explanation, could you tell me your current familiarity with machine learning — beginner, intermediate, or advanced?",
  "context": "Your query about gradient descent could be answered at multiple levels.",
  "schema_version": "1.0"
}
```

### UserClarificationResponse — consumed from `user-clarification-response`

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id":  "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "response":   "I'm a beginner, just started two weeks ago.",
  "schema_version": "1.0"
}
```

### RAGAgentInput — produced to `rag`

```json
{
  "request_id":          "550e8400-e29b-41d4-a716-446655440000",
  "user_prompt":         "Explain gradient descent from the uploaded chapter\n\nHypothetical relevant content:\nGradient descent is an optimization algorithm that minimizes a loss function by iteratively moving in the direction of steepest descent...",
  "file_paths":          ["rag_agent/tests/inputs/sample.pdf"],
  "include_tables":      true,
  "include_images":      true,
  "relevance_threshold": 0.6,
  "schema_version":      "1.0"
}
```

### RAGAgentOutput — consumed from `rag-complete`

```json
{
  "request_id":           "550e8400-e29b-41d4-a716-446655440000",
  "compiled_material":    "# Study Material\n\n## Gradient Descent\nGradient descent is...",
  "extracted_pages":      [
    {"file_name": "sample.pdf", "page_number": 3, "relevance_score": 0.87,
     "status": "SUCCESS", "ocr_used": false, "errors": []}
  ],
  "total_pages_processed": 10,
  "total_pages_included":   4,
  "status":               "complete",
  "errors":               [],
  "schema_version":       "1.0"
}
```

### TeachingAgentInput — produced to `teaching`

```json
{
  "request_id":     "550e8400-e29b-41d4-a716-446655440000",
  "user_query":     "Explain gradient descent from the uploaded chapter",
  "learner_level":  "naive",
  "learning_path":  {
    "objective":    "Understand what gradient descent is and why it is used",
    "depth":        "conceptual",
    "use_analogies": true
  },
  "rag_material":   "# Study Material\n\n## Gradient Descent\n...",
  "session_context": [{"role": "user", "content": "I just started learning ML"}],
  "schema_version": "1.0"
}
```

### TeachingAgentOutput — consumed from `material-compiled`

```json
{
  "request_id":      "550e8400-e29b-41d4-a716-446655440000",
  "teaching_content": "# Gradient Descent — Beginner Guide\n\nImagine you are hiking...",
  "learner_level":   "naive",
  "sections": [
    {"title": "What is Gradient Descent?", "content": "..."},
    {"title": "Why Do We Need It?",        "content": "..."}
  ],
  "status":  "complete",
  "errors":  [],
  "schema_version": "1.0"
}
```

### QuizAgentInput — produced to `quiz`

```json
{
  "request_id":     "550e8400-e29b-41d4-a716-446655440000",
  "topic":          "Gradient Descent",
  "learner_level":  "naive",
  "num_questions":  5,
  "question_types": ["mcq", "true_false"],
  "rag_material":   "# Study Material\n...",
  "schema_version": "1.0"
}
```

### QuizAgentOutput — consumed from `quiz-complete`

```json
{
  "request_id":  "550e8400-e29b-41d4-a716-446655440000",
  "questions": [
    {
      "id": "q1", "type": "mcq",
      "question": "What does gradient descent minimize?",
      "options":  ["Loss function", "Accuracy", "Learning rate", "Batch size"],
      "answer":   "Loss function",
      "explanation": "Gradient descent iteratively reduces the loss..."
    }
  ],
  "learner_level":   "naive",
  "total_questions": 5,
  "status":          "complete",
  "errors":          [],
  "schema_version":  "1.0"
}
```

### PlannerResponse — produced to `planner-response`

```json
{
  "request_id":        "550e8400-e29b-41d4-a716-446655440000",
  "session_id":        "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id":           "usr-001",
  "user_query":        "Explain gradient descent from the uploaded chapter",
  "learner_level":     "naive",
  "learning_plan": {
    "required_agents": ["RAG_AGENT", "TEACHING_AGENT"],
    "parallel_groups": [["RAG_AGENT", "TEACHING_AGENT"]],
    "reasoning":       "Query requires document retrieval and beginner-level explanation."
  },
  "synthesized_content": "# Your Learning Session\n\n## What is Gradient Descent?\n...",
  "study_material":    "# Study Material\n\n## Gradient Descent\n...",
  "quiz":              null,
  "status":            "complete",
  "errors":            [],
  "schema_version":    "1.0"
}
```

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid `init-planner` messages result in a schema-valid `planner-response` message being produced, regardless of downstream agent outcomes.
- **SC-002**: For labeled test queries with clear level signals, learner level is correctly assessed in ≥ 90% of cases.
- **SC-003**: For ambiguous queries, a clarification question is produced on `clarify-user-level` in 100% of runs where level confidence < 0.65.
- **SC-004**: For queries requiring multiple agents, all agent Kafka produce calls occur before any consume wait, in 100% of parallel-dispatch runs.
- **SC-005**: Empty, blank, or schema-invalid agent responses are rejected and retried in 100% of cases — none reaches the synthesis step.
- **SC-006**: A new agent type can be registered by adding one `AgentRegistryEntry` with zero changes to any existing Planner source file.
- **SC-007**: All `PlannerResponse` messages follow a consistent schema structure regardless of which agents were dispatched, in 100% of runs.
- **SC-008**: End-to-end orchestration (consume `init-planner` → produce `planner-response`) completes within 60 seconds on developer hardware under standard LLM and Kafka latency.

## Assumptions

- Kafka is available as a shared message broker; broker configuration is provided via environment variables.
- The Planner Agent runs as a long-lived consumer process, not a one-shot function call.
- RAGAgentInput contract (defined in `project/schemas.py`) is already in place.
- TeachingAgentInput and QuizAgentInput contracts are defined in `project/schemas.py`; stubs are acceptable for agents not yet implemented.
- The Teaching Agent independently consumes from the `teaching` topic; the Planner only produces to it.
- LLM calls for level assessment, query rewriting, guardrails, and synthesis use the LiteLLM wrapper pattern established in the RAG Agent.
- session_context is carried across turns by the calling application and included in each `init-planner` message.
- PDF file paths in `available_files` are resolvable on the shared file system accessible by the RAG Agent.
- MIN_CONTENT_LENGTH defaults to 100 characters; configurable via environment variable.
- Agent response timeout defaults to 120 seconds per agent; configurable via environment variable.
- This spec covers only the Planner Agent module and shared Kafka contracts; individual agent implementations are covered by their own specs.
