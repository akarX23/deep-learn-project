# Research: RAG Kafka Worker Simplification

## Decision 1: Worker-Centric Startup Flow
- Decision: `worker.py` is the only startup entry point and owns threaded loop initialization plus startup topic presence check.
- Rationale: Keeps runtime orchestration explicit and removes service-layer indirection.
- Alternatives considered: FastAPI service lifecycle (out of scope), extra orchestration layer (unnecessary abstraction).

## Decision 2: `kafka.py` as the Kafka Ownership Boundary
- Decision: Keep Kafka connector initialization, producer/consumer creation, and consume/produce helper functions only in `kafka.py`.
- Rationale: Single ownership for Kafka lifecycle avoids scattered client logic across modules.
- Alternatives considered: Producer/consumer ownership in worker/agent modules (duplicates responsibilities).

## Decision 3: Direct Consumer-to-Agent Dispatch
- Decision: Consumer loop calls `agent.py` directly with typed inputs and receives typed output; no handler abstraction in primary flow.
- Rationale: Removes indirection and makes poll -> process -> publish path easier to follow and maintain.
- Alternatives considered: Keep handler abstraction/factory pattern (explicitly rejected in clarifications).

## Decision 4: Kafka-Agnostic Agent
- Decision: `agent.py` only returns processing output and never publishes to Kafka.
- Rationale: Clean separation between business processing and transport behavior.
- Alternatives considered: Agent-owned publish path (couples processing with transport).

## Decision 5: Simplified `helpers.py`
- Decision: Keep `helpers.py` limited to environment-value extraction helpers; no classes and no validators.
- Rationale: Matches simplification constraints and reduces unnecessary abstraction surface.
- Alternatives considered: Config classes/validation layers in this phase (deferred).

## Decision 6: Deferred Hardening as TODO Scope
- Decision: Advanced validation, edge-case handling, and deep exception taxonomy remain deferred with explicit TODO markers.
- Rationale: Current phase prioritizes core flow simplification and type-safe boundaries.
- Alternatives considered: Full hardening now (scope expansion beyond clarified requirement).

## Decision 7: Use Concrete Kafka Types, Remove Protocol Stubs
- Decision: Remove `KafkaConsumerProtocol`, `KafkaProducerProtocol`, and `ConsumerRecordProtocol` from `kafka.py`; annotate public function boundaries with concrete kafka-python types.
- Rationale: Worker runtime has one concrete transport implementation; structural stubs add boilerplate with no runtime value.
- Alternatives considered: Keep Protocol-based typing for flexibility (rejected due to unnecessary abstraction in current scope).

## Decision 8: Simplify `RAGWorker` Constructor Surface
- Decision: Remove injectable constructor callables (`producer_factory`, `consumer_factory`, `request_processor`) from `RAGWorker`; call module-level functions directly.
- Rationale: Direct flow improves readability and keeps lifecycle orchestration straightforward.
- Alternatives considered: Keep injection for testability (rejected; tests can monkeypatch module-level functions).

## Decision 9: Keep Kafka Ownership, Remove Trivial Wrappers
- Decision: Retain logic-bearing Kafka functions (`create_producer`, `create_consumer`, `publish_rag_complete`, `check_required_topics`) and remove trivial one-line wrappers (`consumer_subscribe_rag`, `poll_records`, `close_consumer`, `close_producer`).
- Rationale: Preserves clear transport ownership while reducing no-op indirection.
- Alternatives considered: Keep all wrappers for naming consistency (rejected; method calls are already explicit).

## Decision 10: Document-Only Extraction APIs in `tools.py`
- Decision: Remove `_with_optional_open` and path-string branching; extraction functions accept only open `fitz.Document` values.
- Rationale: Agent flow already opens documents upfront; path-or-document polymorphism is unused boilerplate.
- Alternatives considered: Keep dual input support (rejected; dead path adds complexity and extra validation code).

## Decision 11: Inline Poll-and-Dispatch in `_poll_loop`
- Decision: Remove standalone `process_consumer_batch`; place poll-and-dispatch logic directly in `_poll_loop`.
- Rationale: Reduces call chaining and makes runtime behavior easier to read.
- Alternatives considered: Keep helper function for reuse (rejected; no second caller exists).

## Deferred TODO Scope
- Payload semantic validation beyond baseline schema checks.
- Retry and backoff policy tuning for consume/process/publish failures.
- Extended exception classes for transport and processing stages.
- Additional metrics instrumentation and throughput counters.
