# Implementation Plan: RAG Retrieval Agent

**Branch**: `[001-build-rag-retrieval-agent]` | **Date**: 2026-06-08 | **Spec**: `/specs/001-rag-retrieval-agent/spec.md`
**Input**: Feature specification from `/specs/001-rag-retrieval-agent/spec.md`

## Summary

Implement and harden the RAG Retrieval Agent pipeline for synchronous, page-level PDF extraction and relevance filtering, returning a schema-safe audit trail plus one compiled Markdown study artifact. The design locks in one-time per-request PDF handle reuse (`fitz.Document`), per-page VLM batching, remote LiteLLM-based embedding, and modality-specific provider environment keys (`RAG_TEXT_PROVIDER`, `RAG_VLM_PROVIDER`, `RAG_EMBEDDING_PROVIDER`) that default to `hosted_vllm` and are composed with model names as `<provider>/<model>`.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: pydantic v2, pymupdf (fitz), litellm, langgraph, pytest  
**Storage**: N/A (filesystem PDFs + in-memory state + environment-variable configuration)  
**Testing**: pytest with unit and integration-style pipeline tests, monkeypatched LiteLLM calls  
**Target Platform**: Linux local/dev and CI Python runtime  
**Project Type**: Backend agent module with CLI entrypoint  
**Performance Goals**: Representative 5-10 page PDF processed synchronously in acceptable local runtime, with graceful continuation on page-level failures  
**Constraints**: Synchronous processing only, no OCR requirement, one final compilation call, VLM batching constrained by `VLM_BATCH_SIZE`, non-serializable document handles kept outside LangGraph state  
**Scale/Scope**: Planner-to-RAG contract for single request processing of one to several PDFs per invocation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Pre-Phase 0 Gate Review**

- Code Quality Gate: PASS. Import grouping, clear module boundaries (`config`, `llm_client`, `tools`, `helpers`, `agent`), and explicit typing for `fitz.Document` are defined.
- Testing Gate: PASS. Existing pytest suite covers extraction/scoring/output semantics; plan extends coverage for provider-env composition and embedding configuration behavior.
- UX Consistency Gate: PASS. Markdown output consistency remains explicitly required with deterministic sectioning expectations for compiled material.
- Performance Gate: PASS. Synchronous runtime objective retained; one-time PDF open and per-page VLM batching reduce avoidable overhead.
- Maintainability Gate: PASS. Non-obvious behaviors (provider composition, runtime-only document lifecycle) documented in plan/research/data-model/contracts.

## Phase 0: Research

Research was consolidated in `/specs/001-rag-retrieval-agent/research.md` with all prior clarifications resolved, including:

- Remote embedding as primary path through LiteLLM.
- Separate provider keys for text, VLM, and embedding.
- Provider default value set to `hosted_vllm`.
- Provider/model composition strategy for LiteLLM calls.

No unresolved `NEEDS CLARIFICATION` items remain.

## Phase 1: Design and Contracts

Phase 1 artifacts updated:

- `/specs/001-rag-retrieval-agent/data-model.md`
- `/specs/001-rag-retrieval-agent/contracts/rag-agent-contract.md`
- `/specs/001-rag-retrieval-agent/quickstart.md`

Design additions include a configuration sub-model for modality-specific provider/model/API settings and explicit defaults.

Agent context update completed by ensuring `.github/copilot-instructions.md` points to:

- `specs/001-rag-retrieval-agent/plan.md`

## Post-Design Constitution Re-Check

- Code Quality Gate: PASS. Design docs enforce typed configuration, stable interfaces, and focused module responsibilities.
- Testing Gate: PASS. Contract and quickstart specify tests for schema validity, threshold behavior, partial failures, and provider-env wiring.
- UX Consistency Gate: PASS. Output contract preserves single compiled Markdown artifact with stable semantics.
- Performance Gate: PASS. Reuse of open document handles and bounded batching remain explicit and testable.
- Maintainability Gate: PASS. Configuration behavior and assumptions documented across artifacts; no constitution violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-rag-retrieval-agent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── rag-agent-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
project/
└── schemas.py

rag_agent/
├── agent.py
├── config.py
├── helpers.py
├── llm_client.py
├── prompts.py
├── tools.py
└── tests/
    ├── test_rag_agent.py
    └── inputs/
        ├── sample_input.json
        └── sample.pdf
```

**Structure Decision**: Use the existing single backend Python project layout, with feature documentation under `specs/001-rag-retrieval-agent/` and implementation constrained to `rag_agent/` plus shared contracts in `project/schemas.py`.

## Complexity Tracking

No constitution violations requiring exception tracking.
