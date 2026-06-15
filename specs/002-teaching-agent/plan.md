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

Phase 3 introduces the **Reflection pattern** as an internal quality loop layered on top of
the Phase 1 pipeline. After initial generation, the agent issues a **critique** LLM call to
identify weaknesses per output field, then a **revision** LLM call to produce an improved
TeachingContent. This cycle repeats N times (configurable; default N=1; N=0 restores
single-pass behavior). The output schema and Kafka contract are unchanged — reflection is
invisible to all external consumers. (The Phase 3 spec items — US6, FR-029–FR-037 — are a
proposal pending team sign-off; see the proposal section in `spec.md`.)

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pydantic v2, litellm>=1.40.0, pytest>=8.0.0 (no new packages beyond existing requirements.txt)
**Storage**: N/A (pure in-memory; no file I/O beyond CLI input for development)
**Testing**: pytest
**Target Platform**: Linux runtime (local dev and container-ready execution)
**Project Type**: Agent module/library within a multi-agent backend
**Performance Goals**:
- Reflection disabled (N=0): beginner ≤ 5s, intermediate ≤ 10s, advanced ≤ 20s on developer hardware with a fast-endpoint model
- 1 reflection iteration (default): beginner ≤ 15s, intermediate ≤ 25s, advanced ≤ 45s on developer hardware with a fast-endpoint model
- Wall-clock must be measured at both settings; regression vs. Phase 1 baseline is expected and documented
**Constraints**: Synchronous execution only; per-mode token ceilings enforced at LiteLLM call level via `TEACHING_{MODE}_MAX_TOKENS` env vars (default 4096 each); per-mode model, API key, temperature, and effort also configurable via `TEACHING_{MODE}_MODEL` / `TEACHING_{MODE}_API_KEY` / `TEACHING_{MODE}_TEMPERATURE` / `TEACHING_{MODE}_EFFORT` with fallback to shared `TEACHING_MODEL` / `TEACHING_API_KEY` / `TEACHING_TEMPERATURE`; effort (`low | medium | high`) maps to `output_config={"effort": value}` for Claude 4.6 models only, silently skipped for all others; Mermaid validation required before returning diagram; JSON output only; no LangGraph; reflection iterations controlled by `TEACHING_MAX_REFLECTION_ITERATIONS` (global, default 1; 0 disables) and per-mode `TEACHING_{MODE}_MAX_REFLECTION_ITERATIONS` override; critique model configurable via `TEACHING_REFLECTION_MODEL` (falls back to `TEACHING_MODEL`); per-mode `TEACHING_{MODE}_REFLECTION_MODEL` also supported; critique token ceiling `TEACHING_REFLECTION_MAX_TOKENS` (default 512); revision reuses per-mode generation ceiling; `metadata.tokens_used` sums all LLM calls in the lifecycle; `metadata.reflection_iterations` reports completed cycles
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
│                        # Phase 3: ReflectionCritique (internal; not in output events)
└── topics.py            # Phase 2: Add TEACHING to PlannerTopics; add TeachingTopics enum
                         #           (TEACHING_COMPLETE only); include in get_all_topic_names()

