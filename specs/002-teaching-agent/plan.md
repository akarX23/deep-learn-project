# Implementation Plan: Teaching Agent

**Branch**: `002-build-teaching-agent` | **Date**: 2026-05-28 | **Spec**: `/specs/002-teaching-agent/spec.md`
**Input**: Feature specification from `/specs/002-teaching-agent/spec.md`

## Summary

Implement a synchronous Teaching Agent that receives a topic, output mode, and optional
session context from the Planner Agent, calls an LLM to generate a mode-specific
structured explanation (beginner / intermediate / advanced), validates the Mermaid diagram
if one is generated, and returns a schema-safe JSON response containing explanation, diagram,
notes, example, and audit metadata.

The agent uses LiteLLM as the LLM interface through its own `teaching_agent/llm_client.py`
module (not shared with the RAG agent). Configuration is loaded from environment variables.
No graph orchestration runtime (LangGraph) is used — the pipeline is a linear single-step
sequence that does not require stateful loop orchestration.

Phase 2 adds a Kafka integration layer (`kafka.py`, `handlers.py`, `worker.py`) following
the same three-file pattern as the RAG agent. The worker consumes `TeachingRequestEvent`
payloads from the `"teaching"` Kafka topic, invokes `TeachingAgent.run()` unchanged, and
publishes `TeachingCompletionEvent` results to `"teaching-complete"`. The core pipeline
logic from Phase 1 is not modified.

Phase 4 adds real-time token streaming. The LLM prompt switches from JSON mode to a
markdown bold-header format (`**Explanation**`, `**Diagram**`, `**Notes**`, `**Example**`).
A new `StreamingFieldExtractor` component processes the LiteLLM delta stream and publishes
field-keyed `StreamTokensEventBody` events to the `"stream-tokens"` Kafka topic in real
time. The `diagram` field is buffered and sent as one complete event; all other fields
stream token by token. A stream-complete sentinel (`{"done": true}`) signals the end.
`TeachingCompletionEvent.content` now carries the complete raw markdown string (not
JSON-serialized `TeachingContent`). Phase 3 (reflection pattern, colleague-owned) is a
separate branch and is not in scope here.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pydantic v2, litellm>=1.40.0, pytest>=8.0.0 (no new packages beyond existing requirements.txt)
**Storage**: N/A (pure in-memory; no file I/O beyond CLI input for development)
**Testing**: pytest
**Target Platform**: Linux runtime (local dev and container-ready execution)
**Project Type**: Agent module/library within a multi-agent backend
**Performance Goals**: Beginner mode ≤ 5s wall-clock; intermediate ≤ 10s; advanced ≤ 20s on developer hardware under a fast-endpoint model
**Constraints**: Synchronous execution only; per-mode token ceilings enforced at LiteLLM call level via `TEACHING_{MODE}_MAX_TOKENS` env vars (default 4096 each); per-mode model, API key, temperature, and effort also configurable via `TEACHING_{MODE}_MODEL` / `TEACHING_{MODE}_API_KEY` / `TEACHING_{MODE}_TEMPERATURE` / `TEACHING_{MODE}_EFFORT` with fallback to shared `TEACHING_MODEL` / `TEACHING_API_KEY` / `TEACHING_TEMPERATURE`; effort (`low | medium | high`) maps to `output_config={"effort": value}` for Claude 4.6 models only, silently skipped for all others; Mermaid validation required before returning diagram; LLM called without JSON mode (Phase 4) — output is markdown with bold section headers; `TeachingCompletionEvent.content` is raw markdown (Phase 4); no LangGraph
**Scale/Scope**: One synchronous request per invocation; invoked once per user query by the Planner Agent

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate Review (Pre-Research)

- Code Quality Gate: PASS. Responsibility boundaries are explicit by module:
  `project/schemas.py`, `teaching_agent/agent.py`, `teaching_agent/llm_client.py`,
  `teaching_agent/prompts.py`, `teaching_agent/validators.py`, `teaching_agent/helpers.py`,
  `teaching_agent/config.py`. No cross-agent module imports.
- Testing Gate: PASS. Planned tests cover: schema validation per mode, cross-mode
  differentiation (same topic at all three modes), diagram presence/absence rules, Mermaid
  validity enforcement, error response structure on LLM failure and invalid input, and
  token ceiling compliance.
