# Implementation Plan: RAG Kafka Worker Simplification

**Branch**: `001-build-rag-retrieval-agent` | **Date**: 2026-06-12 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/001-rag-retrieval-agent/spec.md`

## Summary

Simplify the `rag_agent/` module by: removing `service.py` and the dedicated `StructuredLogger` class, migrating all files to standard `logging.getLogger(__name__)`, adding a `utils/` directory containing helper-oriented modules (`helpers.py`, `llm_client.py`, `prompts.py`, `tools.py`), consolidating LLM + config responsibilities into `helpers.py`, reducing `agent.py` and the request handler to basic exception handling only with TODOs marking deferred behaviour, and confirming the standalone worker process runtime introduced in the prior iteration.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: kafka-python 2.0+, LiteLLM, PyMuPDF (fitz), sentence-transformers, pydantic v2  
**Storage**: N/A  
**Testing**: pytest  
**Target Platform**: Linux (local dev + server)  
**Project Type**: Background worker / CLI  
**Performance Goals**: SC-005 — p95 poll-to-completion within agreed budget; SC-003 — ≥99% terminal attempts emit `rag-complete`  
**Constraints**: No HTTP runtime dependency; simplicity over abstraction; deferred concerns must be marked with inline TODOs; no `Any` type in public interfaces where avoidable  
**Scale/Scope**: Single-worker, single-cluster; processes one event at a time per poll batch

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality Gate**: All changed files must pass `ruff check` and `ruff format --check`. No dead code, no commented-out blocks. `service.py` and `logging.py` must be deleted or emptied and removed from all imports.
- **Testing Gate**: All existing passing tests must remain green after refactor. Tests that depend on `StructuredLogger` or `logging.py` must be updated. New handler simplification should include a regression test confirming basic dispatch still works.
- **UX Consistency Gate**: N/A — background worker; no user-facing UI. Log output follows standard Python `logging` format; no emoji, no custom formatting class.
- **Performance Gate**: No new I/O paths introduced. Removal of `StructuredLogger` JSON serialization reduces per-event overhead — no regression expected. SC-005 p95 budget inherited from existing behaviour.
- **Maintainability Gate**: All deferred concerns must have explicit `# TODO:` comments. `helpers.py` docstring must note consolidated responsibilities. Non-obvious decisions (why `llm_client`/`config` merged, why `logging.py` removed) documented in `research.md`.

**Post-design re-check**: All gates pass. No added complexity. Simplification reduces surface area.

## Project Structure

### Documentation (this feature)

```text
specs/001-rag-retrieval-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── rag-agent-contract.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (touched files)

```text
rag_agent/
├── __init__.py
├── agent.py                    # Simplified — basic exception handling only, TODOs for rest
├── handlers.py                 # Simplified — basic dispatch, no StructuredLogger dependency
├── kafka.py                    # Unchanged (topic-check logic lives here)
├── worker.py                   # Simplified — remove StructuredLogger usage
├── logging.py                  # DELETE (replaced by standard logging module)
├── service.py                  # DELETE (was already a compatibility shim)
├── utils/
│   ├── __init__.py             # NEW
│   ├── helpers.py              # MOVED + MERGED (helpers + llm_client + config functions)
│   ├── llm_client.py           # MOVED from root — simplified to basic LLM/embedding calls
│   ├── prompts.py              # MOVED from root — unchanged
│   └── tools.py                # MOVED from root — unchanged
└── tests/
    ├── test_rag_agent.py
    ├── test_worker_runtime.py
    ├── test_request_event.py
    ├── test_completion_event.py
    ├── test_kafka_integration.py
    └── test_logging.py         # UPDATE — remove StructuredLogger tests; add basicConfig test
```

**Structure Decision**: Flat module layout with `utils/` subdirectory. No service layer, no custom logging class. `helpers.py` in `utils/` is the consolidated home for pure helper functions, LLM call wrappers, and config loading. All other `utils/` files are existing modules moved without structural changes.

## Data Flow

```
[Kafka topic: rag]
  → KafkaConsumer.poll()           # worker.py consumer loop thread
  → process_consumer_batch()       # worker.py
      → RAGRequestEventHandler.__call__(payload, producer)  # handlers.py
          → parse_event(payload)   → RAGRequestEvent
          → RAGAgent.run(input)    # agent.py (basic exception handling)
              → utils/tools.py     # PDF extraction, scoring
              → utils/helpers.py   # call_llm(), call_embedding(), assemble_page_content()
          → build_completion_event()
          → publish_rag_complete(producer, event)
  → [Kafka topic: rag-complete]
```
