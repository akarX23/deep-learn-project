# Feature Specification: Planner Agent
**Owner**: 'Himanshu5@iisc.ac.in'
**Feature Branch**: `[000-build-planner-agent]`  
**Created**: 2026-05-30  
**Status**: Draft  
**Input**: User description: "Implement the Planner Agent for a multi-agent AI Tutor application. The planner analyzes the intent of a user query and routes the request to a specialized agent (Teaching Agent, RAG Agent, Quiz & Eval Agent, etc.). Must be scalable to accommodate future agents. Follows shared input/output contracts aligned with existing agent contracts."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Route Query to Correct Specialized Agent (Priority: P1)

As the AI Tutor application entry point, I need the Planner Agent to receive a user query, classify the intent, and produce a correctly typed input payload for the appropriate downstream specialized agent so that the right agent can be invoked without manual routing logic.

**Why this priority**: This is the core function of the Planner Agent. Without accurate intent classification and routing, no other downstream agent can be reliably invoked.

**Independent Test**: Can be fully tested by submitting a variety of labeled user queries (study-topic, question-answering, quiz-request) and verifying that the routing decision identifies the correct target agent, produces a valid agent-specific input payload, and returns schema-valid PlannerOutput.

**Acceptance Scenarios**:

1. **Given** a query clearly requesting study material retrieval (e.g., "Explain gradient descent from Chapter 3"), **When** the Planner processes it, **Then** the routing decision targets RAG Agent with a valid RAGAgentInput payload and confidence score ≥ 0.7.
2. **Given** a query requesting teaching or explanation (e.g., "Teach me about backpropagation step by step"), **When** the Planner processes it, **Then** the routing decision targets Teaching Agent with a valid TeachingAgentInput payload.
3. **Given** a query requesting evaluation or quiz (e.g., "Quiz me on neural networks"), **When** the Planner processes it, **Then** the routing decision targets Quiz & Eval Agent with a valid QuizAgentInput payload.
4. **Given** a valid request, **When** processing completes, **Then** request_id, user_query, and schema_version are mirrored from input in the output.

---

### User Story 2 - Handle Ambiguous or Unrecognized Intent (Priority: P2)

As the AI Tutor application, I need the Planner Agent to respond predictably when user intent is unclear or does not map to any known agent so that the caller can surface a meaningful response rather than silently failing.

**Why this priority**: Ambiguous queries are common in natural language tutoring. The system must degrade gracefully without crashing or producing invalid routing.

**Independent Test**: Can be tested by submitting edge-case queries (vague, out-of-scope, or multi-intent queries) and verifying that the output status is `ambiguous` or `failed`, the routing decision includes top candidate agents with scores, and errors are non-empty where applicable.

**Acceptance Scenarios**:

1. **Given** a query with no clear match to any registered agent (e.g., "Hello"), **When** the Planner processes it, **Then** status is `ambiguous`, routing decision contains top candidate(s) with scores, and no downstream payload is constructed.
2. **Given** a query that partially matches multiple agents, **When** the Planner processes it, **Then** status is `ambiguous`, all candidates with confidence scores are included, and the caller can decide how to proceed.
3. **Given** a query that triggers a fatal internal error during intent classification, **When** the error is caught, **Then** status is `failed` and a non-empty errors list is returned.

---

### User Story 3 - Register and Route to New Agent Types (Priority: P3)

As a project contributor adding a new specialized agent to the AI Tutor system, I need to register the new agent in the Planner's agent registry without modifying core routing or classification logic so that the system remains scalable as the team adds future agents.

**Why this priority**: The group project will grow to include new agents. Extensibility must be designed in from the start to avoid rework.

**Independent Test**: Can be tested by adding a new stub agent entry to the agent registry and submitting a query whose intent maps to the new agent, then verifying the Planner correctly routes to the new agent type and produces the expected output status.

**Acceptance Scenarios**:

1. **Given** a new agent type is added to the agent registry with its intent keywords and input contract builder, **When** a matching query is submitted, **Then** the Planner routes to the new agent without changes to core classification code.
2. **Given** the agent registry is queried, **When** listing registered agents, **Then** all configured agent types are enumerated with their intent categories.

---

### Edge Cases

