# Implementation Plan: Planner Agent

**Branch**: `planner-code` | **Date**: 2026-06-15 | **Spec**: `/specs/000-planner-agent/spec.md`
**Input**: Feature specification from `/specs/000-planner-agent/spec.md`

## Summary

Implement the Planner Agent as the **central orchestrator** of the AI Tutor multi-agent system.
The Planner runs as a long-lived Kafka consumer process. It receives user queries from the
`init-planner` topic, assesses the learner's proficiency level (naive / intermediate / advanced)
using LLM reasoning, optionally engages the learner in a single-turn clarification via
`clarify-user-level`, rewrites the query for downstream quality, decomposes the task into a
`LearningPlan`, and dispatches RAG / Teaching / Quiz agents in parallel by producing typed JSON
messages to their respective Kafka topics.

After dispatch, the Planner consumes agent responses from `rag-complete`, `material-compiled`, and
`quiz-complete`, validates each response for completeness and quality, retries invalid responses
up to MAX_RETRIES, and publishes a `PlannerResponse` to the `planner-response` topic. The response
passes through the teaching content directly — no LLM synthesis step is performed.

The LangGraph StateGraph orchestrates the internal pipeline. LiteLLM provides the unified LLM
interface. All configuration (Kafka brokers, model names, thresholds, timeouts) is
environment-variable-driven, consistent with the RAG Agent pattern.

**Removed from initial design:** HyDE (Hypothetical Document Embedding) generation and the
synthesis node have been removed. Query rewrite now always runs to improve downstream agent
query quality (FR-022). All exceptions are surfaced to `state["errors"]` and logged — no silent
failures (FR-023).

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pydantic v2, LangGraph, LiteLLM, confluent-kafka-python, pytest
**Storage**: N/A (stateless per-request; no persistence in v1)
**Testing**: pytest with in-memory Kafka mock
**Target Platform**: Linux runtime (local dev and container-ready execution)
**Project Type**: Long-lived consumer/producer agent within a Kafka-based multi-agent backend
**Performance Goals**: End-to-end orchestration (consume `init-planner` → produce `planner-response`)
within ≤60 seconds under standard LLM and Kafka latency; SIMPLE path (no clarification, 2 agents)
targets ≤30 seconds
**Constraints**: Synchronous LangGraph node execution; environment-variable LLM and Kafka config;
MAX_RETRIES=3 per agent; agent response timeout=120s; MIN_CONTENT_LENGTH=100 chars
**Scale/Scope**: One Planner process handles one request at a time per consumer group partition;
horizontal scaling via Kafka consumer group for concurrency; initial registry supports 3 agent types

## Project Structure

### Documentation (this feature)

```text
specs/000-planner-agent/
├── plan.md              ← this file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── planner-agent-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
project/
└── schemas.py           ← shared; PlannerMessage, PlannerResponse, LearnerLevel,
                            LearningPlan, LearnerProfile, RAGAgentInput, RAGAgentOutput,
                            TeachingAgentInput, TeachingAgentOutput,
                            QuizAgentInput, QuizAgentOutput,
                            ClarifyUserLevelMessage, UserClarificationResponse

planner_agent/
├── __init__.py
├── agent.py             ← LangGraph StateGraph; 11-node pipeline
├── registry.py          ← AgentRegistry, AgentRegistryEntry, default registrations
│                           (each entry: agent_type, produce_topic, consume_topic,
│                            intent_description, input_contract_builder)
├── classifier.py        ← detect_complexity(), assess_learner_level()
├── rewriter.py          ← rewrite_query() LLM call — always applied pre-dispatch
├── guardrails.py        ← check_guardrails() → ALLOWED | WARN | BLOCKED
├── payload_builder.py   ← build_payload(entry, planner_state) per agent type
├── validator.py         ← validate_query(), validate_agent_response()
│                           checks: non-empty, MIN_CONTENT_LENGTH, request_id match,
│                           schema conformance, malformed JSON detection
├── kafka_client.py      ← KafkaProducer / KafkaConsumer wrappers (confluent-kafka)
│                           produce(topic, message), consume(topics, timeout)
│                           deduplication by request_id + agent_type
├── llm_client.py        ← call_llm(messages, config) — same pattern as rag_agent
├── prompts.py           ← LEARNER_LEVEL_PROMPT, CLARIFICATION_PROMPT,
│                           QUERY_REWRITE_PROMPT, GUARDRAIL_PROMPT, LEARNING_PLAN_PROMPT
├── config.py            ← PlannerConfig; env var loaders for LLM + Kafka
└── tests/
    ├── __init__.py
    ├── inputs/
    │   ├── sample_input.json           ← valid PlannerMessage fixture
    │   ├── sample_queries.json         ← labeled queries for level + routing accuracy
    │   ├── mock_rag_response.json      ← valid RAGAgentOutput fixture
    │   ├── mock_teaching_response.json ← valid TeachingAgentOutput fixture
    │   └── mock_quiz_response.json     ← valid QuizAgentOutput fixture
    └── test_planner_agent.py
```