teaching_agent/
├── __init__.py
├── agent.py             # TeachingAgent class: run(), _resolve_diagram(),
│                        #                      _reflect(), _revise()
│                        #                      reflection loop (N iterations)
│                        #                      [Phase 1 core unchanged; reflection added in Phase 3]
├── config.py            # LLMConfig dataclass (add effort, reflection_max_tokens fields)
│                        # get_llm_config(output_mode) — generation config
│                        # get_reflection_config(output_mode) — critique config (Phase 3):
│                        #   TEACHING_REFLECTION_MODEL, TEACHING_{MODE}_REFLECTION_MODEL,
│                        #   TEACHING_REFLECTION_MAX_TOKENS
│                        # get_max_reflection_iterations(output_mode) — iteration count (Phase 3):
│                        #   TEACHING_{MODE}_MAX_REFLECTION_ITERATIONS →
│                        #   TEACHING_MAX_REFLECTION_ITERATIONS → default 1
├── llm_client.py        # call_llm(messages, config) → (str, int); provider-agnostic via LiteLLM
├── prompts.py           # BEGINNER/INTERMEDIATE/ADVANCED_PROMPT (generation)
│                        # REFLECTION_PROMPT_BY_MODE (critique — Phase 3)
│                        # REVISION_PROMPT_BY_MODE (revision — Phase 3)
├── validators.py        # validate_mermaid(diagram: str) → bool; regex-based structural check
├── helpers.py           # parse_llm_response(raw: str) → dict; build_error_output()
├── kafka.py             # Phase 2: Protocol types (KafkaConsumerProtocol, KafkaProducerProtocol)
│                        #           factory functions (create_consumer, create_producer)
│                        #           topic helpers (consumer_subscribe_teaching, publish_teaching_complete)
├── handlers.py          # Phase 2: TeachingRequestEventHandler — parse event → run agent →
│                        #           build completion event → publish; injectable dependencies
├── worker.py            # Phase 2: TeachingWorker — lifecycle (start/stop/get_state),
│                        #           background poll loop; process_consumer_batch() function
└── tests/
    ├── __init__.py
    ├── test_teaching_agent.py       # Phase 1 tests (real LLM calls)
    ├── test_kafka_integration.py    # Phase 2: handler + publish tests (fake Kafka)
    ├── test_worker_runtime.py       # Phase 2: worker lifecycle tests (fake Kafka)
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

- `_reflect(current_content, topic, output_mode, config) → ReflectionCritique | None`
  Calls the LLM with `REFLECTION_PROMPT_BY_MODE[output_mode]`. Parses the response into
  `ReflectionCritique`. Returns `None` on any failure (parse error, LiteLLM exception).
  Adds critique tokens to the running `tokens_used` total.

- `_revise(current_content, critique, topic, output_mode, context, config) → TeachingContent | None`
  Calls the LLM with `REVISION_PROMPT_BY_MODE[output_mode]`. Passes the existing content
  plus `critique.revision_instructions`. Parses and validates the response (including Mermaid).
  Returns `None` on any failure. Adds revision tokens to the running `tokens_used` total.

`run()` updated: after the initial generation and diagram validation, enter the reflection
loop. On each iteration, call `_reflect()`; if `None`, break and return current content.
Call `_revise()`; if `None`, break and return current content. Replace current content with
revision. After N iterations, assemble `TeachingAgentOutput` with `tokens_used` = sum of
all calls and `reflection_iterations` = number of completed cycles.

### Token Accounting

```
tokens_used = generation_tokens
            + sum(critique_tokens_i + revision_tokens_i  for i in completed_cycles)
```

`metadata.tokens_used` always reflects total real consumption.
`metadata.reflection_iterations` is a new field (int, ge=0) — add to `TeachingMetadata`
in `project/schemas.py`.

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

### Kafka Event Rules (FR-019 – FR-028)

| Rule | Detail |
|---|---|
| Inbound topic | `"teaching"` — consumed by `TeachingWorker`; published by Planner Agent |
| Outbound topic | `"teaching-complete"` — published by `TeachingRequestEventHandler` |
| Field mapping | Handler maps inbound `user_prompt → topic`, `user_level → output_mode`, `rag_compiled → context`; core `run()` signature unchanged (FR-020) |
| `request_id` pass-through | Copied verbatim from `TeachingRequestEvent` to `TeachingCompletionEvent`; Teaching Agent never modifies it |
| `sid` pass-through | Copied verbatim; Teaching Agent never reads or validates its contents |
| Always-publish rule | A `TeachingCompletionEvent` is published for every consumed message regardless of outcome (error → empty `content`); Planner is never left waiting |
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
