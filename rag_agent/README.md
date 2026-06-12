# RAG Agent

This package implements a synchronous RAG retrieval agent that processes PDF files page-by-page and returns planner-safe study material in markdown.

It also includes a Kafka-driven worker runtime that consumes request events from `rag`, executes the existing `RAGAgent` pipeline, and publishes completion events to `rag-complete`.

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

Kafka runtime variables:

- `BACKEND_KAFKA_BOOTSTRAP_SERVERS` (required)
- `BACKEND_KAFKA_CLIENT_ID` (optional, defaults to `rag-service`)
- `BACKEND_KAFKA_SECURITY_PROTOCOL` (optional)
- `BACKEND_KAFKA_SASL_MECHANISM` (optional)
- `BACKEND_KAFKA_SASL_USERNAME` (optional)
- `BACKEND_KAFKA_SASL_PASSWORD` (optional)
- `BACKEND_KAFKA_SSL_CAFILE` (optional)
- `BACKEND_KAFKA_POLL_TIMEOUT_MS` (optional, default `1000`)

Startup behavior assumes required topics already exist and performs a Kafka metadata presence check with warning-only logging when topics are missing.

LiteLLM routing behavior:

- Text model id: `<RAG_TEXT_PROVIDER>/<RAG_TEXT_MODEL>`
- VLM model id: `<RAG_VLM_PROVIDER>/<RAG_VLM_MODEL>`
- Embedding model id: `<RAG_EMBEDDING_PROVIDER>/<RAG_EMBEDDING_MODEL>`

## Run locally

```bash
python -m rag_agent.agent --input rag_agent/tests/inputs/sample_input.json
```

## Run Kafka worker locally

```bash
python -m rag_agent.worker
```

Startup flow:

- Loads Kafka settings from `BACKEND_KAFKA*`
- Checks Kafka metadata for required topics (`rag`, `rag-complete`)
- Starts Kafka consumer polling on `rag`
- Dispatches inbound request events to `RAGAgent`
- Publishes completion events to `rag-complete`
- Emits structured lifecycle logs for `startup_topic_check`, `consumed`, `processing_started`, `processing_completed`, `publish_completed`, and `error`

## Run tests

```bash
.venv/bin/python -m pytest -q rag_agent/tests/test_request_event.py rag_agent/tests/test_completion_event.py rag_agent/tests/test_logging.py rag_agent/tests/test_kafka_integration.py
```