**Removed files:** `hyde.py` (HyDE generation) and `synthesizer.py` (response synthesis) have been
deleted. Their prompts (HYDE_PROMPT, SYNTHESIS_PROMPT) have been removed from `prompts.py`.

## Kafka Topics Architecture

### Topic Map

| Topic | Direction | Producer | Consumer | Message Schema |
|-------|-----------|----------|----------|---------------|
| `init-planner` | → Planner | Application / UI layer | Planner Agent | `PlannerMessage` |
| `clarify-user-level` | ← Planner | Planner Agent | UI / session layer | `ClarifyUserLevelMessage` |
| `user-clarification-response` | → Planner | UI / session layer | Planner Agent | `UserClarificationResponse` |
| `rag` | ← Planner | Planner Agent | RAG Agent | `RAGAgentInput` |
| `teaching` | ← Planner | Planner Agent | Teaching Agent | `TeachingAgentInput` |
| `quiz` | ← Planner | Planner Agent | Quiz Agent | `QuizAgentInput` |
| `rag-complete` | → Planner | RAG Agent | Planner Agent | `RAGAgentOutput` |
| `material-compiled` | → Planner | Teaching Agent | Planner Agent | `TeachingAgentOutput` |
| `quiz-complete` | → Planner | Quiz Agent | Planner Agent | `QuizAgentOutput` |
| `planner-response` | ← Planner | Planner Agent | Application / UI layer | `PlannerResponse` |

### Kafka Configuration (environment variables)

```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONSUMER_GROUP_ID=planner-agent-group
KAFKA_AUTO_OFFSET_RESET=earliest
KAFKA_ENABLE_AUTO_COMMIT=false          # manual commit after successful processing
KAFKA_SESSION_TIMEOUT_MS=45000
KAFKA_MAX_POLL_INTERVAL_MS=300000
AGENT_RESPONSE_TIMEOUT_SEC=120          # per-agent wait timeout
```

---

## LangGraph Pipeline Design (11 nodes)

### Node Responsibilities

| # | Node | LLM call? | Kafka I/O | Don't-fail-silently |
|---|------|-----------|-----------|---------------------|
| 1 | `validate_query` | No | Consume: `init-planner` | Errors → state["errors"] |
| 2 | `assess_learner_level` | Yes (LEARNER_LEVEL_PROMPT) | — | Exception → log ERROR + errors |
| 3 | `produce_clarification` | Yes (CLARIFICATION_PROMPT) | Produce: `clarify-user-level` | Exception → log WARNING + errors |
| 4 | `wait_for_clarification` | No | Consume: `user-clarification-response` | Timeout → log WARNING + errors |
| 5 | `check_guardrails` | Yes (GUARDRAIL_PROMPT) | — | Exception → log ERROR + errors |
| 6 | `rewrite_query` | Yes (QUERY_REWRITE_PROMPT) | — | Exception → log WARNING + errors; use original |
| 7 | `plan_learning_path` | Yes (LEARNING_PLAN_PROMPT) | — | Exception → log WARNING + errors; use default plan |
| 8 | `dispatch_agents` | No | Produce: `rag`, `teaching`, `quiz` (parallel) | Exception per agent → log ERROR + errors |
| 9 | `collect_responses` | No | Consume: `rag-complete`, `material-compiled`, `quiz-complete` | Timeout → log WARNING + errors |
| 10 | `validate_responses` | No | — | Invalid → log WARNING + errors; schedule retry |
| 11 | `emit_result` | No | Produce: `planner-response` | Exception → log ERROR |

> **Note:** `retry_agent` is an intermediate state (not a standalone node) that re-dispatches
> invalid agents before cycling back through `collect_responses` → `validate_responses`.

### Conditional Edge Logic

