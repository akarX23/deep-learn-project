# Research: RAG Kafka Worker Simplification

## Decision 1: Worker Runtime Model
- Decision: Run Kafka integration as a standalone worker process with a dedicated consumer thread instead of a FastAPI lifecycle host.
- Rationale: Aligns directly with scope constraints, reduces moving parts, and avoids HTTP runtime coupling for background event processing.
- Alternatives considered: Keep FastAPI lifecycle orchestration (violates new requirements), use synchronous blocking loop on main thread (harder graceful shutdown and control).

## Decision 2: Startup Topic Presence Check
- Decision: Replace topic-creation startup flow with direct Kafka metadata checks for required topics and log warnings if missing.
- Rationale: Supports externally managed topic provisioning while preserving operator visibility at startup.
- Alternatives considered: Auto-create topics on startup (explicitly out of scope), fail hard on missing topics (contradicts continue-with-warning requirement).

## Decision 3: Remove Backend Topic API Dependency
- Decision: Eliminate direct backend topic API calls and remove associated runtime variables from worker startup contract.
- Rationale: Removes cross-service startup dependency and simplifies configuration surface.
- Alternatives considered: Keep optional backend bootstrap call (unnecessary coupling), keep variable but unused (configuration ambiguity).

## Decision 4: Kafka Gateway Responsibilities
- Decision: Keep Kafka transport concerns in `rag_agent/kafka.py` and add typed helper functions for metadata checks, polling, and publish flows.
- Rationale: Preserves a single integration boundary and keeps worker orchestration code concise.
- Alternatives considered: Spread Kafka client operations across worker and handler modules (reduced maintainability).

## Decision 5: Simplified Request Handler Scope
- Decision: Keep `RAGRequestEventHandler` focused on ingesting events and dispatching to `RAGAgent`, with advanced validation and metrics marked as TODO for later.
- Rationale: Delivers core behavior quickly while making deferred concerns explicit and traceable.
- Alternatives considered: Implement full validation/metrics now (larger scope than requested), remove TODO markers (loses clarity on deferred work).

## Decision 6: Type Safety Emphasis
- Decision: Use explicit type annotations for public function inputs/outputs in worker, Kafka, and handler modules, avoiding untyped generic placeholders wherever practical.
- Rationale: Improves reviewability and reduces runtime ambiguity in event-processing boundaries.
- Alternatives considered: Preserve broad untyped signatures (faster short-term but less maintainable).

## Decision 7: Failure Semantics
- Decision: Keep per-event failures non-fatal; log stage-scoped errors and continue consumer loop operation.
- Rationale: Matches resilience requirements and avoids worker downtime from isolated bad events.
- Alternatives considered: Fail-fast on handler exceptions (poor availability), silent retries without logs (weak observability).

## Decision 8: Logging Strategy
- Decision: Maintain structured lifecycle logging with startup check stages and request processing stages (`consumed`, `processing_started`, `processing_completed`, `publish_completed`, `error`).
- Rationale: Supports operator diagnostics while fitting simplified handler scope.
- Alternatives considered: Freeform logs only (harder filtering/analysis), no startup-stage logs (poor readiness visibility).

## Decision 9: Scope Guardrail
- Decision: Continue excluding planner-side logic; only consume planner-produced events and emit RAG completion events.
- Rationale: Keeps this feature bounded to RAG runtime behavior.
- Alternatives considered: planner-side fallback behavior inside worker (scope violation).

## Decision 10: Remove Dedicated `StructuredLogger` Class

- **Decision**: Delete `rag_agent/logging.py` and `StructuredLogger`. Replace all usages with `import logging; logger = logging.getLogger(__name__)` in each module.
- **Rationale**: `StructuredLogger` wraps the standard library without adding behaviour not already provided by `logging.basicConfig`. It couples imports to a custom class, adds test surface area, and contradicts the constitution's simplicity mandate (Principle V). Per-module `__name__` loggers produce equivalent output with no extra code.
- **Alternatives considered**: Keep `StructuredLogger` as a thin wrapper (indirection with no benefit); migrate to `structlog` (new dependency, over-engineered for current scope).

## Decision 11: Create `utils/` Directory and Move Helper-Oriented Modules