- User query is empty or contains only whitespace.
- User query is extremely long (> 2000 characters).
- Query simultaneously matches two agents with equal confidence scores.
- Agent registry contains only one registered agent.
- A registered agent's input contract builder raises an exception during payload construction.
- Query language is ambiguous (e.g., a single word like "explain" with no topic context).
- Requested file paths are embedded in the query (relevant for RAG routing) but the planner cannot validate their existence.
- Schema version in input does not match the Planner's supported version.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a PlannerInput payload containing request_id, user_query, session_context (optional), available_files (optional, for RAG routing hints), and schema_version.
- **FR-002**: The system MUST classify the intent of the user_query into one of the registered agent categories using LLM-based reasoning.
- **FR-003**: The system MUST produce a RoutingDecision containing the target agent type, confidence score, brief reasoning, and a fully constructed agent-specific input payload.
- **FR-004**: The system MUST support routing to at minimum: RAG Agent, Teaching Agent, and Quiz & Eval Agent as initial registered agents.
- **FR-005**: The system MUST implement an agent registry that allows new agent types to be added by contributing an intent description and input contract builder, without modifying core Planner routing logic.
- **FR-006**: The system MUST return a PlannerOutput containing mirrored request metadata, the routing decision, status (routed | ambiguous | failed), and an errors list.
- **FR-007**: The system MUST set status to `ambiguous` when no agent achieves confidence above the configured threshold, and include all candidates with their scores.
- **FR-008**: The system MUST set status to `failed` and populate errors when an unrecoverable internal error prevents classification or payload construction.
- **FR-009**: The system MUST mirror request_id, user_query, and schema_version from input into all output responses.
- **FR-010**: The system MUST validate PlannerInput on receipt and return a `failed` status with descriptive errors for invalid or missing required fields.
- **FR-011**: The system MUST provide standalone test inputs and automated test coverage for intent classification, routing, ambiguous handling, and registry extensibility.
- **FR-012**: The system MUST define UX consistency requirements, including stable output contract structure, consistent status semantics, and predictable error reporting across all routing outcomes.
- **FR-013**: The system MUST define measurable performance requirements for synchronous routing, including classification latency and graceful handling under concurrent routing requests.

### Key Entities

- **PlannerInput**: Request payload received by the Planner Agent. Contains request_id, user_query, session_context (optional), available_files (optional list of PDF paths for RAG hint), schema_version.
- **AgentType**: Enum of registered agent identifiers (e.g., RAG_AGENT, TEACHING_AGENT, QUIZ_EVAL_AGENT, UNKNOWN).
- **RoutingDecision**: Contains target_agent (AgentType), confidence_score (float [0,1]), reasoning (string), constructed_payload (typed dict or None), and candidate_agents (list of AgentType with scores when ambiguous).
- **PlannerOutput**: Response contract. Contains request_id, user_query, schema_version, routing_decision, status (routed | ambiguous | failed), errors (list of strings).
- **AgentRegistryEntry**: Per-agent registration record containing agent_type, intent_keywords, intent_description, and input_contract_builder (callable).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid PlannerInput requests return schema-valid PlannerOutput matching the defined contract.
- **SC-002**: For clearly-categorized test queries (pre-labeled by intent), routing accuracy achieves ≥ 90% correct agent selection.
- **SC-003**: For queries with no clear intent match, status is `ambiguous` and candidate list is non-empty in 100% of runs.
- **SC-004**: A new agent type can be registered and made routable by adding a single registry entry, with no changes to any existing Planner source file.
- **SC-005**: All PlannerOutput responses follow a consistent contract structure with identical field layout regardless of routing outcome, in 100% of runs.
- **SC-006**: Intent classification and routing for a single user query completes synchronously within 10 seconds on developer hardware under standard LLM latency.

## Assumptions

- The Planner Agent is a one-shot intent classifier and router — it does not orchestrate multi-turn agent coordination or consume downstream agent responses.
- Downstream agents (RAG, Teaching, Quiz & Eval) are invoked by the caller after receiving PlannerOutput; the Planner only constructs their input payloads.
- RAGAgentInput contract (defined in `project/schemas.py`) is already in place and the Planner will construct it for RAG-routed requests.
- TeachingAgentInput and QuizAgentInput contracts will be defined during the planning phase of those respective features; stubs are acceptable for Planner v1.
- Session context is optional and may be used as a routing hint but is not required for basic intent classification.
- Input files (available_files) are PDF paths provided as hints for RAG routing; the Planner does not validate file existence.
- The confidence threshold for routing (vs. ambiguous) defaults to 0.6 and is configurable via environment variable.
- LLM calls for intent classification use the same LiteLLM wrapper and config pattern established in the RAG Agent.
- This feature covers only the Planner Agent module; Teaching Agent, Quiz & Eval Agent, and any future agent implementations are out of scope.
- The current branch remains `master` during specification per user instruction; a feature branch will be created before implementation.
