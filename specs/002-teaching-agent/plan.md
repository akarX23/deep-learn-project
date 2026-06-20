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
payloads from the `"teaching"` Kafka topic, maps the event's `user_prompt` / `user_level` /
`rag_compiled` onto `TeachingAgent.run()`'s `topic` / `output_mode` / `context`, and
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

Phase 5 adds multi-turn conversation support. A new optional `chat_history` field on
`TeachingRequestEvent` / `TeachingAgentInput` carries prior conversation turns
(`{role, content}`, oldest→newest, excluding the current query). The agent threads this
history into the LLM message list ahead of the current structured prompt
(`messages = [*chat_history, {"role": "user", "content": prompt}]`) — there is no follow-up
branch, no conversational mode, and no auto-detection. Every turn keeps the existing 4-section
structured output; the streaming pipeline, diagram handling, parsing, and the reflection loop
(gated at N=0) are unchanged. An empty `chat_history` (the default) reproduces single-turn
behavior exactly, so the change is additive and backward-compatible. The Planner owns history
truncation/summarization; an optional defensive cap (`TEACHING_MAX_HISTORY_TURNS`) is
available in the agent.

Phase 6 adds a guardrail classification step executed as Step 0 of `TeachingAgent.run()` —
before any config loading, prompt rendering, or main LLM call. A small, fast LLM call
classifies the user prompt into one of four categories: `greeting`, `off_topic`, `unclear`,
or `valid_question`. Only `valid_question` proceeds to Step 1 of the existing pipeline;
the other three categories receive canned friendly responses delivered via a single
`token_callback("explanation", canned_text)` call, and `run()` returns early with
`status="ok"`, `content=None`, `raw_markdown=canned_text`. No schema changes are needed
because `TeachingAgentOutput.content` is already `Optional` and the handler uses
`raw_markdown` (not `content`) to build `TeachingCompletionEvent.content`. The guardrail
is skipped entirely when `chat_history` is non-empty (follow-up queries always run the
full pipeline). On any classification failure the guardrail fails open — the full pipeline
runs as if the input were `valid_question`.

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
  Test mocking pattern mirrors the RAG agent suite (monkeypatching `call_llm`). Phase 3 adds
  reflection tests (all monkeypatched, no real LLM): N=0 single-pass equivalence, critique
  and revision fallback paths (SC-012), token accumulation across calls (SC-013), and the
  two-iteration case. The SC-011 quality-improvement rubric (≥80% of runs) is validated
  manually with a real model (tasks.md T046), not in the automated suite.
- UX Consistency Gate: PASS. Contract defines stable field structure; diagram null-fallback
  behavior is documented so the UI can handle both cases.
- Performance Gate: PASS. Token ceiling enforcement is at the LiteLLM call level with
  actual consumption reported in metadata. Wall-clock targets are stated; reflection adds
  2N LLM calls per request; wall-clock budget updated per FR-018; N=0 restores the Phase 1
  budget; the latency cost is justified by the quality improvement requirement (SC-011).
- Maintainability Gate: PASS. Environment-variable-driven configuration eliminates
  hard-coded provider coupling. Separate prompt templates per mode are independently
  auditable; reflection prompts isolated in `REFLECTION_PROMPT_BY_MODE` /
  `REVISION_PROMPT_BY_MODE` constants, independently auditable and replaceable without
  touching agent logic.

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
│                        #           TeachingMetadata (add reflection_iterations int field),
│                        #           TeachingAgentOutput
│                        # Phase 2: TeachingRequestEvent, TeachingCompletionEvent
│                        # Phase 4: StreamTokensEventBody (already present, no change)
│                        # Phase 5: + chat_history on TeachingRequestEvent & TeachingAgentInput (default [])
└── topics.py            # Phase 2: Add TEACHING to PlannerTopics; add TeachingTopics enum
                         #           (TEACHING_COMPLETE only); include in get_all_topic_names()
                         # Phase 4: BackendStreamTopics.STREAM_TOKENS (already present, no change)

