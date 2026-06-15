# Feature Specification: Planner Agent Orchestrator

**Feature Branch**: `000-planner-agent`  
**Created**: 2026-06-13  
**Status**: Draft  
**Owner**: `Himanshu5@iisc.ac.in`  
**Input**: User description: "Create a planner agent which will act as an orchestrator for all agents. The orchestrator consumes init-planner events from Kafka, assigns request IDs, infers user knowledge levels, and creates workflows with RAG, Teaching, Quiz, and Eval agents based on pre-defined rules."

## Clarifications

### Session 2026-06-14

- Q: What is the required logging standard across planner flow stages? → A: Logging is required at every planner flow stage with appropriate log levels; existing logger configuration remains unchanged.
- Q: Should planner inference use RAG's LiteLLM configuration? → A: No. Planner agent must use its own LiteLLM configuration and environment variables.
- Q: What type-safety and schema-conformance constraints apply? → A: Planner code must enforce strong typing end-to-end; inbound/outbound messages must conform to `project/schemas.py`; function signatures must declare argument and return types; `Any` is disallowed except unavoidable cases.

### Session 2026-06-14 (Continued)

- Q: How should environment variables be loaded in the planner agent? → A: Use `dotenv` package to load environment variables without overriding existing variables (apply `override=False` in `load_dotenv()`); this allows local `.env.local` files to coexist with system-set variables.
- Q: Should the planner consume completion topic events and resume interrupted workflows? → A: Yes. The planner must consume `rag-complete`, `teaching-complete`, and `quiz-complete` topics, then use LangGraph's `Command(resume=...)` API to resume graph execution where it was interrupted (after dispatch nodes `run_rag`, `teach_node`, `run_quiz`); completion-driven resumption is now in scope for this phase.
- Q: How strict should boilerplate minimization be relative to logging and type-safety? → A: Minimize boilerplate only where it does not compromise observability or type-safety; every stage must log; function signatures must declare types. Trade-off favors correctness and debuggability over brevity.

### Session 2026-06-14 (Worker/Interrupt Update)

- Q: How should planner workers and Kafka consumption be structured? → A: Use a single `run_worker` function with one Kafka consumer subscribed to all required topics (`init-planner`, `rag-complete`, `teaching-complete`, `quiz-complete`).
- Q: How should messages from multiple topics be handled? → A: Branch by `message.topic`, validate payload by topic schema, then call the appropriate planner function (`run` for init events, `resume` for completion events).
- Q: What keying and graph pause/resume semantics are required? → A: For each produced event, use `request_id` as the Kafka message key. Use LangGraph `interrupt()` (not static `interrupt_after`) to pause execution and resume with `Command(resume=...)` when completion events arrive; if needed, place the interrupt in the node immediately after dispatch-producing nodes.

## User Scenarios & Testing

### User Story 1 - Consume init-planner Events and Request Assignment (Priority: P1)

A user submits a learning request through the backend, which produces an event to the `init-planner` Kafka topic. The planner agent consumes this event, assigns a unique `request_id` to track the request through the entire workflow, and stores the request context (user prompt, sid, file paths, provided user levels) for later reference.

**Why this priority**: This is the entry point for the entire orchestration pipeline. Without consuming and tracking requests, downstream agents have no context and the system cannot route work.

**Independent Test**: Deploy planner agent, produce a test event to `init-planner`, verify the planner consumes it, assigns a request_id, and stores request context in memory/cache.

**Acceptance Scenarios**:

1. **Given** a valid event in `init-planner` topic, **When** the planner agent processes it, **Then** it assigns a unique `request_id` and stores request metadata.
2. **Given** multiple events in `init-planner`, **When** processed, **Then** each receives a distinct `request_id` and contexts are isolated.
3. **Given** an event with malformed data, **When** processed, **Then** it logs the error and continues (basic exception handling, no crash).

---

### User Story 2 - Infer User Knowledge Level with Confidence Threshold (Priority: P1)

After consuming an event, the planner agent analyzes the user prompt to infer the user's knowledge level (beginner, intermediate, advanced). If the confidence score exceeds a defined threshold (FR-004), that level is finalized. If confidence is below the threshold, the agent produces a `clarify-user-level` event to Kafka and removes the request from active memory. If the init-planner event already contains a list of user levels, the planner skips inference and uses the provided levels.

**Why this priority**: Accurate knowledge level classification determines which teaching content is generated and which agents are invoked; this is foundational to personalized workflows.

**Independent Test**: Call planner with high-confidence inference prompts (e.g., "I'm an ML expert"), verify level is finalized; call with ambiguous prompts, verify clarify event is produced; provide pre-defined user levels, verify inference is skipped.

**Acceptance Scenarios**:

