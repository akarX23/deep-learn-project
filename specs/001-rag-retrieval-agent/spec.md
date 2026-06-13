# Feature Specification: RAG Kafka Worker Simplification

**Feature Branch**: `[001-build-rag-retrieval-agent]`  
**Created**: 2026-06-12  
**Status**: Draft  
**Input**: User description: "The RAG agent should not be initialized as a FASTAPI service. Remove all code associated with FastAPI and have a separate thread running the consumer loop. Additionally, remove the topic creation logic on startup and just assume that all topics already exists. Keep a simple check at startup which connects to Kafka directly to check if topics are present in Kafka. If not, start the application but with a clear message. Remove any direct API calls to the backend and the variables associated with it.

Simplify the RAGRequestEventHandler by only focusing on ingesting Kafka events and dispatching them to the RAG pipeline. All the validation and metric calculation can be put as TODOs and implemented later. Also, each function sohuld have type safety for arguments as well as output. Avoid the use of \"any\" type wherever possible."

## Clarifications

### Session 2026-06-12

- Q: Should this update create a new branch or a new feature directory? → A: No. Stay on current branch and update current feature directory in place.
- Q: Should logging use a dedicated logger class or standard module logging? → A: Use standard `logging` module with `basicConfig(...)` and per-file `logging.getLogger(__name__)`; remove dedicated logger class.
- Q: How should the runtime/module layout be simplified? → A: Remove `service.py`; add a `utils/` directory and place helper-oriented modules there (`helpers.py`, `llm_client.py`, `prompts.py`, `tools.py`).
- Q: How should LLM and config logic be structured? → A: Simplify LLM operations to basic embedding + completion calls, defer complex validation/exception logic as TODOs, and consolidate `llm_client` + `config` responsibilities into `helpers.py`.
- Q: How should handler and agent error handling be scoped? → A: Keep only basic exception handling in request handler and `agent.py`; defer extensive validation/error orchestration as explicit TODOs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run RAG as a Kafka Worker Process (Priority: P1)

As a platform operator, I need the RAG integration to run as a standalone background worker process so event processing is decoupled from HTTP service lifecycle concerns.

**Why this priority**: This is the core architecture constraint for the feature; all other behavior depends on this runtime model.

**Independent Test**: Start the worker process and verify a dedicated background consumer loop begins polling Kafka without requiring an HTTP service runtime.

**Acceptance Scenarios**:

1. **Given** Kafka connectivity settings are present, **When** the worker starts, **Then** it initializes Kafka clients and starts a dedicated background consumer loop.
2. **Given** the worker is running, **When** no events are available, **Then** the process remains alive and continues polling.
3. **Given** a worker shutdown signal, **When** shutdown starts, **Then** the consumer loop exits and Kafka resources are closed cleanly.

---

### User Story 2 - Verify Topic Presence Without Topic Creation (Priority: P2)

As an operator, I need startup behavior to check whether required topics already exist while avoiding automatic topic creation or backend API dependencies.

**Why this priority**: Startup should be lightweight and safe in environments where topic provisioning is managed externally.

**Independent Test**: Start the worker against a Kafka cluster with missing required topics and verify startup logs a clear warning while the worker still starts.

**Acceptance Scenarios**:

1. **Given** all required topics exist, **When** startup topic check runs, **Then** startup logs topic readiness and processing continues.
2. **Given** one or more required topics are missing, **When** startup topic check runs, **Then** startup logs a clear warning listing missing topics and continues running.
3. **Given** startup succeeds, **When** configuration is loaded, **Then** no backend topic-creation endpoint is called and no backend topic API setting is required.

---

### User Story 3 - Use a Minimal Typed Event Handler (Priority: P3)

As a maintainer, I need a simplified request handler that focuses on ingesting Kafka events and dispatching to the RAG pipeline with strongly typed interfaces, while deferring advanced validation and metrics.

**Why this priority**: A narrower handler surface improves maintainability and supports iterative delivery.

**Independent Test**: Send an inbound request event and verify the handler maps it to a pipeline call and completion publication path, while deferred concerns are explicitly marked for follow-up.

**Acceptance Scenarios**:

1. **Given** an inbound request event, **When** the handler receives it, **Then** it dispatches the event to the RAG pipeline path.
2. **Given** the handler code path, **When** typed interfaces are reviewed, **Then** function inputs and outputs are explicitly typed and avoid untyped catch-all structures except where raw transport input is unavoidable.
3. **Given** advanced validation and metrics are deferred, **When** maintainers inspect handler flow, **Then** explicit TODO markers identify deferred behavior without blocking core dispatch.