teaching_agent/
├── __init__.py
├── agent.py             # Phase 1: TeachingAgent class: run(), input validation, prompt dispatch,
│                        #           response assembly
│                        # Phase 4: uses call_llm_stream(); accepts token_callback; calls
│                        #           parse_markdown_response() on complete buffer
│                        # Phase 5: pass agent_input.chat_history into build_messages()
│                        # Phase 6: Step 0 guardrail check; skip if chat_history non-empty;
│                        #           call GuardrailClassifier; early return with canned text
│                        #           for non-valid_question; fall through on failure (fail-open)
├── guardrail.py         # Phase 6 (new): GuardrailClassifier.classify(topic) → str;
│                        #   calls LLM with GUARDRAIL_PROMPT; parses {"category": "..."}; 
│                        #   returns "valid_question" on any failure (fail-open)
│                        #   _CANNED_RESPONSES dict; get_canned_response(category) → str
├── config.py            # LLMConfig dataclass, get_llm_config(), per-mode max_tokens map
│                        # Phase 5 (optional): get_max_history_turns() defensive cap
│                        # Phase 6: get_guardrail_config() reading TEACHING_GUARDRAIL_MODEL
│                        #   (fallback: TEACHING_MODEL); TEACHING_GUARDRAIL_ENABLED (default true)
├── llm_client.py        # Phase 1: call_llm(messages, config) → (str, int)
│                        # Phase 4: add call_llm_stream(messages, config) → Iterator[(str, int)];
│                        #           remove response_format=json_object from call_llm()
├── prompts.py           # Phase 1: BEGINNER_PROMPT, INTERMEDIATE_PROMPT, ADVANCED_PROMPT constants
│                        # Phase 4: updated to markdown bold-header output format
│                        # Phase 5 (optional): one-line conversation-aware nudge per template
│                        # Phase 6: GUARDRAIL_PROMPT — classification prompt returning
│                        #           {"category": "greeting|off_topic|unclear|valid_question", "reason": "..."}
│                        # Bugfix (FR-046): all 3 prompts instruct LLM to quote node labels
│                        # Bugfix (FR-051): all 3 prompts instruct LLM to use small example
│                        #                  inputs (n ≤ 10) to prevent token exhaustion
├── validators.py        # validate_mermaid(diagram: str) → bool; regex-based structural check
├── helpers.py           # Phase 1: parse_llm_response(raw) → dict; build_error_output()
│                        # Phase 4: parse_llm_response() replaced by parse_markdown_response()
│                        # Phase 5: build_messages(prompt, chat_history=None) prepends history
│                        # Bugfix: sanitize_mermaid_labels(diagram) — auto-quotes unquoted node
│                        #         labels containing special chars before validate_mermaid()
├── stream_parser.py     # Phase 4 (new): StreamingFieldExtractor — state machine for field-keyed
│                        #                token extraction from markdown delta stream
├── kafka.py             # Phase 2: Protocol types, factory functions, topic helpers
│                        # Phase 4: add publish_stream_token(producer, StreamTokensEventBody)
├── handlers.py          # Phase 2: TeachingRequestEventHandler
│                        # Phase 4: builds token_callback; accumulates raw_markdown;
│                        #           publishes stream_complete sentinel; content = raw_markdown
│                        # Phase 5: passes event.chat_history into agent.run() input
├── worker.py            # Phase 2: TeachingWorker lifecycle (unchanged in Phase 4)
└── tests/
    ├── __init__.py
    ├── test_teaching_agent.py       # Phase 1 tests (real LLM calls)
    │                                # Phase 4: updated mocks (markdown format, call_llm_stream)
    │                                # Phase 5: build_messages + run() history tests
    ├── test_kafka_integration.py    # Phase 2: handler + publish tests (fake Kafka)
    │                                # Phase 4: updated for streaming events
    │                                # Phase 5: handler passes chat_history; multi-turn test
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

## Reflection Architecture

> Phase 3. Corresponds to the Reflection proposal in `spec.md` (US6, FR-029–FR-037),
> pending team sign-off. Implementation is gated on that ratification.

### Pattern: Generate → Critique → Revise (×N)

