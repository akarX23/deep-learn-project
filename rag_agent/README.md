# RAG Agent

This package implements a synchronous RAG retrieval agent that processes PDF files page-by-page and returns planner-safe study material in markdown.

## Environment variables

Use the project-level `.env.local` file and keep variables under the section headers:

- `# === Shared ===`
- `# === RAG Agent ===`
- `# === Planner Agent ===`
- `# === Teaching Agent ===`

RAG variables:

- `RAG_TEXT_PROVIDER` (default `hosted_vllm`)
- `RAG_TEXT_MODEL`
- `RAG_TEXT_API_BASE` (optional)
- `RAG_TEXT_API_KEY` (optional)
- `RAG_TEXT_TEMPERATURE` (optional)
- `RAG_TEXT_MAX_TOKENS` (optional)
- `RAG_VLM_PROVIDER` (default `hosted_vllm`)
- `RAG_VLM_MODEL`
- `RAG_VLM_API_BASE` (optional)
- `RAG_VLM_API_KEY` (optional)
- `RAG_VLM_TEMPERATURE` (optional)
- `RAG_VLM_MAX_TOKENS` (optional)
- `RAG_VLM_BATCH_SIZE` (optional, default `4`)
- `RAG_EMBEDDING_PROVIDER` (default `hosted_vllm`)
- `RAG_EMBEDDING_MODEL`
- `RAG_EMBEDDING_API_BASE` (optional)
- `RAG_EMBEDDING_API_KEY` (optional)
- `RAG_EMBEDDING_MAX_TOKENS` (optional)

LiteLLM routing behavior:

- Text model id: `<RAG_TEXT_PROVIDER>/<RAG_TEXT_MODEL>`
- VLM model id: `<RAG_VLM_PROVIDER>/<RAG_VLM_MODEL>`
- Embedding model id: `<RAG_EMBEDDING_PROVIDER>/<RAG_EMBEDDING_MODEL>`

## Run locally

```bash
python -m rag_agent.agent --input rag_agent/tests/inputs/sample_input.json
```

## Run tests

```bash
pytest rag_agent/tests/test_rag_agent.py -q
```
