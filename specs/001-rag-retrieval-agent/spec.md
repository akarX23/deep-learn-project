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
- Q: How should consumer-loop and agent error handling be scoped? → A: Keep only basic exception handling in the consumer loop and `agent.py`; defer extensive validation/error orchestration as explicit TODOs.

### Session 2026-06-13

- Q: Should this clarification switch branches or create a new feature directory? → A: No. Stay on the current branch and continue in feature directory `001-rag-retrieval-agent`.
- Q: How should runtime startup flow be simplified? → A: Start from `worker.py`, initialize the threaded consumer loop, and perform only a direct Kafka topic presence check at startup.
- Q: Where should Kafka connection and client creation live? → A: Keep Kafka connector initialization in `kafka.py` using environment variables directly, and create producer/consumer there.
- Q: Should handler and factory abstractions remain? → A: No. Remove handler abstraction and factory structure; consumer loop calls `agent.py` directly and publishes output via `kafka.py` functions.
- Q: Should `agent.py` publish to Kafka directly? → A: No. `agent.py` only returns processing output; the consumer loop publishes the completion event.
- Q: How should `helpers.py` be simplified? → A: Keep only environment-variable extraction helper functions; remove classes and validators, and defer advanced validation/exception behavior as TODO tasks.

### Session 2026-06-14

- Q: Should `kafka.py` Protocol stubs (`KafkaConsumerProtocol`, `KafkaProducerProtocol`, `ConsumerRecordProtocol`) be kept? → A: No. Remove all three Protocol stubs; annotate with concrete `KafkaConsumer` / `KafkaProducer` types from `kafka-python` directly. Eliminates ~35 lines of structural typing for a single concrete implementation.
- Q: Should `RAGWorker.__init__` retain injectable factory callables (`producer_factory`, `consumer_factory`, `request_processor`)? → A: No. Remove all three injectable parameters; call `create_producer`, `create_consumer`, and `process_request_event` directly inside the worker. Tests monkeypatch those module-level functions instead.
- Q: Should trivial one-line wrapper functions in `kafka.py` (`consumer_subscribe_rag`, `poll_records`, `close_consumer`, `close_producer`) be retained? → A: No. Remove those four wrappers; call `consumer.subscribe()`, `consumer.poll()`, and `.close()` at the call sites. Keep the logic-bearing functions (`create_producer`, `create_consumer`, `publish_rag_complete`, `check_required_topics`) and inline `apply_kafka_security_options` from `helpers.py` directly into `kafka.py`'s private kwargs builders.
- Q: Should `tools.py` retain `_with_optional_open` and the str-path branching that lets callers pass a file path or an open `fitz.Document`? → A: No. Remove `_with_optional_open` and all path-string support; extraction functions accept only `fitz.Document` directly. The agent always passes an open document; the str-path branch is dead code.
- Q: Should `process_consumer_batch` remain a standalone function passed as a callable into `_poll_loop`? → A: No. Remove `process_consumer_batch`; inline the poll-and-dispatch logic directly into `_poll_loop`. Eliminates the function and the `processor` parameter threading through the call chain.

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

### User Story 3 - Use Direct Consumer-to-Agent Flow Without Handler Abstraction (Priority: P3)

As a maintainer, I need the consumer loop to call the RAG agent directly and publish completion events itself, so the runtime removes unnecessary handler and factory indirection while keeping typed interfaces.

**Why this priority**: Removing intermediary abstractions makes event flow easier to reason about and reduces maintenance overhead.

**Independent Test**: Send an inbound request event and verify the consumer loop maps it directly to an `agent.py` call, receives output, and publishes `rag-complete` using `kafka.py` producer functions.

**Acceptance Scenarios**:

