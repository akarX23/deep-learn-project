# Implementation Plan: RAG Retrieval Agent — v2 (Clarification Update)

**Branch**: `001-build-rag-retrieval-agent` | **Date**: 2026-06-08 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/001-rag-retrieval-agent/spec.md` — updated with session 2026-06-08 clarifications (FR-019 through FR-026)

## Summary

The RAG Retrieval Agent processes multi-page PDFs, scores content relevance via sentence embeddings, and compiles focused study material in Markdown for downstream teaching agents. This v2 plan updates the architecture to incorporate five clarification decisions: (1) one-time fitz document loading per request stored on the agent instance (not in graph state), (2) per-page VLM image batching controlled by `VLM_BATCH_SIZE`, (3) a configurable image-analysis instruction prompt, (4) removal of `retained_content` from the output payload, and (5) strict grouped import organization across all modules. Infrastructure updates include a sectioned `.env.local` and a sectioned `requirements.txt`.

## Technical Context

**Language/Version**: Python 3.12.3  
**Primary Dependencies**: PyMuPDF ≥1.24 (`fitz`), sentence-transformers ≥2.7, LiteLLM ≥1.40, LangGraph ≥0.2, Pydantic v2 ≥2.7, python-dotenv ≥1.0  
**Storage**: Local filesystem (PDF input); no persistent store  
**Testing**: pytest ≥8.0; monkeypatched LLM/embedding calls; fixture PDF generated programmatically  
**Target Platform**: Linux server (local dev, CI)  
**Project Type**: CLI + importable library  
**Performance Goals**: Synchronous processing of a 5–10 page PDF in < 30 s (excluding real LLM latency)  
**Constraints**: Offline-capable embedding fallback; no OCR; single-process synchronous; no async  
**Scale/Scope**: Single-agent; multi-agent scaffolding via shared `project/schemas.py`; RAG only

## Constitution Check

*Gate evaluated before Phase 0. Re-evaluated post-design below.*

### Pre-Design Gate

| Gate | Status | Evidence |
|---|---|---|
| **Code Quality** | PASS | All modules use `ruff`-compatible style; imports grouped (FR-026); no dead code policy; new modules follow existing naming conventions |
| **Testing** | PASS | Existing 10-test suite covers extraction, scoring, schema; new behavior (batching, fitz reuse, payload removal) requires additional unit tests in `test_rag_agent.py` |
| **UX Consistency** | PASS | CLI output format unchanged (`model_dump_json`); Markdown compilation conventions preserved; `extracted_pages` audit metadata format unchanged minus `retained_content` |
| **Performance** | PASS | Eliminating repeated `fitz.open()` calls per page directly improves per-request latency; VLM batching reduces round-trips; budgets carry over from v1 |
| **Maintainability** | PASS | Non-obvious decision (fitz outside graph state) documented here and in research.md; `.env.local` and `requirements.txt` sectioning improves onboarding |

### Post-Design Re-Evaluation

| Gate | Status | Notes |
|---|---|---|
| **Code Quality** | PASS | Import grouping enforced via FR-026; `ExtractedPage` schema change is additive-removal (no `retained_content` field in output) |
| **Testing** | PASS | Five new/modified test cases cover batching, fitz reuse, and payload schema |
| **UX Consistency** | PASS | `RAGAgentOutput` contract remains stable for downstream consumers; removal of `retained_content` is a clean break on internal field |
| **Performance** | PASS | fitz document reuse eliminates N-1 redundant open/close cycles per file |
| **Maintainability** | PASS | `_open_documents()` / `_close_documents()` lifecycle methods are clearly scoped to `run()` |

## Project Structure

### Documentation (this feature)

```text
specs/001-rag-retrieval-agent/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output (updated)
├── contracts/
│   └── rag-agent-contract.md   ← Phase 1 output (updated)
└── tasks.md             ← Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
project/
├── __init__.py
└── schemas.py              ← Pydantic v2 shared contracts (ExtractedPage loses retained_content)

rag_agent/
├── __init__.py
├── agent.py                ← RAGAgent: fitz lifecycle methods, graph invoke, batched VLM dispatch
├── config.py               ← LLMConfig, get_text_llm_config(), get_vlm_config(), get_vlm_batch_size()
├── helpers.py              ← Pure deterministic utilities (unchanged)
├── llm_client.py           ← call_llm() gateway (unchanged)
├── prompts.py              ← IMAGE_DESCRIPTION_PROMPT updated for general+contextual instruction
├── tools.py                ← describe_images_with_vlm() replaces describe_image_with_vlm()
├── README.md
└── tests/
    ├── __init__.py
    ├── test_rag_agent.py   ← Updated / new tests
    └── inputs/
        ├── sample.pdf
        ├── sample_input.json
        └── README.md

.env.local                  ← NEW: sectioned env config (shared + per-agent)
requirements.txt            ← UPDATED: sectioned (shared + per-agent)
```

**Structure Decision**: Single project layout. Agent-specific code lives under `rag_agent/`; shared contracts in `project/`. No new top-level directories introduced.

## Architecture Changes (v1 → v2)

### 1. fitz Document Lifecycle

**Before**: `fitz.open(file_path)` called inside each extraction tool function (`extract_text_from_page`, `extract_tables_from_page`, `extract_images_from_page`), reopening the document on every page-level call.

**After**: `RAGAgent._open_documents(file_paths)` populates `self._open_docs: dict[str, fitz.Document]` before `graph.invoke()`. All extraction tools accept an open `fitz.Document` (or `fitz.Page`) directly. `RAGAgent._close_documents()` closes all handles after the graph completes. `AgentState` holds no fitz objects.

### 2. VLM Image Batching

**Before**: One `call_llm` call per image (sequential per-image loop).

**After**: Images on a page are chunked into batches of size `VLM_BATCH_SIZE` (default 4, read from env). Each batch is sent as a multi-image message to the VLM. `tools.describe_images_with_vlm(images, prompt, config, batch_size)` replaces `describe_image_with_vlm`.

### 3. Image Instruction Prompt

`IMAGE_DESCRIPTION_PROMPT` updated to provide a general descriptive instruction followed by user-prompt context, so the VLM understands the domain and frames its response accordingly.

### 4. ExtractedPage.retained_content Removed from Output

`retained_content` remains an internal-only field during graph processing (held in `AgentState["retained_pages"]` as assembled strings), but is never written into `ExtractedPage` objects. `ExtractedPage` schema drops the `retained_content` field entirely.

### 5. Import Grouping

All modules enforce three import blocks in order: stdlib → third-party libraries → project-local imports, separated by blank lines.

## Complexity Tracking

No constitution violations. All changes are simplifying or constraint-driven.
