# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

For additional context about technologies to be used, project structure,
shell commands, and other important information, read
specs/002-teaching-agent/plan.md
## Project Overview

Multi-agent AI Tutor backend (Python 3.11). All agents communicate exclusively through Kafka — no direct agent-to-agent calls. The Planner Agent orchestrates the workflow by writing to Kafka topics; each agent consumes its input topic and publishes its result to an output topic.

```
UI
 └─► Backend Service (FastAPI)
      └─► Kafka
           ├─► RAG Agent        (consume: "rag"      | publish: "rag-complete")
           ├─► Teaching Agent   (consume: "teaching"  | publish: "teaching-complete")
           └─► Planner Agent    (not yet implemented)
```

## Commands

Install dependencies:
```bash
pip install -r requirements.txt
```

Run teaching agent tests (default `pytest.ini` target):
```bash
pytest
```

Run a single test file:
```bash
pytest teaching_agent/tests/test_teaching_agent.py -q
```

Run a single test by name:
```bash
pytest teaching_agent/tests/test_teaching_agent.py -q -k test_beginner_success
```

Run sample outputs across all 3 topics × 3 modes (real LLM calls, saves JSON to `teaching_agent/tests/outputs/`):
```bash
PYTHONPATH=. python teaching_agent/tests/run_samples.py
```

Run teaching agent CLI directly:
```bash
PYTHONPATH=. python teaching_agent/agent.py --input teaching_agent/tests/inputs/sample_input.json
```

Start the backend service:
```bash
uvicorn backend_service.app.main:app --host 0.0.0.0 --port 8001
```

Run RAG worker (Kafka consume loop):
```bash
PYTHONPATH=. python rag_agent/worker.py
```

Run Teaching Agent worker (Kafka consume loop):
```bash
PYTHONPATH=. python teaching_agent/worker.py
```

End-to-end smoke test for Teaching Agent (requires worker running + Kafka up):
```bash
PYTHONPATH=. python teaching_agent/tests/e2e_smoke.py
```

## Architecture

### Shared contracts (`project/`)

| Module | Role |
|---|---|
| `project/schemas.py` | All Pydantic v2 schemas for every agent and Kafka event. Single source of truth for inter-agent data contracts. |
| `project/topics.py` | Kafka topic registry. `PlannerTopics`, `RAGTopics`, `TeachingTopics` enums; `get_all_topic_names()` drives backend bootstrap; `get_teaching_topic_names()` / `get_rag_topic_names()` are agent-scoped subsets used by each worker at startup. Add new topic enums here — never hardcode topic strings in agent code. |

### Backend Service (`backend_service/`)

FastAPI service that owns Kafka cluster lifecycle. On startup it calls `get_all_topic_names()` from `project/topics.py` and bootstraps any missing topics idempotently. Exposes a REST API for topic inspection.

- `app/main.py` — `create_app()` factory with lifespan hook (connect → bootstrap topics → yield → close)
- `app/kafka_admin.py` — `KafkaAdminService`: wraps `kafka-python` admin client
- `app/config.py` — `KafkaSettings` (reads `BACKEND_KAFKA_*` env vars from `.env.local`)
- `app/api/topics.py` — REST endpoints for topic presence checks

### RAG Agent (`rag_agent/`) — colleague-owned, do not modify

Four-layer structure that mirrors what the Teaching Agent Kafka integration should follow:

| File | Role |
|---|---|
| `agent.py` | `RAGAgent`: LangGraph `StateGraph` loop — `process_page` → relevance-score → `_compile_material` |
| `kafka.py` | Protocol types (`KafkaConsumerProtocol`, `KafkaProducerProtocol`) + factory functions (`create_consumer`, `create_producer`) + topic-specific helpers (`consumer_subscribe_rag`, `publish_rag_complete`) |
| `handlers.py` | `RAGRequestEventHandler`: parse Kafka payload → validate → run agent → build completion event → publish |
| `worker.py` | `RAGWorker`: owns consumer/producer lifecycle; runs poll loop in a background thread via `threading.Event` |
| `utils/helpers.py` | Merged config module: `LLMConfig`, `KafkaRuntimeConfig` dataclasses + pure PDF helpers + env-read functions |
| `utils/llm_client.py` | LiteLLM wrapper for RAG model calls |
| `utils/tools.py` | Stateless PyMuPDF extraction (`get_page_count`, `extract_text_from_page`, etc.) + `score_page_relevance` |

### Teaching Agent (`teaching_agent/`) — Shalin's module

Fully implemented: core pipeline + Kafka integration + token streaming + multi-turn + guardrail.