```
Input
  │
  ▼
[1] Generation call  →  initial TeachingContent  (PROMPT_BY_MODE)
  │
  ▼
[2] Critique call    →  ReflectionCritique JSON  (REFLECTION_PROMPT_BY_MODE)
  │    (if fails: skip to [4] with initial output)
  ▼
[3] Revision call    →  revised TeachingContent  (REVISION_PROMPT_BY_MODE)
  │    (if fails: skip to [4] with initial output)
  ▼
[4] Repeat [2]–[3] up to N-1 more times
  │
  ▼
Assemble TeachingAgentOutput with best available content
```

N = `get_max_reflection_iterations(output_mode)`, which resolves
`TEACHING_{MODE}_MAX_REFLECTION_ITERATIONS` → `TEACHING_MAX_REFLECTION_ITERATIONS` (global)
→ default 1. N = 0 → steps [2]–[4] are skipped entirely; behavior identical to Phase 1.

### Critique Prompt Design

`REFLECTION_PROMPT_BY_MODE` instructs the LLM to return a `ReflectionCritique` JSON:
- `quality_score` (int, 1–10): holistic score of the current output
- `issues`: list of `{field, issue, severity}` objects; `field` ∈ {explanation, diagram, notes, example}
- `revision_instructions`: a concise string instructing the revision call on what to fix

The critique prompt includes: `{topic}`, `{output_mode}`, `{current_output}` (the current
TeachingContent serialised as JSON). It does not include `{context}` to keep the critique
call within `TEACHING_REFLECTION_MAX_TOKENS` (default 512).

### Revision Prompt Design

`REVISION_PROMPT_BY_MODE` is structurally similar to `PROMPT_BY_MODE` but adds two
additional placeholders:
- `{current_output}`: the current TeachingContent JSON (so the LLM refines, not reinvents)
- `{revision_instructions}`: the `revision_instructions` string from the critique

The revision call uses the same token ceiling and model as the generation call
(`TEACHING_{MODE}_MAX_TOKENS`, `TEACHING_{MODE}_MODEL` or `TEACHING_MODEL`).
It returns JSON with the same structure as generation (explanation, diagram, notes, example).

### Agent Changes

Two new private methods added to `TeachingAgent` in `agent.py`:

- `_reflect(current_content, topic, output_mode, config, tokens_accumulator) → ReflectionCritique | None`
  Calls the LLM with `REFLECTION_PROMPT_BY_MODE[output_mode]`. Parses the response into
  `ReflectionCritique`. Returns `None` on any failure (parse error, LiteLLM exception).
  Appends the critique call's tokens to `tokens_accumulator`.

- `_revise(current_content, critique, topic, output_mode, context, config, tokens_accumulator) → TeachingContent | None`
  Calls the LLM with `REVISION_PROMPT_BY_MODE[output_mode]`. Passes the existing content
  plus `critique.revision_instructions`. Parses and validates the response (including Mermaid).
  Returns `None` on any failure. Appends the revision call's tokens to `tokens_accumulator`.

`run()` updated: after the initial generation and diagram validation, enter the reflection
loop. On each iteration, call `_reflect()`; if `None`, break and return current content.
Call `_revise()`; if `None`, break and return current content. Replace current content with
revision. After N iterations, assemble `TeachingAgentOutput` with `tokens_used` = sum of
all calls and `reflection_iterations` = number of completed cycles.

### Token Accounting

```
tokens_used = sum of completion_tokens over EVERY LLM call that returns
              (generation + each critique + each revision), per SC-013 —
              including a critique/revision whose response later fails to parse
              (the call still consumed tokens).
```

`metadata.tokens_used` always reflects total real consumption.
`metadata.reflection_iterations` counts only fully completed (critique + revision)
cycles and is independent of `tokens_used`. It is a new field (int, ge=0) added to
`TeachingMetadata` in `project/schemas.py`.

### Graceful Degradation

| Failure point | Recovery |
|---|---|
| Critique call fails (exception or parse error) | Break loop; return current content (initial or last revision) |
| Revision call fails (exception or parse error) | Break loop; return content from before this iteration |
| Revision produces invalid Mermaid (beginner) | Apply same retry-once + fallback-template rule as generation |
| Revision produces invalid Mermaid (inter/adv) | Set diagram to null in revised content |