1. **Given** an inbound request event on `rag`, **When** the consumer loop processes it, **Then** it directly calls `agent.py` with typed inputs and no handler layer.
2. **Given** `agent.py` processing completes, **When** output is returned, **Then** the consumer loop publishes the completion payload to `rag-complete` through `kafka.py` producer helpers.
3. **Given** advanced validation and edge-case handling are out of scope for this phase, **When** maintainers inspect the flow, **Then** explicit TODO markers identify deferred validation, metrics, and exception-hardening work.

---

### Edge Cases

- Kafka is reachable at startup but metadata fetch for topics partially fails.
- Required topics are absent at startup but appear later while worker is already running.
- Consumer receives malformed event payloads while strict validation is deferred.
- Duplicate request events arrive for the same request identifier.
- RAG pipeline execution fails for one event while worker must continue processing subsequent events.
- `fitz.Document` handle is `None` or already-closed when extraction functions are called (caller responsibility; document lifecycle is managed by `agent.py`).
- Monkeypatched module-level functions in tests (`create_producer`, `create_consumer`, `process_request_event`) must be restored between test cases to avoid state leakage.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST run RAG Kafka integration as a standalone worker process and MUST NOT require an HTTP service runtime to process events.
- **FR-002**: The system MUST start and manage a dedicated background consumer loop thread for continuous Kafka polling.
- **FR-003**: The system MUST remove startup topic-creation behavior and MUST NOT perform external backend API calls for topic provisioning.
- **FR-004**: The system MUST perform a startup check against Kafka metadata to determine whether required topics exist.
- **FR-005**: If required topics are missing at startup, the system MUST log a clear actionable warning and continue starting.
- **FR-006**: The system MUST consume request events from topic `rag` and dispatch them to the existing RAG pipeline path.
- **FR-007**: The system MUST publish completion events to topic `rag-complete` after each processing attempt reaches terminal state.
- **FR-008**: The system MUST remove the request handler abstraction; the consumer loop MUST ingest Kafka events and dispatch directly to `agent.py`.
- **FR-009**: Public function interfaces in the worker, `kafka.py`, `agent.py`, and helper modules MUST use explicit typed inputs and outputs and SHOULD avoid untyped generic placeholders. Concrete `kafka-python` types (`KafkaConsumer`, `KafkaProducer`) MUST be used directly for all Kafka-related type annotations; structural Protocol stubs (`KafkaConsumerProtocol`, `KafkaProducerProtocol`, `ConsumerRecordProtocol`) MUST be removed.
- **FR-010**: The worker MUST continue processing after single-event failures and MUST log error stages without terminating the process.
- **FR-011**: The system MUST support clean shutdown by stopping the consumer loop thread and closing Kafka producer/consumer resources.
- **FR-012**: The runtime MUST remove non-functional `service.py` from active structure and rely on a simplified worker-centric module layout.
- **FR-013**: The worker startup path in `worker.py` MUST initialize the threaded consumer loop and perform a direct Kafka topic presence check before entering steady-state polling.
- **FR-014**: The `kafka.py` module MUST initialize Kafka connector settings from environment variables directly and MUST expose producer/consumer creation functions (`create_producer`, `create_consumer`), a completion-event publisher (`publish_rag_complete`), and a topic-presence checker (`check_required_topics`). Trivial one-line wrapper functions (`consumer_subscribe_rag`, `poll_records`, `close_consumer`, `close_producer`) MUST be removed; callers MUST invoke consumer and producer methods directly.
- **FR-015**: Security option application (`apply_kafka_security_options`) MUST be inlined directly into `kafka.py`'s private kwargs builder functions and MUST be removed from `helpers.py`. No other module should own Kafka client lifecycle or security-option wiring.
- **FR-016**: The `agent.py` module MUST remain Kafka-agnostic and MUST only return processing output; it MUST NOT publish events directly.
- **FR-017**: `helpers.py` MUST contain only environment-variable extraction helper functions (`get_text_llm_config`, `get_vlm_config`, `get_embedding_config`, `get_kafka_runtime_config`, and private `_read_*` helpers). Security-option application MUST be moved to `kafka.py`. All class-based abstractions and validators are out of scope and MUST be deferred as TODO tasks if needed.
- **FR-018**: The system MUST define stable event contract expectations for inbound request and outbound completion messages.
- **FR-019**: The system MUST define measurable performance and reliability expectations for poll-to-completion throughput and emission success.
- **FR-020**: The system MUST define observability requirements for lifecycle stages across startup checks, consume, process, publish, and failures.
- **FR-021**: `RAGWorker.__init__` MUST NOT accept injectable factory callables (`producer_factory`, `consumer_factory`, `request_processor`). The worker MUST call `create_producer`, `create_consumer`, and `process_request_event` directly. Test isolation MUST be achieved by monkeypatching those module-level functions rather than injecting alternatives through the constructor.
- **FR-022**: `process_consumer_batch` MUST be removed as a standalone function. Poll-and-dispatch logic MUST be inlined directly into `_poll_loop`, eliminating the processor-callable indirection and the `RequestProcessor` type alias.
- **FR-023**: Extraction functions in `tools.py` (`extract_text_from_page`, `extract_tables_from_page`, `extract_images_from_page`) MUST accept only an open `fitz.Document` object. The `_with_optional_open` helper and all path-string branching MUST be removed. The `open_pdf` utility function MAY remain as the caller-side document opener. The `_page_from_source` internal guard (`if page_number < 1`) MUST be removed; the agent guarantees 1-based page numbers from its own loop.