```
validate_query
  → emit_result[failed]          if schema invalid / empty query / bad UUID
  → assess_learner_level         if valid

assess_learner_level
  → produce_clarification        if confidence < threshold AND not already clarified
  → check_guardrails             if confidence ≥ threshold OR already clarified

produce_clarification → wait_for_clarification

wait_for_clarification → check_guardrails
  (level updated from response, or defaulted to intermediate on timeout)

check_guardrails
  → emit_result[failed]          if BLOCKED
  → rewrite_query                if ALLOWED or WARN (always rewrite for downstream quality)

rewrite_query → plan_learning_path
  (rewritten_query forwarded to all agent payloads; original used on failure + error recorded)

plan_learning_path → dispatch_agents

dispatch_agents → collect_responses

collect_responses → validate_responses
  (all expected responses received OR timeout)

validate_responses
  → retry_agent                  for each invalid response (if retries < MAX_RETRIES)
  → emit_result                  when all valid OR max retries exhausted

retry_agent → collect_responses  (cycle for retry loop)

emit_result → END
```

### LLM Call Budget per Path

| Path | Nodes with LLM calls | Max calls |
|------|---------------------|-----------|
| SIMPLE, 1 agent, clear level | assess_level, rewrite, plan | 3 |
| SIMPLE, 2 agents, clear level | assess_level, rewrite, plan | 3 |
| COMPLEX, RAG + Teaching | assess_level, guardrail, rewrite, plan | 4 |
| With clarification round-trip | + clarification question gen | +1 |
| With 1 agent retry | + re-plan (rewrite already done) | 0 extra |

**HyDE removed**: no HyDE LLM call. **Synthesis removed**: no synthesis LLM call.

---

## Query Rewrite Design (FR-022)

Query rewriting always runs after guardrails pass. The QUERY_REWRITE_PROMPT instructs the LLM to:
- Return the query unchanged if it is already clear and specific
- Expand abbreviations and resolve vague references
- Collapse multi-intent into the primary intent
- Preserve learner intent — topic and scope must not change

The `rewritten_query` (or original on failure) is stored in `PlannerState` and forwarded
verbatim as `user_query` / `user_prompt` in every agent dispatch payload. This ensures:
- RAG agent retrieves content relevant to the clearest possible query expression
- Teaching agent explains the intended concept, not an ambiguous abbreviation
- Quiz agent generates questions for the correct topic scope

On LLM failure during rewrite:
- `logger.warning("query_rewrite_failed ...")` is emitted with `request_id` and exception
- Original query is used for dispatch
- `state["errors"].append(...)` records the failure so it appears in `PlannerResponse.errors`

---

## Don't-Fail-Silently Design (FR-023)

Every node in the pipeline follows this pattern for exception handling:

```python
try:
    result = do_something(...)
except Exception as exc:
    logger.error("stage_name_failed request_id=%s error=%s", request_id, exc)
    state["errors"].append(f"Stage name failed: {exc}")
    result = fallback_value  # safe default where applicable
```

This ensures:
- All failures appear in structured logs with `request_id` for correlation
- All failures accumulate in `state["errors"]` and surface in `PlannerResponse.errors`
- `_derive_status` uses the errors list to decide `complete` vs `partial` vs `failed`
- No exception path produces a `status=complete` response while hiding internal failures

---

## Response Validation Design

Every agent response is validated in `validator.py` before reaching `emit_result`:

| Check | Rule | On failure |
|-------|------|-----------|
| Schema conformance | Response parses against pydantic model | Retry dispatch |
| Non-empty primary field | `compiled_material` / `teaching_content` / `questions` not empty/null | Retry dispatch |
| MIN_CONTENT_LENGTH | Primary field ≥ 100 characters | Flag `vague`, retry with augmented prompt |
| request_id match | Response `request_id` == dispatched `request_id` | Discard (stale/misrouted) |
| Status check | `status` != `failed` | Mark agent as failed; no retry |
| JSON integrity | Valid UTF-8 JSON, no truncation markers | Retry dispatch |

Retry prompt augmentation added to agent payloads:
```
[RETRY {n}/{MAX}] Previous response was rejected: {reason}.
Please provide a more complete and detailed response (minimum 100 characters).
```

---

## emit_result Design (No Synthesis)

The `emit_result` node builds `PlannerResponse` directly from collected `agent_responses`:

- `synthesized_content` ← Teaching Agent's `teaching_content` (pass-through)
- `study_material` ← RAG Agent's `compiled_material`
- `quiz` ← Quiz Agent's `questions` list

`_derive_status` is determined by:
1. `failed` if input invalid or guardrail blocked
2. `failed` if no agents were dispatched
3. `complete` if all dispatched agents responded with valid content and no errors
4. `partial` if some agents responded with valid content but errors exist or not all responded
5. `failed` if no agent produced valid content