- UX Consistency Gate: PASS. Output format (JSON structure) is stable across all modes
  and requests. Explanation structure per mode is defined and enforced by prompt templates.
  Diagram validation prevents broken Mermaid from reaching the Streamlit renderer.
- Performance Gate: PASS. Token ceilings define measurable per-mode budgets enforced at the
  LiteLLM call boundary. Per-mode wall-clock targets are stated and verifiable.
- Maintainability Gate: PASS. Config and prompt templates are centralized in dedicated
  modules. Mermaid validation is isolated in `validators.py`. All non-obvious design
  decisions are documented in `research.md`.

### Post-Design Gate Review (After Phase 1 Artifacts)

- Code Quality Gate: PASS. Data model and contracts are defined; no cross-module ambiguity.
  Module boundary for schemas follows the established `project/schemas.py` pattern.
- Testing Gate: PASS. `quickstart.md` includes both full-run and targeted test instructions.
  Test mocking pattern mirrors the RAG agent suite (monkeypatching `call_llm`).
- UX Consistency Gate: PASS. Contract defines stable field structure; diagram null-fallback
  behavior is documented so the UI can handle both cases.
- Performance Gate: PASS. Token ceiling enforcement is at the LiteLLM call level with
  actual consumption reported in metadata. Wall-clock targets are stated.
- Maintainability Gate: PASS. Environment-variable-driven configuration eliminates
  hard-coded provider coupling. Separate prompt templates per mode are independently
  auditable.

## Project Structure

### Documentation (this feature)

```text
specs/002-teaching-agent/
├── plan.md                          # This file
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/
│   └── teaching-agent-contract.md   # Phase 1 output
├── checklists/
│   └── requirements.md
└── tasks.md                         # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
project/
├── schemas.py           # Phase 1: OutputMode, TeachingAgentInput, TeachingContent,
│                        #           TeachingMetadata, TeachingAgentOutput
│                        # Phase 2: TeachingRequestEvent, TeachingCompletionEvent
│                        # Phase 4: StreamTokensEventBody (already present, no change)
└── topics.py            # Phase 2: Add TEACHING to PlannerTopics; add TeachingTopics enum
                         #           (TEACHING_COMPLETE only); include in get_all_topic_names()
                         # Phase 4: BackendStreamTopics.STREAM_TOKENS (already present, no change)

teaching_agent/
├── __init__.py
├── agent.py             # Phase 1: TeachingAgent class: run(), input validation, prompt dispatch,
│                        #           response assembly
│                        # Phase 4: uses call_llm_stream(); accepts token_callback; calls
│                        #           parse_markdown_response() on complete buffer
├── config.py            # LLMConfig dataclass, get_llm_config(), per-mode max_tokens map
├── llm_client.py        # Phase 1: call_llm(messages, config) → (str, int)
│                        # Phase 4: add call_llm_stream(messages, config) → Iterator[(str, int)];
│                        #           remove response_format=json_object from call_llm()
├── prompts.py           # Phase 1: BEGINNER_PROMPT, INTERMEDIATE_PROMPT, ADVANCED_PROMPT constants
│                        # Phase 4: updated to markdown bold-header output format
├── validators.py        # validate_mermaid(diagram: str) → bool; regex-based structural check
├── helpers.py           # Phase 1: parse_llm_response(raw) → dict; build_error_output()
│                        # Phase 4: parse_llm_response() replaced by parse_markdown_response()
├── stream_parser.py     # Phase 4 (new): StreamingFieldExtractor — state machine for field-keyed
│                        #                token extraction from markdown delta stream
├── kafka.py             # Phase 2: Protocol types, factory functions, topic helpers
│                        # Phase 4: add publish_stream_token(producer, StreamTokensEventBody)
├── handlers.py          # Phase 2: TeachingRequestEventHandler
│                        # Phase 4: builds token_callback; accumulates raw_markdown;
│                        #           publishes stream_complete sentinel; content = raw_markdown
├── worker.py            # Phase 2: TeachingWorker lifecycle (unchanged in Phase 4)
└── tests/
    ├── __init__.py
    ├── test_teaching_agent.py       # Phase 1 tests (real LLM calls)
    │                                # Phase 4: updated mocks (markdown format, call_llm_stream)
    ├── test_kafka_integration.py    # Phase 2: handler + publish tests (fake Kafka)
    │                                # Phase 4: updated for streaming events
    ├── test_worker_runtime.py       # Phase 2: worker lifecycle tests (unchanged in Phase 4)
    ├── test_stream_parser.py        # Phase 4 (new): unit tests for StreamingFieldExtractor
    ├── live_call_test.py
    ├── run_samples.py
    └── inputs/
        └── sample_input.json
```