In all cases: `status` remains `"ok"` if initial generation succeeded.
`reflection_iterations` reflects the number of **completed** (critique + revision both
succeeded) cycles, not attempted cycles.

### Reflection Quality Validation (SC-011)

The ≥80% quality-improvement target is validated **manually with a real model** (tasks.md
T046), not in the automated suite — the automated reflection tests use a monkeypatched
`call_llm` and assert control flow and token accounting, not output quality. A reviewer runs
each of the 9 topic/mode pairs with reflection on (N≥1) versus off (N=0) and scores both the
initial and reflected output on a fixed rubric:

- **Clarity** — easier to follow; jargon appropriate to the mode.
- **Structure adherence** — follows the mode's required section structure (FR-012/013/014).
- **Example completeness** — the worked example / code is correct and self-contained.

The reflected output must score **strictly higher** than the initial generation in ≥80% of
the pairs. A "lateral move" (no net change) counts as a non-improvement, per the probabilistic
assumption in `spec.md`.

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
| Field mapping | Handler maps inbound `user_prompt → topic`, `user_level → output_mode`, `rag_compiled → context`; core `run()` signature unchanged (FR-020) |
| `request_id` pass-through | Copied verbatim from `TeachingRequestEvent` to `TeachingCompletionEvent`; Teaching Agent never modifies it |
| `sid` pass-through | Copied verbatim from `TeachingRequestEvent`; used by backend to route completion event to the correct Socket.IO session; Teaching Agent never reads or validates its contents |
| `user_level` pass-through | Copied verbatim from `TeachingRequestEvent` to `TeachingCompletionEvent`; also used as `output_mode` for the core pipeline |
| Field mapping in handler | `user_prompt` → `topic`, `user_level` → `output_mode`, `rag_compiled` → `context` before calling `TeachingAgent.run()` |
| Always-publish rule | A `TeachingCompletionEvent` is published for every consumed message regardless of outcome; `content` is `""` (empty string) on failure; Planner is never left waiting |
| Malformed payload | Logged with `request_id` (or `"unknown"` if absent), skipped; poll loop continues without crashing |
| Topic bootstrap | `PlannerTopics.TEACHING` and `TeachingTopics.TEACHING_COMPLETE` registered in `project/topics.py`; both included in `get_all_topic_names()`; backend service creates topics at startup |
| Test isolation | All Kafka dependencies injectable via factory parameters; tests use Protocol-compatible fakes, no real Kafka required |

### Reflection Rules (FR-029 – FR-037, Phase 3)

| Rule | Detail |
|---|---|
| Default behavior | N=1 reflection iteration; configurable via `TEACHING_MAX_REFLECTION_ITERATIONS` |
| Disable reflection | Set `TEACHING_MAX_REFLECTION_ITERATIONS=0`; exact Phase 1 behavior restored |
| Per-mode override | `TEACHING_{MODE}_MAX_REFLECTION_ITERATIONS` takes precedence over global |
| Critique model | `TEACHING_REFLECTION_MODEL` → fallback `TEACHING_MODEL`; per-mode: `TEACHING_{MODE}_REFLECTION_MODEL` |
| Critique token ceiling | `TEACHING_REFLECTION_MAX_TOKENS` (default 512); critique must fit to be parseable |
| Revision token ceiling | Per-mode generation ceiling (`TEACHING_{MODE}_MAX_TOKENS`, default 4096) |
| Failure recovery | Any failure in critique or revision → return best available content; status stays `"ok"` |
| tokens_used | Sum of completion_tokens across all LLM calls (generation + all critiques + all revisions) |
| reflection_iterations | Number of completed (both critique and revision succeeded) cycles; 0 when disabled |
| Output schema | `TeachingAgentOutput` and `TeachingCompletionEvent` are unchanged; reflection is internal |
| Kafka publish | TeachingCompletionEvent published exactly once, after all reflection iterations |
| Mermaid rules | Applied identically to revised output as to initial output (FR-005, FR-006, FR-007) |

### Guardrail Architecture (FR-047 – FR-050, Phase 6)

