# Feature Specification: RAG Kafka Event Integration

**Feature Branch**: `[001-build-rag-retrieval-agent]`  
**Created**: 2026-06-11  
**Status**: Draft  
**Input**: User description: "I want the rag_agent to be able to communicate with Kafka. When the planner agent decides that RAG needs to be called, it will produce an event to a topic `rag` containing the `session_ctx` (object), user request and the `file_paths` properties. The RAG agent will subscribe to this topic and consume this event. On receiving the user request and file paths, the RAG agent will initiate the RAG pipeline to extract details from each page using the RAGAgent class. The RAG agent will then produce an event to a topic called `rag-complete` and pass the `session_ctx`, `user_prompt` and `compiled_material` along with other metadata to Kafka. The progress should be logged wherever necessary to track the flow of the request. Stay in the current branch. Use the `specs/001-rag-retrieval-agent` folder to update the spec and make this folder the active spec directory for this feature integration.""

## Clarifications

### Session 2026-06-11

- Q: Which specification folder should be used for this integration feature? → A: Reuse `specs/001-rag-retrieval-agent` and make it the active feature directory.
- Q: Which branch should be used for this specification update? → A: Stay on the current branch (`001-build-rag-retrieval-agent`) and do not create/switch branches.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consume RAG Requests From Kafka (Priority: P1)

As the planner-to-RAG integration flow, I need the RAG agent to consume events from topic `rag` and trigger retrieval processing so RAG can run automatically when requested.

**Why this priority**: Without reliable request consumption, the integration cannot start and no downstream completion event can be produced.

**Independent Test**: Publish a valid request event to topic `rag` and verify the RAG pipeline is invoked once with matching request payload values.

**Acceptance Scenarios**:

1. **Given** a valid event on topic `rag` containing `session_ctx`, `user_request`, and `file_paths`, **When** the RAG consumer receives the event, **Then** the agent starts one RAG pipeline execution using those values.
2. **Given** an event on topic `rag` with missing required fields, **When** the event is consumed, **Then** processing is not executed and an error outcome is logged with clear reason.
3. **Given** an event with valid structure but unreadable file paths, **When** pipeline processing runs, **Then** request handling completes with failure metadata rather than crashing the consumer process.

---

### User Story 2 - Publish RAG Completion Events (Priority: P2)

As downstream agents that depend on retrieval output, I need the RAG agent to publish completion events to topic `rag-complete` with compiled results and context so orchestrated flows can continue.

**Why this priority**: Downstream orchestration requires a stable completion event contract to continue planning and teaching steps.

**Independent Test**: Trigger one valid `rag` request event and verify one `rag-complete` event is published containing required fields and retrieval output.

**Acceptance Scenarios**:

1. **Given** successful retrieval processing, **When** the run completes, **Then** the agent publishes one event on `rag-complete` containing `session_ctx`, `user_prompt`, `compiled_material`, and request metadata.
2. **Given** retrieval processing that finishes with partial or failed output, **When** completion is emitted, **Then** the event still includes status and error metadata needed for downstream handling.
3. **Given** multiple independent requests, **When** completion events are published, **Then** each completion event can be matched to its originating request context.

---

### User Story 3 - Track End-to-End Progress Logs (Priority: P3)

As an operator, I need progress logs at key integration stages so I can trace each request lifecycle across consume, process, and publish steps.

**Why this priority**: Operational visibility is necessary to diagnose event flow issues and monitor throughput/reliability.

**Independent Test**: Submit a request and verify logs include consistent progress milestones for consume, processing start/end, and completion publish with correlation metadata.

**Acceptance Scenarios**:

1. **Given** a valid request event, **When** the lifecycle progresses, **Then** logs are recorded for event consumed, pipeline started, pipeline completed, and completion event published.
2. **Given** processing or publishing failures, **When** the error occurs, **Then** logs include failure stage, request correlation details, and actionable error message.

---

### Edge Cases