1. **Given** a prompt with clear knowledge indicators, **When** analyzed with confidence ≥ threshold, **Then** level is finalized (e.g., beginner).
2. **Given** an ambiguous prompt with confidence < threshold, **When** analyzed, **Then** a `clarify-user-level` event is produced and request is removed from memory.
3. **Given** an event with pre-defined `user_level` list, **When** processed, **Then** inference is skipped and provided levels are used.
4. **Given** a level inference call, **When** the LLM fails, **Then** the error is logged and clarify event is produced (basic handling).

---

### User Story 3 - Orchestrate Multi-Agent Workflow Creation (Priority: P2)

Once user level is finalized, the planner agent creates a workflow that orchestrates RAG, Teaching, Quiz, and Eval agents following pre-defined rules:
- If files are uploaded, RAG agent is always first.
- Teaching agent is called in parallel for each user level (beginner/intermediate/advanced).
- Quiz agent is called after teaching, only if the user explicitly requested a quiz in their prompt.
- Eval agent is not included in workflows initially.

The planner produces events to designated Kafka topics (e.g., `rag-request`, `teaching-request`, `quiz-request`) to trigger each agent, along with the finalized request_id, user prompt, level, and file paths.

**Why this priority**: This defines the core orchestration logic that differentiates the planner. Without this, agents cannot be coordinated and personalized workflows cannot be built.

**Independent Test**: Create a request with files and levels [beginner, advanced]; verify RAG event is produced first, then two Teaching events (one per level) are produced in parallel, and no Quiz event unless explicitly requested.

**Acceptance Scenarios**:

1. **Given** an event with file uploads, **When** workflow is created, **Then** RAG event is produced first in the sequence.
2. **Given** user levels [beginner, intermediate], **When** workflow is created, **Then** Teaching events are produced in parallel for both levels.
3. **Given** a request without quiz keywords in the prompt, **When** workflow is created, **Then** no Quiz event is produced.
4. **Given** a request containing quiz keywords, **When** workflow is created, **Then** Quiz event is produced after Teaching agents complete.
5. **Given** Eval agent, **When** workflow is created, **Then** Eval is not included in the initial workflow.

---

### User Story 4 - Workflow Status Tracking and Intermediate Output Storage (Priority: P2)

As agents complete their work, they produce completion events (e.g., `rag-complete`, `teaching-complete`, `quiz-complete`) to Kafka. A single planner worker with one multi-topic consumer handles both init and completion traffic by branching on topic name, updates an in-memory workflow state (e.g., marking RAG as done, marking specific Teaching level as done), extracts intermediate outputs (e.g., RAG-extracted materials, teaching artifacts), and uses LangGraph's `Command(resume=...)` API to resume graph execution where it was paused by `interrupt()`. When all agents in the workflow finish, the planner produces a `workflow-complete` event.

**Why this priority**: Tracking workflow progress, collecting outputs, and implementing resumption enables non-linear workflows and proper state management; this is essential for production-quality orchestration.

**Independent Test**: Submit a request that triggers RAG + Teaching (2 levels). Verify planner consumes completion events in any order, resumes graph execution at correct node, stores outputs, updates state correctly, and produces `workflow-complete` only after all agents finish.

**Acceptance Scenarios**:

1. **Given** agents complete and produce completion events, **When** events are consumed, **Then** intermediate outputs are extracted and stored by request_id.
2. **Given** a completion event arrives for a dispatched agent, **When** processed, **Then** `Command(resume=...)` is invoked to resume graph execution at the correct pause point with updated state.
3. **Given** agents finish in any order, **When** completion events are consumed, **Then** graph resumes correctly regardless of event order.
4. **Given** all agents in workflow have completed, **When** final agent completes, **Then** `workflow-complete` event is produced with request_id and collected outputs.
5. **Given** an agent fails or times out, **When** no completion event arrives, **Then** the workflow state reflects the missing agent and continues (basic handling, no rollback).

---

### Edge Cases

- What happens if the same request_id is consumed twice from `init-planner`? (Likely duplicate; handle with logging, skip or idempotent upsert.)
- What if no user level can be inferred or provided? (Produce clarify event and delete request.)
- What if Teaching agents for multiple levels produce outputs of different sizes/formats? (Store as-is; assume downstream aggregation handles reconciliation.)
- What if agents produce completion events but never finish certain levels? (Workflow state shows incomplete; request remains active indefinitely until all agents complete or timeout is added in future phase.)
- What if the planner agent crashes mid-workflow? (Request state and in-flight workflows are lost; acceptable for MVP as all state is stored in memory only. Persistence deferred to future phase.)

## Requirements

### Functional Requirements