**Structure Decision**: Single Python agent module following the `rag_agent/` layout.
Schemas in `project/schemas.py` (shared contract location). No new top-level directories.
No LangGraph — the linear pipeline requires only a plain class. Phase 2 Kafka files follow
the RAG agent three-file pattern exactly for system-wide consistency.

## Behavior Rules and Requirement Clarifications

These clarifications resolve interpretation questions left open by the Technical Context
section. They are binding design decisions, traceable to the listed spec requirements.

### Token-Ceiling Semantics (FR-008, SC-005)

- The per-mode ceiling is read from `TEACHING_{MODE}_MAX_TOKENS` (where `{MODE}` is `BEGINNER`, `INTERMEDIATE`, or `ADVANCED`) and defaults to 4096 when unset. It governs **generated completion tokens**, enforced as `max_tokens` at the LiteLLM call boundary. No ceiling value is hardcoded in `config.py` — all defaults resolve from environment/configuration files. This is the value reported as `metadata.tokens_used` (the `completion_tokens` field of the LLM usage response).

Similarly, `TEACHING_{MODE}_MODEL` selects the model per learner level (fallback: `TEACHING_MODEL`), `TEACHING_{MODE}_API_KEY` selects the API key (fallback: `TEACHING_API_KEY`), `TEACHING_{MODE}_TEMPERATURE` sets the sampling temperature (fallback: `TEACHING_TEMPERATURE`, default 0.7), and `TEACHING_{MODE}_EFFORT` sets the output effort level (`low | medium | high`) for Claude 4.6 models only (silently skipped for all other models — Haiku, Groq/Llama, etc. do not support `output_config`). This allows different providers, quotas, temperature, and compute effort per mode without changing any Python file.
- Prompt + `context` tokens are **not** counted against the completion ceiling, but are
  bounded separately: `agent.py` enforces an input guard that truncates/rejects an oversized
  `context` before dispatch, so total request size stays within the model window and a long
  prior-session summary cannot crowd out the generated answer.
- Rationale: `max_tokens` only caps completion, not prompt+completion. SC-005 is measured
  against completion tokens; defining the ceiling this way makes enforcement deterministic at
  the call boundary and keeps `tokens_used` reporting unambiguous for downstream consumers.

### Mermaid Validation Depth (FR-007)

- `validators.py::validate_mermaid` performs a **structural (regex-based) check**, not a full
  Mermaid parse. It verifies: a recognized diagram header (`graph TD|LR`, `flowchart`,
  `sequenceDiagram`), at least one node/edge token, and balanced brackets/parentheses.
- This is an accepted v1 limitation: a structurally valid but semantically broken diagram may
  pass. A true Mermaid parser is deferred; the structural check is sufficient to prevent the
  common malformed-output failure modes from reaching the renderer.
- Beginner-mode fallback (required non-null diagram per FR-005): on validation failure the
  agent retries generation once; if the retry also fails validation, it substitutes a minimal
  valid template diagram rather than returning null or erroring. Intermediate/advanced simply
  set `diagram` to null on failure.

### Output-Mode Authority (FR-003)

- `output_mode` is treated as **authoritative and opaque**. The agent selects the prompt
  template and token ceiling strictly from the input value and never infers, overrides, or
  re-derives the mode from `topic` or `context`.
- The response mirrors the input `output_mode` exactly in all cases, including errors.
- An `output_mode` outside the three enum values fails input validation and returns
  `status: "error"` before any LLM call (no default/fallback mode).

### Per-Mode Diagram Rules (FR-005, FR-006)