---

## System Architecture Overview

```
╔══════════════════════════════════════════════════════════════════╗
║                    PLANNER AGENT  (Orchestrator)                 ║
║                    planner_agent/agent.py  ─  LangGraph          ║
║                                                                  ║
║  [1] validate_query       ← schema, UUID, non-empty, version     ║
║       │ invalid ──────────────────────────────────► emit_result  ║
║       │ valid                                                     ║
║       ▼                                                          ║
║  [2] assess_learner_level  ◄──── LiteLLM                        ║
║       LEARNER_LEVEL_PROMPT                                       ║
║       naive │ intermediate │ advanced  +  confidence             ║
║       │ conf < threshold ──► [3] produce_clarification           ║
║       │                          [4] wait_for_clarification      ║
║       │ conf ≥ threshold ◄────────────────────────────           ║
║       ▼                                                          ║
║  [5] check_guardrails  ◄──── LiteLLM (COMPLEX path)             ║
║       GUARDRAIL_PROMPT                                           ║
║       │ BLOCKED ──────────────────────────────────► emit_result  ║
║       │ ALLOWED / WARN                                           ║
║       ▼                                                          ║
║  [6] rewrite_query  ◄──── LiteLLM  (ALWAYS)                     ║
║       QUERY_REWRITE_PROMPT                                       ║
║       "neural nets?" → "Explain the fundamentals of             ║
║        neural networks for a beginner"                          ║
║       Rewritten query forwarded to ALL downstream agents         ║
║       Failure: use original + log WARNING + add to errors        ║
║       ▼                                                          ║
║  [7] plan_learning_path  ◄──── LiteLLM                          ║
║       LEARNING_PLAN_PROMPT                                       ║
║       → LearningPlan { required_agents, parallel_groups,         ║
║           depth, objective }                                     ║
║       ▼                                                          ║
║  [8] dispatch_agents  (PARALLEL)                                 ║
║    Kafka produce → rag       (RAGAgentInput)                     ║
║    Kafka produce → teaching  (TeachingAgentInput)                ║
║    Kafka produce → quiz      (QuizAgentInput) [optional]         ║
║    Each failure → log ERROR + add to errors                      ║
║       ▼                                                          ║
║  [9] collect_responses                                           ║
║    Kafka consume ← rag-complete       (RAGAgentOutput)           ║
║    Kafka consume ← material-compiled  (TeachingOutput)           ║
║    Kafka consume ← quiz-complete      (QuizAgentOutput)          ║
║    Timeout → log WARNING + add to errors                         ║
║       ▼                                                          ║
║  [10] validate_responses  (validator.py)                         ║
║    ✓ schema conformance, non-empty field, MIN_CONTENT_LENGTH     ║
║    ✓ request_id match, status != failed, valid UTF-8 JSON        ║
║    invalid + retries left ──► retry_agent ──► [9]               ║
║    invalid + max retries  ──► mark partial + add to errors       ║
║       ▼                                                          ║
║  [11] emit_result                                                ║
║    synthesized_content ← teaching_content (pass-through)         ║
║    study_material ← compiled_material (RAG)                      ║
║    quiz ← questions list (Quiz)                                  ║
║    PlannerResponse { complete │ partial │ failed }               ║
╚══════════════════════════════════════════════════════════════════╝
```

## Complexity Tracking

| Element | Why Needed |
|---------|-----------|
| Kafka async I/O | Decouples agent lifecycle; enables parallel dispatch |
| LangGraph StateGraph (11 nodes) | Explicit conditional branching with observability and testability |
| Learner level assessment | Core personalisation; isolated to `classifier.py` |
| Multi-turn clarification (Kafka loop) | Required for ambiguous queries; bounded to 1 clarification |
| Query rewrite (always-on) | Improves retrieval and explanation quality for all downstream agents; isolated to `rewriter.py` |
| Response validation + retry loop | Agent responses can be empty or malformed; bounded retries (max 3) |
| Don't-fail-silently pattern | All exceptions logged and surfaced to PlannerResponse.errors |
| Guardrails node | Educational-scope safety; COMPLEX path only; isolated to `guardrails.py` |

**Removed complexity:**
- HyDE augmentation: removed; query rewrite provides sufficient downstream query quality improvement without an extra LLM call
- Synthesis node: removed; teaching agent produces level-calibrated content directly; planner passes it through
