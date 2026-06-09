# Quickstart: RAG Retrieval Agent

## 1. Install dependencies

Install project dependencies from repository root:

```bash
pip install -r requirements.txt
```

Core runtime dependencies for this feature include:
- pydantic>=2
- pymupdf
- litellm
- langgraph
- pytest

## 2. Configure environment variables

Use one project-level `.env.local` and place RAG settings in the RAG section.

### Text model
- `RAG_TEXT_PROVIDER` (default: `hosted_vllm`)
- `RAG_TEXT_MODEL`
- `RAG_TEXT_API_BASE` (optional for local endpoints)
- `RAG_TEXT_API_KEY` (optional for unauthenticated local endpoints)
- `RAG_TEXT_TEMPERATURE` (optional)
- `RAG_TEXT_MAX_TOKENS` (optional)

### Vision model
- `RAG_VLM_PROVIDER` (default: `hosted_vllm`)
- `RAG_VLM_MODEL`
- `RAG_VLM_API_BASE` (optional)
- `RAG_VLM_API_KEY` (optional)
- `RAG_VLM_TEMPERATURE` (optional)
- `RAG_VLM_MAX_TOKENS` (optional)
- `RAG_VLM_BATCH_SIZE` (optional, default from config)

### Embedding model
- `RAG_EMBEDDING_PROVIDER` (default: `hosted_vllm`)
- `RAG_EMBEDDING_MODEL`
- `RAG_EMBEDDING_API_BASE` (optional)
- `RAG_EMBEDDING_API_KEY` (optional)
- `RAG_EMBEDDING_MAX_TOKENS` (optional)

LiteLLM routing composes each call model as `<provider>/<model>`.

## 3. Prepare sample input

Use fixture input from:
- `rag_agent/tests/inputs/sample_input.json`
- `rag_agent/tests/inputs/sample.pdf`

Verify `file_paths` in JSON point to valid files in your checkout.

## 4. Run the agent

From repository root:

```bash
python -m rag_agent.agent --input rag_agent/tests/inputs/sample_input.json
```

Expected outcome:
- Schema-valid `RAGAgentOutput`
- `status` in `{complete, partial}` for non-fatal mixed outcomes
- Non-empty `compiled_material` when at least one relevant page is retained

## 5. Run tests

```bash
pytest rag_agent/tests/test_rag_agent.py -q
```

## 6. Verify strict threshold behavior

Set `relevance_threshold` to `1.0` in sample input and run again.

Expected:
- `total_pages_included == 0`
- all page statuses are `SKIPPED_IRRELEVANT`

## 7. Operational notes

- Source PDFs are opened once per request and reused via request-scoped `fitz.Document` handles.
- `extracted_pages` contains audit metadata only; assembled text is returned only in `compiled_material`.
- OCR remains out of scope for this feature iteration.
- Ensure embedding env vars are set before running (`RAG_EMBEDDING_PROVIDER`, `RAG_EMBEDDING_MODEL`, and either `RAG_EMBEDDING_API_BASE` or `RAG_EMBEDDING_API_KEY`).

## 8. Validation snapshot

- Validated on 2026-06-08 with `rag_agent/tests/inputs/sample_input.json`
- Runtime baseline: 1.93 seconds
- Observed output: `status=complete`, `total_pages_processed=6`, `total_pages_included=5`