| File | Role |
|---|---|
| `agent.py` | `TeachingAgent.run(raw_input, token_callback)` — Step 0: guardrail classification → Step 1: validate input → Step 2: load config → Step 3: render prompt → Step 4: stream LLM → Step 5: validate/sanitize Mermaid → Step 6: assemble content → Step 7: reflection loop → Step 8: return `(TeachingAgentOutput, raw_markdown)`. Never raises — all failure paths return `status='error'`. |
| `guardrail.py` | `GuardrailClassifier.classify(topic, config) → str`: classifies prompt as `greeting / off_topic / unclear / valid_question` via a fast LLM call; returns `"valid_question"` on any failure (fail-open). `get_canned_response(category)` returns canned text or `None`. |
| `config.py` | `LLMConfig` dataclass + `get_llm_config(output_mode)`, `get_reflection_config()`, `get_guardrail_config()`, `get_max_reflection_iterations()`; `KafkaRuntimeConfig` dataclass + `from_env()`. Loads `.env` then `.env.local` at import time. `TEACHING_MODEL` is required. |
| `llm_client.py` | `call_llm(messages, config) → (content, tokens_used)`. `call_llm_stream(messages, config) → Iterator[(delta, tokens_used)]`. Provider API keys auto-read by LiteLLM from env. |
| `prompts.py` | `BEGINNER_PROMPT`, `INTERMEDIATE_PROMPT`, `ADVANCED_PROMPT`; `PROMPT_BY_MODE` dict. `REFLECTION_PROMPT_BY_MODE`, `REVISION_PROMPT_BY_MODE`. `GUARDRAIL_PROMPT` — classification prompt returning `{"category": "...", "reason": "..."}`. All generation prompts return markdown with `**Explanation**`, `**Diagram**`, `**Notes**`, `**Example**` bold-header sections. |
| `validators.py` | `validate_mermaid(diagram)` — regex structural check. |
| `helpers.py` | `parse_markdown_response(raw)` — splits on bold-header sections. `sanitize_mermaid_labels(diagram)` — auto-quotes unquoted node labels with special chars. `build_messages(prompt, chat_history)`, `build_error_output()`. |
| `stream_parser.py` | `StreamingFieldExtractor` — state machine that buffers diagram and streams explanation/notes/example token-by-token via `token_callback`. `finalize()` returns `(raw_markdown, diagram_raw)`. |
| `kafka.py` | Protocol types + factory functions + topic helpers: `consumer_subscribe_teaching()`, `publish_teaching_complete()`, `publish_stream_token()`. |
| `handlers.py` | `TeachingRequestEventHandler`: parse Kafka payload → `agent.run()` → publish stream tokens → stream-complete sentinel → `TeachingCompletionEvent`. Always publishes a completion event. |
| `worker.py` | `TeachingWorker`: owns consumer/producer lifecycle; startup topic presence check; runs poll loop in daemon thread. `main()` entry point. |

### Teaching Agent pipeline — key behaviors

**Step 0 — Guardrail** (skipped when `chat_history` non-empty):
- Classifies prompt via fast LLM call; non-`valid_question` → emits single `token_callback("explanation", canned_text)` → returns early with `status="ok"`, `content=None`, `raw_markdown=canned_text`
- No schema changes: `content=None` is already valid; handler uses `raw_markdown` for `TeachingCompletionEvent.content`

**Output mode rules:**

| Mode | Diagram | Token ceiling |
|---|---|---|
| `beginner` | Required — retry once on invalid, then use `_BEGINNER_FALLBACK_DIAGRAM` | `TEACHING_BEGINNER_MAX_TOKENS` (default 4096) |
| `intermediate` | Optional — null if topic is not structural/sequential | `TEACHING_INTERMEDIATE_MAX_TOKENS` (default 4096) |
| `advanced` | Optional — null unless visualization adds over prose | `TEACHING_ADVANCED_MAX_TOKENS` (default 4096) |

**Streaming:** `explanation`, `notes`, `example` stream token-by-token via `"stream-tokens"` Kafka topic. `diagram` is buffered and emitted as one complete event. Stream-complete sentinel `{"done": true, "tokens_used": N}` is always the last event — including on error paths.

**Mermaid sanitization:** `sanitize_mermaid_labels()` runs before `validate_mermaid()` on every diagram path (initial, retry, revision). It auto-wraps unquoted labels containing `:(){}#%÷×≤≥≠` in double quotes.

**Reflection loop (Phase 3):** Runs after initial generation at N iterations (`TEACHING_MAX_REFLECTION_ITERATIONS`, default 1; N=0 disables). Each iteration: critique call → revision call. Any failure breaks the loop and returns best available content. `N=0` is equivalent to the pre-reflection pipeline.

**Multi-turn (Phase 5):** `chat_history: list[dict]` (oldest→newest `{role, content}` pairs, default `[]`) prepended to LLM messages. Empty history reproduces single-turn behavior exactly.

## Environment Variables

### Teaching Agent