- **Decision**: Add `rag_agent/utils/` containing `helpers.py`, `llm_client.py`, `prompts.py`, and `tools.py`, moved from the module root. Remove from root.
- **Rationale**: These are support utilities, not entry points. Separating them into `utils/` makes the module root scannable: entry-points (`worker.py`, `agent.py`, `handlers.py`) vs. utilities. Satisfies FR-013.
- **Alternatives considered**: Flatten everything at root (too many top-level files); sub-packages per concern (over-structured).

## Decision 12: Consolidate `config` and `llm_client` into `helpers.py`

- **Decision**: Move `LLMConfig`, `EmbeddingConfig`, all `get_*_config()` accessors from `config.py`, and `call_llm()`/`call_embedding()` from `llm_client.py` into `utils/helpers.py`. Delete standalone `config.py` and `llm_client.py`.
- **Rationale**: Config objects are only ever consumed alongside LLM/embedding call sites — they have no separate consumer. Maintaining three files for one concern (LLM invocation + config) violates Principle V. Satisfies FR-016.
- **Alternatives considered**: Keep `config.py` separate (import indirection with no benefit); create `llm.py` (renames without reducing surface).

## Decision 13: Simplify LLM Call Wrappers to Basic Calls

- **Decision**: After merging into `utils/helpers.py`, `call_llm()` and `call_embedding()` retain only the essential litellm call body. Credential guards, import-error guards, and response-format checks are replaced with `# TODO:` markers.
- **Rationale**: Current guards duplicate responsibility that belongs in config loading and are mixed with invocation logic. Removing them from call functions simplifies the critical path per FR-014.
- **Alternatives considered**: Keep guards in call functions (duplicates responsibility); move guards to config loader now (adds scope beyond this iteration).

## Decision 14: Delete `service.py`

- **Decision**: Delete `rag_agent/service.py`. It is a compatibility shim (`from rag_agent.worker import ...`) with no unique logic and no direct test callers.
- **Rationale**: Dead re-export modules contradict FR-012 and Principle V's "remove obsolete code paths" requirement.
- **Alternatives considered**: Keep as public API alias (no known callers; creates confusion).

## Decision 15: Scope Basic Exception Handling in `agent.py` and `handlers.py`

- **Decision**: Retain one broad `except Exception` guard per top-level entry (`RAGAgent.run()`, `RAGRequestEventHandler.__call__()`). Remove inner per-step try/except blocks. Mark each removed guard `# TODO: Add specific exception handling for <concern>`.
- **Rationale**: Per FR-008 and FR-017, this phase focuses on core dispatch flow. Inner exception granularity adds code surface without changing observable behaviour for the current test suite.
- **Alternatives considered**: Remove all exception handling (breaks SC-004); keep all current guards (contradicts simplification mandate).

## Implementation Evidence
- Replaced FastAPI service lifecycle with standalone worker runtime in `rag_agent/worker.py`.
- Removed backend topic API startup dependency from config and environment templates.
- Added Kafka topic presence metadata checks that warn-and-continue on missing topics.
- Added structured startup-stage logging (`startup_topic_check`) and kept request lifecycle stages.
- Added worker runtime test coverage for lifecycle, idle loop continuity, startup topic checks, and non-fatal per-event failures.
- Added typed handler contract and TODO-marker tests for deferred validation/metrics scope.

## Deferred TODO Scope
- Advanced semantic/event validation in `RAGRequestEventHandler.parse_event`.
- Metrics instrumentation (timing/throughput counters) in `RAGRequestEventHandler.process_request`.
- Full local end-to-end quickstart validation against a running Kafka stack remains environment-dependent.

## Deferred TODO Scope (Updated — Simplification Phase)

- Credential validation guards in `call_llm()` / `call_embedding()`.
- Response-format validation in LLM call wrappers.
- Advanced config validation beyond env-read in `get_kafka_config()` / `get_text_llm_config()` etc.
- Inner per-step exception handling in `RAGAgent.run()` page-processing loop.
- Inner exception handling in `RAGRequestEventHandler.__call__()` beyond top-level guard.
- `StructuredLogger`-style JSON-serialized lifecycle entries (superseded by plain logger calls).