```
TeachingAgent.run()
  Step 0: Guardrail check
          ├── chat_history non-empty?  → skip (always run full pipeline)
          ├── TEACHING_GUARDRAIL_ENABLED=false? → skip
          ├── GuardrailClassifier.classify(topic)
          │     ├── "greeting"       → token_callback("explanation", CANNED_GREETING) → return early
          │     ├── "off_topic"      → token_callback("explanation", CANNED_OFF_TOPIC) → return early
          │     ├── "unclear"        → token_callback("explanation", CANNED_UNCLEAR) → return early
          │     └── "valid_question" → fall through to Step 1
          └── classify() failure → fail-open → fall through to Step 1
  Step 1 → Step 8: existing pipeline (unchanged)
```

**Early return shape (non-valid_question)**:
```python
token_callback("explanation", canned_text)   # single call, not streamed
return TeachingAgentOutput(
    status="ok",
    output_mode=OutputMode(output_mode),
    content=None,               # already Optional in schema — no change needed
    metadata=TeachingMetadata(
        topic=topic,
        tokens_used=guardrail_tokens,
        model=guardrail_config.model,
    ),
), canned_text                  # raw_markdown = canned_text → TeachingCompletionEvent.content
```

**Canned responses**:

| Category | Canned text |
|---|---|
| `greeting` | `"Hi there! I'm your AI tutor. What topic would you like to learn about? I can explain concepts at beginner, intermediate, or advanced depth."` |
| `off_topic` | `"I'm a specialized learning assistant for educational topics. I'm not able to help with that, but I'd love to explain any concept you're curious about!"` |
| `unclear` | `"I'd be happy to help! Could you clarify what you'd like to learn? Try asking about a specific concept, algorithm, data structure, or topic."` |

**Guardrail LLM prompt design** (`GUARDRAIL_PROMPT`):
- Tight, deterministic prompt — no markdown, no section headers, no fences in the response.
- Returns `{"category": "...", "reason": "..."}` as a JSON object (uses `call_llm` with `response_format={"type": "json_object"}`).
- Uses `TEACHING_GUARDRAIL_MODEL` (falls back to `TEACHING_MODEL`); small/fast model recommended (e.g. `groq/llama-3.1-8b-instant`) since the call is purely classificatory.
- Token ceiling: low (e.g. 128 tokens) — classification is never more than a few words.
- On exception or JSON parse failure: returns `"valid_question"` (fail-open).

### Edge-Case Handling (spec "Edge Cases", FR-010)

| Edge case                                   | Handling                                                        |
|---------------------------------------------|-----------------------------------------------------------------|
| Single-word vs multi-word topic             | No special handling; passed verbatim to the prompt              |
| Empty `context`                             | Valid input; full response produced from general knowledge |
| Lengthy RAG-compiled `context`              | Input guard bounds context tokens (see Token-Ceiling Semantics) so the completion ceiling is unaffected; context is still treated as primary source |
| Same topic, different modes                 | Distinct prompt templates yield structurally distinct output (FR-004) |
| Ambiguous / out-of-scope topic              | Prompts instruct a structured best-effort response; never an error solely for ambiguity |
| LLM call fails or returns empty             | `status: "error"`, `tokens_used: 0`, no unhandled exception (FR-010) |
| Invalid generated Mermaid                   | Diagram set to null (intermediate/advanced) or retried/fallback (beginner); never returned invalid |
| Mermaid node labels contain special chars (`:`, `()`, `%`, etc.) | `sanitize_mermaid_labels()` in `helpers.py` auto-wraps unquoted labels in double quotes before `validate_mermaid()` runs; already-quoted labels untouched; applied on all diagram paths (initial, retry, revision) |
| User types a greeting instead of a learning question | Guardrail classifies as `greeting`; single canned welcome token emitted via `token_callback`; main pipeline not invoked (Phase 6) |
| User types off-topic or unclear message | Guardrail classifies and returns appropriate canned redirect or clarification; no main pipeline invocation (Phase 6) |
| Guardrail LLM call or JSON parse fails | Fail-open: system falls through to the full pipeline as if category were `valid_question`; learner is never silently dropped (Phase 6) |
| Follow-up query in active conversation (non-empty `chat_history`) | Guardrail step skipped entirely; full pipeline always runs (Phase 6) |
| LLM generates example with large input (e.g. `fibonacci(50)`) producing exhaustive computation trace | Prompt rule in all 3 mode templates (FR-051): use small input values (e.g. n ≤ 10 for recursive algorithms); never show full computation traces; demonstrate the concept, not the arithmetic |