- **FR-001**: System MUST run a single planner worker and consume required topics (`init-planner`, `rag-complete`, `teaching-complete`, `quiz-complete`) using one Kafka consumer.
- **FR-002**: System MUST assign a unique `request_id` (UUID or sequential) to each consumed init-planner event and maintain request metadata in memory during workflow execution.
- **FR-003**: System MUST infer user knowledge level (beginner, intermediate, advanced) from the user prompt using an LLM with a defined confidence threshold (FR-004).
- **FR-004**: System MUST define a configurable confidence threshold (e.g., 0.75); if inference confidence is below this threshold, produce a `clarify-user-level` event and remove the request from memory.
- **FR-005**: System MUST skip level inference if the init-planner event provides a pre-defined `user_level` list, using those levels directly.
- **FR-006**: System MUST define and apply workflow orchestration rules using rule-based logic only — no LLM call is required to decide which agents to invoke or in what order: (a) if files are uploaded, RAG is dispatched first and Teaching waits for RAG to complete before being dispatched; (b) Teaching is dispatched for each finalized learner level after RAG completes (or directly if no files); (c) Quiz is dispatched after Teaching only when keyword-based detection identifies quiz intent in the user prompt (keywords include: quiz, test, question, practice, evaluate, assess, exercise, exam, challenge); (d) Eval is not included initially.
- **FR-007**: System MUST produce events to Kafka topics (`rag-request`, `teaching-request`, `quiz-request`) with payload containing request_id, user_prompt, user_level, file_paths, and sid, and MUST set Kafka message key to `request_id` for each produced event.
- **FR-008**: System MUST consume completion events (`rag-complete`, `teaching-complete`, `quiz-complete`) from Kafka and update in-memory workflow state (request_id -> agent status mapping).
- **FR-009**: System MUST store intermediate outputs from completion events (e.g., `rag_materials`, `teaching_artifacts`) retrievable by request_id; simple storage to memory/dict is acceptable for MVP.
- **FR-010**: System MUST produce a `workflow-complete` event when all agents in a workflow have completed, including the final request_id and collected intermediate outputs.
- **FR-011**: System MUST include basic exception handling (try/except, logging) for LLM calls, Kafka producer/consumer failures; errors are logged but do not crash the agent (FR-012).
- **FR-012**: System MUST NOT include complex retry logic, transaction handling, distributed tracing, or persistence layer in the first pass; all deferred to TODO markers.
- **FR-013**: System directory structure MUST follow the rag_agent pattern: `planner_agent/` with `agent.py`, `config.py`, `llm_client.py`, `kafka.py`, `utils/`, and `tests/`.
- **FR-014**: System MUST emit logs at every major planner workflow step (consume init event, request_id assignment, inference decision, route decision, dispatch publish, completion consume, final completion publish) using appropriate severity levels (`DEBUG`/`INFO` for normal flow, `WARNING` for recoverable issues, `ERROR` for failures).
- **FR-015**: System MUST use planner-local LiteLLM configuration for all planner LLM calls (planner-specific model/base URL/key/temperature/token settings) and MUST NOT depend on rag_agent runtime config.
- **FR-016**: System MUST validate and serialize all inbound and outbound planner Kafka messages using their corresponding schemas from `project/schemas.py`.
- **FR-017**: System MUST provide explicit type annotations for planner function parameters and return values; `Any` MAY be used only in unavoidable interoperability boundaries and must be minimized.
- **FR-018**: System MUST load environment variables using `dotenv` package with `override=False` so that system-set variables are never overwritten by `.env.local` files.
- **FR-019**: System MUST consume `rag-complete`, `teaching-complete`, and `quiz-complete` completion topics and extract payloads (request_id, output artifacts) from each event.
- **FR-020**: System MUST implement LangGraph `interrupt()` to pause execution at workflow checkpoints (including the stage immediately following dispatch-producing nodes when needed) and MUST use `Command(resume=...)` to continue execution when matching completion events are received; state and intermediate outputs are updated before resumption.
- **FR-021**: System MUST branch completion/init handling by source topic name (`message.topic`), validate payloads with topic-specific schemas, and invoke the appropriate planner function (`run` or `resume`).
- **FR-022**: System MUST apply LLM-based query rewriting only when the query is classified COMPLEX by rule-based heuristics (word count < 5, multi-intent connectors, or single-term vague queries). Clear queries are forwarded unchanged with no LLM call. When rewriting is triggered, the rewritten query MUST be used in all agent dispatch payloads. On failure, the original query is used, the error is logged at WARNING level, and appended to `state["errors"]`.
- **FR-023**: System MUST NOT fail silently. Every caught exception in LLM calls, Kafka operations, and pipeline nodes MUST be: (a) logged at WARNING or ERROR level with `request_id` and the exception message; (b) appended to `state["errors"]` so failures are visible in the final `PlannerResponse.errors` field. No exception may be swallowed without both a structured log entry and an `errors` record.
- **FR-024**: System MUST use rule-based orchestration for all agent selection and workflow decisions. The only two cases where an LLM call is permitted are: (1) learner level inference — when levels are not pre-provided in the init-planner event; (2) query rewrite — when the query is classified COMPLEX by rule-based heuristics. No LLM call is permitted for agent routing, quiz intent detection, RAG/Teaching/Quiz ordering, or any other orchestration decision. The LangGraph pipeline MUST reflect this: `infer_level` (one optional LLM call for level + one optional LLM call for rewrite) → rule-based routing → `run_rag` → `await_rag` → `dispatch_teaching` → `await_teaching` → (optional) `run_quiz` → `await_quiz` → `finish`.