| output_mode  | diagram field behavior                                                    |
|--------------|---------------------------------------------------------------------------|
| beginner     | Always non-null; `graph TD` or `sequenceDiagram`; required (see fallback) |
| intermediate | Non-null only when the topic has structural/sequential complexity; else null |
| advanced     | Non-null only when visualization communicates more than prose; else null  |

The mode-specific rule is enforced in `agent.py` after diagram validation; full field-level
validation rules live in `data-model.md` and `contracts/teaching-agent-contract.md`.

### Token Streaming Rules (FR-029 – FR-035, Phase 4)

| Rule | Detail |
|---|---|
| LLM output format | Markdown with bold section headers; `response_format={"type": "json_object"}` removed |
| Section headers | `**Explanation**`, `**Diagram**`, `**Notes**`, `**Example**` — exact bold-header strings |
| Streaming topic | `"stream-tokens"` (`BackendStreamTopics.STREAM_TOKENS`) |
| Token event `data` | `{"field": "<section>", "token": "<chunk>"}` |
| Diagram handling | Buffered by `StreamingFieldExtractor`; published once as a complete event when the next section header or stream end is detected |
| Stream-complete sentinel | `{"done": true, "tokens_used": N}` — always published last, including on error |
| `TeachingCompletionEvent.content` | Complete raw markdown string on success; `""` on error (replaces JSON-serialized `TeachingContent`) |
| Internal parsing | `parse_markdown_response()` used in `agent.py` for Mermaid validation and `TeachingAgentOutput`; not exposed to Kafka |
| Diagram retry (beginner) | Retry LLM call uses `call_llm()` (non-streaming); retry tokens are not published to `"stream-tokens"` |

### Kafka Event Rules (FR-019 – FR-028)

| Rule | Detail |
|---|---|
| Inbound topic | `"teaching"` — consumed by `TeachingWorker`; published by Planner Agent |
| Outbound topic | `"teaching-complete"` — published by `TeachingRequestEventHandler` |
| `request_id` pass-through | Copied verbatim from `TeachingRequestEvent` to `TeachingCompletionEvent`; Teaching Agent never modifies it |
| `sid` pass-through | Copied verbatim from `TeachingRequestEvent`; used by backend to route completion event to the correct Socket.IO session; Teaching Agent never reads or validates its contents |
| `user_level` pass-through | Copied verbatim from `TeachingRequestEvent` to `TeachingCompletionEvent`; also used as `output_mode` for the core pipeline |
| Field mapping in handler | `user_prompt` → `topic`, `user_level` → `output_mode`, `rag_compiled` → `context` before calling `TeachingAgent.run()` |
| Always-publish rule | A `TeachingCompletionEvent` is published for every consumed message regardless of outcome; `content` is `""` (empty string) on failure; Planner is never left waiting |
| Malformed payload | Logged with `request_id` (or `"unknown"` if absent), skipped; poll loop continues without crashing |
| Topic bootstrap | `PlannerTopics.TEACHING` and `TeachingTopics.TEACHING_COMPLETE` registered in `project/topics.py`; both included in `get_all_topic_names()`; backend service creates topics at startup |
| Test isolation | All Kafka dependencies injectable via factory parameters; tests use Protocol-compatible fakes, no real Kafka required |

### Edge-Case Handling (spec "Edge Cases", FR-010)

| Edge case                                   | Handling                                                        |
|---------------------------------------------|-----------------------------------------------------------------|
| Single-word vs multi-word topic             | No special handling; passed verbatim to the prompt              |
| Empty `context`                             | Valid input; full response produced without prior-session context |
| Lengthy `context` summary                   | Input guard bounds context tokens (see Token-Ceiling Semantics) so the completion ceiling is unaffected |
| Same topic, different modes                 | Distinct prompt templates yield structurally distinct output (FR-004) |
| Ambiguous / out-of-scope topic              | Prompts instruct a structured best-effort response; never an error solely for ambiguity |
| LLM call fails or returns empty             | `status: "error"`, `tokens_used: 0`, no unhandled exception (FR-010) |
| Invalid generated Mermaid                   | Diagram set to null (intermediate/advanced) or retried/fallback (beginner); never returned invalid |

## Complexity Tracking

No constitution violations identified. Complexity is justified by the per-mode prompt
differentiation requirement (three separate prompt templates) and Mermaid validation,
both of which are direct spec requirements rather than architectural overhead.