### Guardrail Rules (FR-047 – FR-050, Phase 6)

| Rule | Detail |
|---|---|
| Trigger condition | `TEACHING_GUARDRAIL_ENABLED` is `true` (default) AND `chat_history` is empty |
| Skip condition | `chat_history` non-empty → guardrail bypassed; OR `TEACHING_GUARDRAIL_ENABLED=false` |
| Classification categories | `greeting`, `off_topic`, `unclear`, `valid_question` |
| LLM prompt | `GUARDRAIL_PROMPT` in `teaching_agent/prompts.py`; returns `{"category": "...", "reason": "..."}` |
| Model | `TEACHING_GUARDRAIL_MODEL` → fallback `TEACHING_MODEL`; small/fast model recommended |
| Token ceiling | Low (128 tokens) — classification response is always short |
| Failure behavior | Any exception or malformed JSON → return `"valid_question"` (fail-open) |
| Canned response delivery | Single `token_callback("explanation", canned_text)` call; no diagram/notes/example events |
| Return shape | `status="ok"`, `content=None`, `raw_markdown=canned_text` |
| Schema impact | Zero — `content=None` already schema-valid; handler uses `raw_markdown`; no new fields |

### RAG Context Priority (FR-036)

- The `context` field maps from `rag_compiled` in the Kafka event. It contains study material compiled by the RAG Agent from the user's course documents — **not** a prior conversation or session summary.
- When `context` is non-empty, LLM prompts MUST label it clearly as reference material (e.g., `"Reference material (compiled from course documents):"`) and include an explicit priority instruction immediately after: the LLM MUST ground its explanation in this material first and supplement with general knowledge only where the material is silent or incomplete.
- The trailing rule in each prompt template MUST reflect this: `"If no reference material is provided above, explain from general knowledge."` — replacing the old weak instructions ("briefly connect it", "build on it explicitly", "reference it where directly relevant") that treated context as an optional addendum rather than the primary source.
- When `context` is empty, the agent proceeds with general knowledge only; no special handling required.
- This was a correction to the original implementation which incorrectly labelled context as `"Prior session context:"` and gave it low-priority instructions.

### Multi-Turn Conversation Rules (FR-040 – FR-044, Phase 5)

| Rule | Detail |
|---|---|
| New input field | `chat_history: list[dict] = []` on `TeachingRequestEvent` and `TeachingAgentInput`; entries `{"role": "user"\|"assistant", "content": str}`, oldest→newest, excluding the current query |
| Message construction | `build_messages(prompt, chat_history)` returns `[*chat_history, {"role": "user", "content": prompt}]`; the structured per-mode prompt stays the final user message |
| No branch / no mode | No follow-up path, no conversational/Q&A output, no intent auto-detection; the 4-section structured pipeline runs every turn |
| Backward compatibility | Empty/absent `chat_history` → single user message → byte-for-byte the pre-Phase-5 behavior; existing callers/tests unaffected |
| Current-query placement | Current query stays in `user_prompt` (→ `topic`); `chat_history` holds prior turns only; Planner must not duplicate the current query |
| History size | Planner owns truncation/summarization; optional agent-side defensive cap via `TEACHING_MAX_HISTORY_TURNS` (keep most recent N), disabled by default |
| Unchanged downstream | `PROMPT_BY_MODE`, `StreamingFieldExtractor`, `parse_markdown_response`, `_resolve_diagram`, `TeachingContent` (notes required), reflection (N=0), the 4 streaming fields, and `ui_frontend/` are all unchanged |
| Optional prompt nudge | If quality testing shows drift between "continue chat" and "produce structured block", add one line per `PROMPT_BY_MODE` template; mechanism unchanged |

## Complexity Tracking

No constitution violations identified. Complexity is justified by the per-mode prompt
differentiation requirement (three separate prompt templates) and Mermaid validation,
both of which are direct spec requirements rather than architectural overhead.