### Key Entities *(include if feature involves data)*

- **RAGRequestEvent**: Inbound Kafka message payload consumed from `rag`, including request correlation and retrieval inputs.
- **RAGCompletionEvent**: Outbound Kafka message payload produced to `rag-complete`, including result status and response content.
- **WorkerRuntimeState**: Process-level state tracking loop status, startup topic check outcome, and shutdown signals.
- **TopicPresenceCheckResult**: Startup check output identifying required topics, discovered topics, and missing-topic warnings.
- **RequestLifecycleLogEntry**: Structured lifecycle record with request correlation and stage metadata.
- **KafkaRuntimeGateway**: Functions in `kafka.py` responsible for env-based connector initialization and for creating/using producer and consumer objects. Annotated with concrete `KafkaConsumer` / `KafkaProducer` types; no Protocol stubs.
- ~~`KafkaConsumerProtocol` / `KafkaProducerProtocol` / `ConsumerRecordProtocol`~~: **Removed.** Structural typing stubs replaced by concrete kafka-python types (FR-009).
- ~~`RequestProcessor`~~: **Removed.** Type alias and injectable callback pattern replaced by direct function calls (FR-021, FR-022).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of worker starts attempt Kafka topic presence checks and emit a startup readiness or warning message.
- **SC-002**: 100% of valid consumed `rag` events are dispatched into the RAG pipeline path.
- **SC-003**: At least 99% of terminal processing attempts emit a corresponding `rag-complete` event.
- **SC-004**: 100% of single-event failures are logged without terminating the worker process.
- **SC-005**: Under representative load, p95 poll-to-completion latency remains within the agreed budget for this integration.
- **SC-006**: 100% of exported function boundaries in worker Kafka modules are type-annotated in implementation review.
- **SC-007**: After boilerplate reduction, the combined line count across `kafka.py`, `worker.py`, and `tools.py` MUST decrease (no new abstractions or stubs introduced to compensate for removed ones).

## Assumptions

- Topic provisioning is handled externally by infrastructure or deployment workflows.
- Kafka cluster credentials and connectivity are available at worker startup.
- Existing RAG pipeline behavior remains unchanged; this feature focuses on runtime structure and dispatch flow.
- Deferred validation/metrics TODOs are acceptable for this phase as long as they are explicitly tracked.
- Simplification and consolidation of module responsibilities are prioritized over introducing new abstraction layers in this iteration.
- Current branch and feature directory remain unchanged for this update.