**Shared (fallback) variables:**
| Variable | Required | Notes |
|---|---|---|
| `TEACHING_MODEL` | **Yes** | Required when no per-mode model override is set. Any LiteLLM string: `groq/llama-3.3-70b-versatile`, `anthropic/claude-sonnet-4-6`, `gemini/gemini-1.5-flash`, `gpt-4o` |
| `TEACHING_API_KEY` | No | Shared API key fallback; omit to let LiteLLM read the standard provider key |
| `TEACHING_TEMPERATURE` | No | Default `0.7` |
| `TEACHING_API_BASE` | No | Self-hosted/custom-proxy endpoints only |

**Per-mode overrides** (`{MODE}` = `BEGINNER`, `INTERMEDIATE`, or `ADVANCED`):
| Variable | Notes |
|---|---|
| `TEACHING_{MODE}_MODEL` | Overrides `TEACHING_MODEL` for this mode |
| `TEACHING_{MODE}_API_KEY` | Overrides `TEACHING_API_KEY` for this mode |
| `TEACHING_{MODE}_MAX_TOKENS` | Token ceiling for this mode; default `4096` |
| `TEACHING_{MODE}_TEMPERATURE` | Overrides `TEACHING_TEMPERATURE` for this mode |
| `TEACHING_{MODE}_EFFORT` | `low\|medium\|high`; maps to `output_config` for Claude 4.6 models only; silently skipped for all other models |

**Guardrail (Phase 6):**
| Variable | Notes |
|---|---|
| `TEACHING_GUARDRAIL_ENABLED` | `true` (default) or `false` to disable |
| `TEACHING_GUARDRAIL_MODEL` | Falls back to `TEACHING_MODEL` |

### RAG Agent
| Variable | Default |
|---|---|
| `RAG_TEXT_MODEL` | `gpt-4o-mini` |
| `RAG_TEXT_PROVIDER` | `hosted_vllm` |
| `RAG_TEXT_API_BASE` | — |
| `RAG_TEXT_API_KEY` | — |
| `RAG_VLM_MODEL` | `gpt-4o-mini` |
| `RAG_VLM_PROVIDER` | `hosted_vllm` |
| `RAG_VLM_API_BASE` | — |
| `RAG_EMBEDDING_MODEL` | — |
| `RAG_EMBEDDING_PROVIDER` | `hosted_vllm` |

### Backend Service / Kafka
| Variable | Required | Notes |
|---|---|---|
| `BACKEND_KAFKA_BOOTSTRAP_SERVERS` | **Yes** | e.g. `localhost:9092` |
| `BACKEND_KAFKA_STARTUP_RETRY_COUNT` | No | Default `5` |
| `BACKEND_KAFKA_STARTUP_RETRY_TIMEOUT_SECONDS` | No | Default `2` |
| `BACKEND_KAFKA_SECURITY_PROTOCOL` | No | For SASL/SSL clusters |

Backend service reads from `.env.local` (existing env wins; `.env.local` supplies local defaults).

## Testing Notes

- `pytest.ini` testpaths points to `teaching_agent/tests` only. RAG agent tests require the RAG environment (colleague's setup).
- `test_teaching_agent.py` — schema/validator/parser unit tests + agent integration tests. Integration tests make **real LLM calls** — `TEACHING_MODEL` must be set.
- `test_guardrail.py` — 13 unit tests for `GuardrailClassifier` and `get_canned_response`. Fully offline (monkeypatched `call_llm`).
- `test_kafka_integration.py` — handler dispatch, publish routing, correlation fields, logging. Uses Protocol-compatible fakes — **no real Kafka needed**.
- `test_worker_runtime.py` — startup/shutdown lifecycle, idle loop, batch failure recovery. Uses Protocol-compatible fakes — **no real Kafka needed**.
- `test_stream_parser.py` — `StreamingFieldExtractor` unit tests. Fully offline.
- Monkeypatch target for guardrail: `teaching_agent.guardrail.call_llm`.
- Monkeypatch target for main generation: `teaching_agent.agent.call_llm_stream` (yields `(delta, tokens)` tuples).
- Monkeypatch target for reflection/revision: `teaching_agent.agent.call_llm`.
- RAG agent monkeypatch targets (for reference): `rag_agent.agent.call_llm` and `rag_agent.tools.call_llm`.

## Spec Artifacts

Feature specifications, plans, data models, and task lists live under `specs/<feature-id>/`:

| ID | Feature | Status |
|---|---|---|
| `000` | Planner Agent | Spec written, not implemented |
| `001` | RAG Retrieval Agent | Implemented |
| `002` | Teaching Agent | Fully implemented (core pipeline + Kafka + streaming + multi-turn + guardrail) |
| `003` | Integrate Kafka Backend | Implemented (backend service + RAG worker) |

## Claude Code Instructions
- State all constraints before writing a file, not after reviewing it
- When a test fails, read the source files and reason first before writing debug scripts
- Always write tests to .py files, never use python -c for multi-line tests
- Do not re-read spec files that were already read in this session unless explicitly asked
- Do not modify any files inside `rag_agent/` — that module is owned by a colleague
- New Kafka topic names must be added to `project/topics.py` enums, never hardcoded in agent code