- Incoming `rag` event payload has malformed JSON or incompatible schema shape.
- Incoming `rag` event omits `file_paths` or provides an empty list.
- `session_ctx` is present but not serializable in completion event form.
- RAG extraction succeeds for some files but fails for others in the same request.
- Kafka publish to `rag-complete` fails after RAG processing has finished.
- Duplicate `rag` events are delivered for the same request context.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST subscribe to Kafka topic `rag` to receive RAG request events.
- **FR-002**: The system MUST validate incoming `rag` events for required fields: `session_ctx`, `user_request`, and `file_paths`.
- **FR-003**: The system MUST invoke the existing RAG pipeline using the RAGAgent class when a valid `rag` event is consumed.
- **FR-004**: The system MUST map incoming `user_request` to the RAG user prompt used for retrieval processing.
- **FR-005**: The system MUST publish a completion event to Kafka topic `rag-complete` after processing attempts finish.
- **FR-006**: The completion event MUST include `session_ctx`, `user_prompt`, `compiled_material`, processing status, and request correlation metadata.
- **FR-007**: The completion event MUST include error metadata when processing completes with partial or failed outcomes.
- **FR-008**: The system MUST preserve request-to-completion traceability so each completion event can be matched to its triggering request.
- **FR-009**: The system MUST record progress logs for key lifecycle stages: event consume, validation outcome, pipeline start, pipeline end, and completion publish.
- **FR-010**: The system MUST log errors with stage context and correlation metadata for consume, processing, and publish failures.
- **FR-011**: The system MUST continue running after individual message failures and avoid terminating the consumer service on single-request errors.
- **FR-012**: The system MUST define consistent event payload contracts for incoming `rag` and outgoing `rag-complete` messages.
- **FR-013**: The system MUST define measurable performance and reliability expectations for consume-to-complete processing latency and successful completion emission.
- **FR-014**: The system MUST define observability consistency requirements so log records use predictable stage naming and correlation fields across the integration flow.

### Key Entities *(include if feature involves data)*

- **RAGRequestEvent**: Incoming message from topic `rag` containing `session_ctx`, `user_request`, `file_paths`, and request correlation metadata.
- **RAGCompletionEvent**: Outgoing message to topic `rag-complete` containing `session_ctx`, `user_prompt`, `compiled_material`, status, errors, and completion metadata.
- **SessionContext**: Opaque object passed through unchanged for downstream orchestration continuity.
- **RAGProcessingResult**: Internal result object summarizing retrieval output, status (`complete`, `partial`, `failed`), timing, and error details.
- **RequestLifecycleLogEntry**: Structured log record capturing lifecycle stage, correlation metadata, timestamp, and message.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid events published to topic `rag` are consumed and acknowledged by the RAG integration flow.
- **SC-002**: At least 99% of valid consumed requests emit exactly one corresponding completion event on topic `rag-complete`.
- **SC-003**: 100% of completion events include required fields `session_ctx`, `user_prompt`, `compiled_material` (or explicit empty value), status, and correlation metadata.
- **SC-004**: 100% of malformed or invalid request events are rejected with logged validation failure details without crashing the consumer process.
- **SC-005**: For representative request loads, p95 consume-to-complete latency remains within the agreed performance budget for this integration.
- **SC-006**: 100% of request lifecycles have logs covering consume, process start/end, and publish outcome with correlation identifiers.

## Assumptions

- Planner and RAG components share Kafka connectivity and can access topics `rag` and `rag-complete` in the target environment.
- `session_ctx` is passed through as an opaque object and is not transformed by the RAG integration layer beyond serialization requirements.
- Existing RAGAgent retrieval behavior remains the source of compiled output; this feature adds event-driven invocation and completion publishing.
- Message ordering guarantees are handled by Kafka/topic configuration and are outside this feature’s scope.
- Security, authentication, and topic ACL provisioning for Kafka are managed by environment/platform configuration outside this feature.
