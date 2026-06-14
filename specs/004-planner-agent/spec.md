# Feature Specification: Planner Agent Orchestrator

**Feature Branch**: `005-planner-agent`  
**Created**: 2026-06-13  
**Status**: Draft  
**Input**: User description: "Create a new agent which will act as an orchestrator for all agents. The orchestrator consumes init-planner events from Kafka, assigns request IDs, infers user knowledge levels, and creates workflows with RAG, Teaching, Quiz, and Eval agents based on pre-defined rules."

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

As agents complete their work, they produce completion events (e.g., `rag-complete`, `teaching-complete`, `quiz-complete`) to Kafka. The planner agent consumes these events, updates an in-memory workflow state (e.g., marking RAG as done, marking specific Teaching level as done), and saves intermediate outputs (e.g., RAG-extracted materials, teaching artifacts) for later compilation or review. When all agents in the workflow finish, the planner produces a `workflow-complete` event.

**Why this priority**: Tracking workflow progress and collecting outputs enables monitoring, debugging, and final compilation of results; this is essential for non-trivial user journeys.

**Independent Test**: Submit a request that triggers RAG + Teaching (2 levels). Verify planner consumes completion events in any order, updates workflow state correctly, stores outputs, and produces `workflow-complete` only after all agents finish.

**Acceptance Scenarios**:

1. **Given** agents finish in any order, **When** completion events are consumed, **Then** workflow state is updated independently of order.
2. **Given** all agents in workflow have completed, **When** final event is processed, **Then** `workflow-complete` event is produced with request_id and collected outputs.
3. **Given** intermediate outputs from agents, **When** stored, **Then** they are retrievable by request_id for later steps.
4. **Given** an agent fails or times out, **When** no completion event arrives, **Then** the workflow state reflects the missing agent and continues (basic handling, no rollback).

---

### Edge Cases

- What happens if the same request_id is consumed twice from `init-planner`? (Likely duplicate; handle with logging, skip or idempotent upsert.)
- What if no user level can be inferred or provided? (Produce clarify event and delete request.)
- What if Teaching agents for multiple levels produce outputs of different sizes/formats? (Store as-is; assume downstream aggregation handles reconciliation.)
- What if agents produce completion events but never finish certain levels? (Workflow state shows incomplete; request remains active indefinitely until all agents complete or timeout is added in future phase.)
- What if the planner agent crashes mid-workflow? (Request state and in-flight workflows are lost; acceptable for MVP as all state is stored in memory only. Persistence deferred to future phase.)

## Requirements

### Functional Requirements

- **FR-001**: System MUST consume events from the `init-planner` Kafka topic and extract user prompt, file paths, provided user levels (if any), and session ID (sid).
- **FR-002**: System MUST assign a unique `request_id` (UUID or sequential) to each consumed init-planner event and maintain request metadata in memory during workflow execution.
- **FR-003**: System MUST infer user knowledge level (beginner, intermediate, advanced) from the user prompt using an LLM with a defined confidence threshold (FR-004).
- **FR-004**: System MUST define a configurable confidence threshold (e.g., 0.75); if inference confidence is below this threshold, produce a `clarify-user-level` event and remove the request from memory.
- **FR-005**: System MUST skip level inference if the init-planner event provides a pre-defined `user_level` list, using those levels directly.
- **FR-006**: System MUST define and apply workflow orchestration rules: (a) if files uploaded, RAG event first; (b) Teaching events in parallel for each provided level; (c) Quiz event only if LLM-based detection identifies quiz intent in user prompt (using same LLM with confidence threshold); (d) Eval not included initially.
- **FR-007**: System MUST produce events to Kafka topics (`rag-request`, `teaching-request`, `quiz-request`) with payload containing request_id, user_prompt, user_level, file_paths, and sid.
- **FR-008**: System MUST consume completion events (`rag-complete`, `teaching-complete`, `quiz-complete`) from Kafka and update in-memory workflow state (request_id -> agent status mapping).
- **FR-009**: System MUST store intermediate outputs from completion events (e.g., `rag_materials`, `teaching_artifacts`) retrievable by request_id; simple storage to memory/dict is acceptable for MVP.
- **FR-010**: System MUST produce a `workflow-complete` event when all agents in a workflow have completed, including the final request_id and collected intermediate outputs.
- **FR-011**: System MUST include basic exception handling (try/except, logging) for LLM calls, Kafka producer/consumer failures; errors are logged but do not crash the agent (FR-012).
- **FR-012**: System MUST NOT include complex retry logic, transaction handling, distributed tracing, or persistence layer in the first pass; all deferred to TODO markers.
- **FR-013**: System directory structure MUST follow the rag_agent pattern: `planner_agent/` with `agent.py`, `config.py`, `llm_client.py`, `kafka.py`, `utils/`, and `tests/`.

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

## Assumptions

- User knowledge level can be inferred from text analysis with a single LLM call (not multi-turn dialogue).
- Kafka topics (`init-planner`, `rag-request`, `teaching-request`, `quiz-request`, `clarify-user-level`, etc.) are pre-created by the bootstrap agent (US1 of 003-integrate-kafka-backend).
- Request context is stored in memory only; process restart loses in-flight workflows (acceptable for MVP per clarification Q3).
- Intermediate outputs from agents are simple JSON-serializable objects stored in a dict (no database).
- Quiz intent is detected using LLM-based classification (same LLM as level inference) with confidence threshold; reuses existing inference pattern.
- Basic exception handling means try/except with logging; no retry queues, circuit breakers, or exponential backoff.
- Request workflows remain active indefinitely without timeout; agent completion is the primary lifecycle trigger. Timeout logic deferred to future phase.
- "Eval agent" is designed but not invoked; placeholders/TODOs mark its future integration.
