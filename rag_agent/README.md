# RAG Agent

This package implements a synchronous RAG retrieval agent that processes PDF files page-by-page and returns planner-safe study material in markdown.

## Environment variables

- `RAG_TEXT_MODEL`
- `RAG_TEXT_API_BASE` (optional)
- `RAG_TEXT_API_KEY` (optional)
- `RAG_TEXT_TEMPERATURE` (optional)
- `RAG_TEXT_MAX_TOKENS` (optional)
- `RAG_VLM_MODEL`
- `RAG_VLM_API_BASE` (optional)
- `RAG_VLM_API_KEY` (optional)
- `RAG_VLM_TEMPERATURE` (optional)
- `RAG_VLM_MAX_TOKENS` (optional)
- `RAG_EMBEDDING_MODEL_NAME` (optional, default `all-MiniLM-L6-v2`)

## Run locally

```bash
python -m rag_agent.agent --input rag_agent/tests/inputs/sample_input.json
```

## Run tests

```bash
pytest rag_agent/tests/test_rag_agent.py -q
```