---

### Edge Cases

- Kafka is reachable at startup but metadata fetch for topics partially fails.
- Required topics are absent at startup but appear later while worker is already running.
- Consumer receives malformed event payloads while strict validation is deferred.
- Duplicate request events arrive for the same request identifier.
- RAG pipeline execution fails for one event while worker must continue processing subsequent events.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST run RAG Kafka integration as a standalone worker process and MUST NOT require an HTTP service runtime to process events.
- **FR-002**: The system MUST start and manage a dedicated background consumer loop thread for continuous Kafka polling.
- **FR-003**: The system MUST remove startup topic-creation behavior and MUST NOT perform external backend API calls for topic provisioning.
- **FR-004**: The system MUST perform a startup check against Kafka metadata to determine whether required topics exist.
- **FR-005**: If required topics are missing at startup, the system MUST log a clear actionable warning and continue starting.
- **FR-006**: The system MUST consume request events from topic `rag` and dispatch them to the existing RAG pipeline path.
- **FR-007**: The system MUST publish completion events to topic `rag-complete` after each processing attempt reaches terminal state.
- **FR-008**: The request handler MUST prioritize ingestion and dispatch behavior with only basic exception handling in this iteration; advanced validation, metrics, and deeper error orchestration MUST be deferred and marked with TODOs.
- **FR-009**: Public function interfaces in the worker, Kafka gateway, and handler modules MUST use explicit typed inputs and outputs and SHOULD avoid untyped generic placeholders.
- **FR-010**: The worker MUST continue processing after single-event failures and MUST log error stages without terminating the process.
- **FR-011**: The system MUST support clean shutdown by stopping the consumer loop thread and closing Kafka producer/consumer resources.
- **FR-012**: The runtime MUST remove non-functional `service.py` from active structure and rely on a simplified worker-centric module layout.
- **FR-013**: The module structure MUST include a `utils/` directory that contains helper-oriented files, including `helpers.py`, `llm_client.py`, `prompts.py`, and `tools.py`.
- **FR-014**: LLM integration MUST be simplified to essential embedding and completion calls only; complex validation and exception handling in that path MUST be deferred as TODOs.
- **FR-015**: Configuration loading MUST be simplified to a single env-read function that returns a config object, with advanced config validation deferred as TODOs.
- **FR-016**: The design SHOULD consolidate `llm_client` and `config` responsibilities into `helpers.py` to reduce indirection, while preserving core pipeline behavior.
- **FR-017**: The `agent.py` flow MUST keep basic exception handling only in this phase, with extended exception taxonomy, retry policy, and deeper validation explicitly deferred as TODOs.
- **FR-018**: The system MUST define stable event contract expectations for inbound request and outbound completion messages.
- **FR-019**: The system MUST define measurable performance and reliability expectations for poll-to-completion throughput and emission success.
- **FR-020**: The system MUST define observability requirements for lifecycle stages across startup checks, consume, process, publish, and failures.

### Key Entities *(include if feature involves data)*

- **RAGRequestEvent**: Inbound Kafka message payload consumed from `rag`, including request correlation and retrieval inputs.
- **RAGCompletionEvent**: Outbound Kafka message payload produced to `rag-complete`, including result status and response content.
- **WorkerRuntimeState**: Process-level state tracking loop status, startup topic check outcome, and shutdown signals.
- **TopicPresenceCheckResult**: Startup check output identifying required topics, discovered topics, and missing-topic warnings.
- **RequestLifecycleLogEntry**: Structured lifecycle record with request correlation and stage metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of worker starts attempt Kafka topic presence checks and emit a startup readiness or warning message.
- **SC-002**: 100% of valid consumed `rag` events are dispatched into the RAG pipeline path.
- **SC-003**: At least 99% of terminal processing attempts emit a corresponding `rag-complete` event.
- **SC-004**: 100% of single-event failures are logged without terminating the worker process.
- **SC-005**: Under representative load, p95 poll-to-completion latency remains within the agreed budget for this integration.
- **SC-006**: 100% of exported function boundaries in worker Kafka modules are type-annotated in implementation review.

## Assumptions

- Topic provisioning is handled externally by infrastructure or deployment workflows.
- Kafka cluster credentials and connectivity are available at worker startup.
- Existing RAG pipeline behavior remains unchanged; this feature focuses on runtime structure and dispatch flow.
- Deferred validation/metrics TODOs are acceptable for this phase as long as they are explicitly tracked.
- Simplification and consolidation of module responsibilities are prioritized over introducing new abstraction layers in this iteration.
- Current branch and feature directory remain unchanged for this update.