### Key Entities

- **Request**: request_id, user_prompt, user_level(s), file_paths, sid, created_at, status (active/clarified/completed).
- **Workflow**: request_id, assigned_agents (list), agent_status (per-agent state: pending/in-progress/completed), created_at.
- **UserLevelEnum**: Enum with values beginner, intermediate, advanced (defined in `project/schemas.py`).
- **Event Payloads**: init-planner, rag-request, teaching-request, quiz-request, clarify-user-level, rag-complete, teaching-complete, quiz-complete, workflow-complete.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Planner agent successfully consumes and assigns request_id to 100% of valid init-planner events.
- **SC-002**: User level inference completes within 2 seconds per request when LLM is available.
- **SC-003**: Workflow is created and events produced to all required agent topics within 500ms of level finalization.
- **SC-004**: Completion events are consumed and workflow state updated within 1 second of agent production.
- **SC-005**: All agents in a workflow complete without losing intermediate outputs; workflow-complete event includes all collected outputs.
- **SC-006**: Planner agent handles basic Kafka producer/consumer errors (topic unavailable, message serialization) without crashing.
- **SC-007**: Code structure and patterns follow rag_agent conventions (directory layout, module responsibilities, test organization).
- **SC-008**: All TODO markers are documented in code for deferred work (retry logic, persistence, advanced error handling, timeout strategies).
- **SC-009**: 100% of planner workflow stage transitions produce structured logs with appropriate level and `request_id` correlation.
- **SC-010**: 100% of planner LLM calls resolve configuration from planner-local settings (no rag_agent configuration imports for planner inference).
- **SC-011**: 100% of planner-produced and planner-consumed Kafka payloads are schema-validated against `project/schemas.py` in unit tests.
- **SC-012**: Planner modules pass static type checking with no unresolved `Any` usage except explicitly documented unavoidable boundaries.
- **SC-013**: Environment variables are loaded via `dotenv` with `override=False` in `planner_agent/config.py`, verified by unit tests confirming system-set variables are never overwritten.
- **SC-014**: Planner consumes all completion events and resumes workflows correctly; verified by tests confirming intermediate outputs are restored, state is consistent, and graph resumes at correct node.
- **SC-015**: Query rewrite is applied before every agent dispatch when not blocked; verified by tests confirming `rewritten_query` appears in dispatched payloads when rewriting succeeds, and original query is used (with error recorded) on LLM failure.
- **SC-016**: All caught exceptions in planner pipeline result in both a structured log entry and a `state["errors"]` entry; verified by unit tests confirming `errors` list is non-empty after simulated LLM and Kafka failures.

## Assumptions

- User knowledge level can be inferred from text analysis with a single LLM call (not multi-turn dialogue).
- Kafka topics (`init-planner`, `rag-request`, `teaching-request`, `quiz-request`, `clarify-user-level`, etc.) are pre-created by the bootstrap agent (US1 of 003-integrate-kafka-backend).
- Request context is stored in memory only; process restart loses in-flight workflows (acceptable for MVP per clarification Q3).
- Intermediate outputs from agents are simple JSON-serializable objects stored in a dict (no database).
- Quiz intent is detected using LLM-based classification (same LLM as level inference) with confidence threshold; reuses existing inference pattern.
- Basic exception handling means try/except with logging; no retry queues, circuit breakers, or exponential backoff.
- Existing logger configuration is retained; this clarification only mandates broader logging coverage and level discipline.
- Planner uses a dedicated LiteLLM configuration surface and does not reuse rag_agent configuration values.
- Type safety is enforced at implementation boundaries; message contracts are treated as strict schema boundaries.
- Request workflows remain active indefinitely without timeout; agent completion is the primary lifecycle trigger. Timeout logic deferred to future phase.
- "Eval agent" is designed but not invoked; placeholders/TODOs mark its future integration.
- Environment variables for planner configuration are loaded from `.env.local` (or system environment) using `dotenv.load_dotenv(override=False)`; this ensures local overrides do not suppress system-set variables.
- Completion event consumption and `Command(resume=...)` workflow resumption are now in-scope as part of this phase (US4); the planner will subscribe to init and completion topics via one consumer immediately on startup and route handling by topic.
- Planner pause points are implemented with LangGraph `interrupt()` semantics rather than static `interrupt_after` graph configuration.