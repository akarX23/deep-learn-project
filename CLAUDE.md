# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read
specs/000-planner-agent/plan.md
<!-- SPECKIT END -->

## Project Overview

Multi-agent AI Tutor backend (Python 3.11). The first implemented agent is the RAG Retrieval Agent (`rag_agent/`), which processes PDF files page-by-page, scores relevance via sentence embeddings, and compiles topic-focused study material in Markdown. Additional agents (Planner, Teaching) are planned but not yet implemented.

## Commands

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the RAG agent (CLI):
```bash
python -m rag_agent.agent --input rag_agent/tests/inputs/sample_input.json
```

Run all tests:
```bash
pytest
```

Run a single test file:
```bash
pytest rag_agent/tests/test_rag_agent.py -q
```

Run a single test by name:
```bash
pytest rag_agent/tests/test_rag_agent.py -q -k test_rag_agent_output_schema
```

## Architecture

### Module responsibilities

| Module | Role |
|---|---|
| `project/schemas.py` | Shared Pydantic v2 contracts (`RAGAgentInput`, `RAGAgentOutput`, `ExtractedPage`, `PageExtractionStatus`) — the inter-agent communication boundary |
| `rag_agent/agent.py` | `RAGAgent` class: builds a LangGraph `StateGraph` loop (`process_page` → conditional edge continue/end), then calls `_compile_material` after all pages finish |
| `rag_agent/tools.py` | Stateless PyMuPDF extraction functions (`get_page_count`, `extract_text_from_page`, `extract_tables_from_page`, `extract_images_from_page`) + `score_page_relevance` |
| `rag_agent/helpers.py` | Pure deterministic helpers: `cosine_similarity`, `serialize_table_to_markdown`, `assemble_page_content`, `build_compilation_context` |
| `rag_agent/llm_client.py` | Thin LiteLLM wrapper; raises `RuntimeError` when both `api_base` and `api_key` are unset (guards against accidental remote calls in dev) |
| `rag_agent/prompts.py` | Prompt templates (`IMAGE_DESCRIPTION_PROMPT`, `MATERIAL_COMPILATION_PROMPT`) |
| `rag_agent/config.py` | `LLMConfig` frozen dataclass; `get_text_llm_config()`, `get_vlm_config()`, `get_embedding_model_name()` all read from env vars |

### Data flow

```
RAGAgentInput
  → _build_page_pointers()        # one PagePointer per PDF page
  → LangGraph loop (AgentState)   # process_page node, per-page
      extract_text / extract_tables / extract_images
      → assemble_page_content()
      → score_page_relevance()    # cosine similarity via embedding model
      → keep if score ≥ relevance_threshold
  → _compile_material()           # one LLM call across all retained pages
  → RAGAgentOutput
```

### Key design constraints

- **Synchronous only** — no async, no OCR, PDF input only.
- **One LLM call per image** (VLM) + **one final compilation call** per request; no per-page text LLM calls.
- Embedding model is loaded with `local_files_only=True`; a `_FallbackEmbeddingModel` (bag-of-words dot product) activates automatically when the model is unavailable offline.
- Page extraction failures are non-fatal: errors are collected and processing continues; overall `status` becomes `"partial"` rather than raising.

## Environment Variables

The agent requires at least one of `RAG_TEXT_API_BASE` / `RAG_TEXT_API_KEY` and `RAG_VLM_API_BASE` / `RAG_VLM_API_KEY` to make real model calls. Tests monkeypatch `call_llm` directly.

| Variable | Default |
|---|---|
| `RAG_TEXT_MODEL` | `gpt-4o-mini` |
| `RAG_TEXT_API_BASE` | — |
| `RAG_TEXT_API_KEY` | — |
| `RAG_TEXT_TEMPERATURE` | `0.2` |
| `RAG_TEXT_MAX_TOKENS` | `1800` |
| `RAG_VLM_MODEL` | `gpt-4o-mini` |
| `RAG_VLM_API_BASE` | — |
| `RAG_VLM_API_KEY` | — |
| `RAG_VLM_TEMPERATURE` | `0.1` |
| `RAG_VLM_MAX_TOKENS` | `600` |
| `RAG_EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` |

## Testing Notes

- Tests live in `rag_agent/tests/` and use `pytest` (configured in `pytest.ini`).
- `sample.pdf` is a 6-page PDF fixture: page 2 has a table, page 3 has images.
- Tests that exercise the full agent pipeline monkeypatch `rag_agent.agent.call_llm` and `rag_agent.tools.call_llm` to avoid real model calls.
- The test `_MockEmbeddingModel` uses keyword matching (gradient/descent/optimizer vs. photosynthesis/chlorophyll/plant) — new tests requiring the embedding model should follow the same pattern.

## Spec Artifacts

Feature specifications, plans, data models, and task lists live under `specs/<feature-id>/`. The active feature is `specs/001-rag-retrieval-agent/`. Refer to `plan.md` in that directory for the authoritative technical context for this feature.
