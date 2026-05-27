# Implementation Plan: RAG Retrieval Agent

**Branch**: `001-build-rag-retrieval-agent` | **Date**: 2026-05-27 | **Spec**: `/specs/001-rag-retrieval-agent/spec.md`
**Input**: Feature specification from `/specs/001-rag-retrieval-agent/spec.md`

## Summary

Implement a synchronous RAG Retrieval Agent that reads uploaded PDF files page-by-page,
extracts text/tables/images using PyMuPDF, scores assembled page content for relevance
using sentence-transformers, retains relevant pages, and returns a single compiled Markdown
study document plus page-level audit metadata in a schema-safe output contract.

The agent runtime uses LangGraph for the reasoning loop orchestration and LiteLLM as the
single interface for all text/image model calls. LLM/VLM connection values are sourced
from environment variables through centralized configuration.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: pydantic v2, PyMuPDF, sentence-transformers, LiteLLM, LangGraph  
**Storage**: N/A (in-memory processing; file-system PDF reads only)  
**Testing**: pytest  
**Target Platform**: Linux runtime (local dev and container-ready execution)  
**Project Type**: Agent module/library within a multi-agent backend  
**Performance Goals**: Process a representative 5-10 page PDF in <=45 seconds on developer hardware; single final compilation call per request  
**Constraints**: Synchronous execution only, no OCR in v1, PDF-only input, Markdown-only output, environment-variable based LLM configuration  
**Scale/Scope**: Single request processes multiple PDFs, expected default range up to 10 PDFs and up to 200 total pages per request

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate Review (Pre-Research)

- Code Quality Gate: PASS. Responsibility boundaries are explicit by module
  (`project/schemas.py`, `rag_agent/agent.py`, `rag_agent/tools.py`,
  `rag_agent/helpers.py`, `rag_agent/llm_client.py`, `rag_agent/prompts.py`,
  `rag_agent/config.py`).
- Testing Gate: PASS. Planned tests cover unit behavior, tool extraction, scoring,
  schema validation, partial failure, and threshold filtering.
- UX Consistency Gate: PASS. Output format constrained to coherent Markdown with stable
  sectioning and preserved retained content.
- Performance Gate: PASS. Budgets and synchronous constraints are defined; extraction
  remains one-page-at-a-time with bounded LLM calls.
- Maintainability Gate: PASS. Config and prompting are centralized; pure helper functions
  isolate deterministic behavior from model calls.

### Post-Design Gate Review (After Phase 1 Artifacts)

- Code Quality Gate: PASS. Data model and contracts are explicit; no cross-module
  ambiguity remains.
- Testing Gate: PASS. quickstart includes full-run and targeted test instructions.
- UX Consistency Gate: PASS. Contract preserves predictable compiled_material structure.
- Performance Gate: PASS. Research decisions cap call count and define fallback behavior.
- Maintainability Gate: PASS. Environment-driven model configuration eliminates hard-coded
  provider coupling.

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
├── tools.py
├── helpers.py
├── llm_client.py
├── prompts.py
├── config.py
└── tests/
    ├── inputs/
    │   ├── sample.pdf
    │   └── sample_input.json
    └── test_rag_agent.py
```

**Structure Decision**: Single Python agent module with shared schemas at repository
root, keeping domain boundaries explicit while minimizing framework overhead.

## Complexity Tracking

No constitution violations identified. Complexity remains justified by requirements for
non-deterministic reasoning orchestration (LangGraph) and multimodal model support.
