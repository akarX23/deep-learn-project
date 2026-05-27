# Quickstart: RAG Retrieval Agent

## 1. Install dependencies

Use your project environment manager, then install required packages:

- pydantic>=2
- pymupdf
- sentence-transformers
- litellm
- langgraph
- pytest

## 2. Configure environment variables

Set model/provider values before running the agent:

- RAG_TEXT_MODEL
- RAG_TEXT_API_BASE (optional, for local vLLM such as http://localhost:8000/v1)
- RAG_TEXT_API_KEY (optional if local endpoint does not require key)
- RAG_TEXT_TEMPERATURE (optional)
- RAG_TEXT_MAX_TOKENS (optional)
- RAG_VLM_MODEL
- RAG_VLM_API_BASE (optional)
- RAG_VLM_API_KEY (optional)
- RAG_VLM_TEMPERATURE (optional)
- RAG_VLM_MAX_TOKENS (optional)

Embedding model:

- RAG_EMBEDDING_MODEL_NAME (default: all-MiniLM-L6-v2)

## 3. Prepare sample input

Use:

- rag_agent/tests/inputs/sample.pdf
- rag_agent/tests/inputs/sample_input.json

Ensure sample_input.json points to the sample PDF path available in your checkout.

## 4. Run the agent end-to-end

Example (from repository root):

```bash
python -m rag_agent.agent --input rag_agent/tests/inputs/sample_input.json
```

Expected result:

- A schema-valid RAGAgentOutput payload
- status of complete or partial
- non-empty compiled_material when at least one page is retained

## 5. Run tests

```bash
pytest rag_agent/tests/test_rag_agent.py -q
```

## 6. Verify threshold filtering behavior

Set relevance_threshold to 1.0 in sample_input.json and rerun:

- total_pages_included should be 0
- all extracted_pages statuses should be SKIPPED_IRRELEVANT

## 7. Notes

- Planner Agent and Teaching Agent runtime are not required for standalone execution.
- OCR is intentionally out of scope for this version.

## 8. Validation Snapshot

- Validated on 2026-05-27 using `sample_input.json`
- Runtime baseline: 4.53 seconds
- Observed output: `status=complete`, `total_pages_processed=6`, `total_pages_included=4`
