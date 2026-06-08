# Implementation Plan: Planner Agent

**Branch**: `000-build-planner-agent` | **Date**: 2026-05-30 | **Spec**: `/specs/000-planner-agent/spec.md`
**Input**: Feature specification from `/specs/000-planner-agent/spec.md`

## Summary

Implement the Planner Agent as the **central async orchestrator** of the AI Tutor multi-agent system.
The Planner runs as a long-lived Kafka consumer process. It receives user queries from the
`init-planner` topic, assesses the learner's proficiency level (naive / intermediate / advanced)
using LLM reasoning, optionally engages the learner in a single-turn clarification via
`clarify-user-level`, decomposes the task into a `LearningPlan`, and dispatches RAG / Teaching /
Quiz agents in parallel by producing typed JSON messages to their respective Kafka topics.

After dispatch, the Planner consumes agent responses from `rag-complete`, `material-compiled`, and
`quiz-complete`, validates each response for completeness and quality, retries invalid responses
up to MAX_RETRIES, and synthesizes a coherent final answer calibrated to the learner's level.
The synthesized `PlannerResponse` is published to the `planner-response` topic.

The LangGraph StateGraph orchestrates the internal pipeline. LiteLLM provides the unified LLM
interface. All configuration (Kafka brokers, model names, thresholds, timeouts) is
environment-variable-driven, consistent with the RAG Agent pattern.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pydantic v2, LangGraph, LiteLLM, confluent-kafka-python, pytest
**Storage**: N/A (stateless per-request; no persistence in v1; Redis session store planned for v2)
**Testing**: pytest (with Kafka mock via testcontainers or in-memory mock producer/consumer)
**Target Platform**: Linux runtime (local dev and container-ready execution)
**Project Type**: Long-lived async consumer/producer agent within a Kafka-based multi-agent backend
**Performance Goals**: End-to-end orchestration (consume `init-planner` → produce `planner-response`)
within ≤60 seconds under standard LLM and Kafka latency; SIMPLE path (no clarification, 2 agents)
targets ≤30 seconds
**Constraints**: Async Kafka I/O; synchronous LangGraph node execution within each processing cycle;
environment-variable LLM and Kafka config; MAX_RETRIES=3 per agent; agent response timeout=120s;
MIN_CONTENT_LENGTH=100 chars
**Scale/Scope**: One Planner process handles one request at a time per consumer group partition;
horizontal scaling via Kafka consumer group for concurrency; initial registry supports 3 agent types

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate Review (Pre-Research)

- **Code Quality Gate**: PASS. Module boundaries are explicit: `agent.py` (graph),
  `registry.py` (extension point), `classifier.py` (complexity + intent), `rewriter.py`
  (query rewriting), `hyde.py` (HyDE generation), `guardrails.py` (safety check),
  `payload_builder.py` (contract construction), `llm_client.py`, `prompts.py`, `config.py`.
  Each module has a single responsibility. No cross-agent imports.
- **Testing Gate**: PASS. Tests planned for routing accuracy, ambiguous handling, guardrail paths,
  HyDE application, query rewriting, registry extensibility, schema validation, retry loop, and
  latency budget.
- **UX Consistency Gate**: PASS. PlannerOutput contract is stable and field-consistent across all
  status values (routed / ambiguous / failed). Errors list is always present. Original user_query
  is always mirrored verbatim.
- **Performance Gate**: PASS. ≤10s budget defined; SIMPLE fast path targets ≤5s. LLM call count
  per path is bounded: SIMPLE=1 call, COMPLEX=2–3 calls, retry path adds ≤3 more.
- **Maintainability Gate**: PASS. Agent registry is the sole extension point. Prompts are
  centralized. Config is env-driven. LangGraph graph topology is readable from `agent.py` alone.

### Post-Design Gate Review (After Phase 1 Artifacts)

- **Code Quality Gate**: PASS. Data model and contracts define all entities; no ambiguity in
  field ownership. Contract explicitly separates internal `PlannerState` from external
  `PlannerOutput`.
- **Testing Gate**: PASS. Quickstart defines all test commands and expected outcomes. Routing
  accuracy test uses labeled query fixture for objective SC-002 measurement.
- **UX Consistency Gate**: PASS. Contract enforces verbatim request mirroring and consistent
  `errors` presence. HyDE augmentation is transparent to callers (flagged but does not alter
  original `user_query`).
- **Performance Gate**: PASS. Latency budget test (`test_routing_latency_budget`) validates ≤10s
  for sample input. LLM call count per path is bounded and documented.
- **Maintainability Gate**: PASS. `AgentRegistryEntry.input_contract_builder` callable pattern
  ensures new agents extend, not modify, existing code.

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
└── tasks.md             ← generated by /speckit-tasks
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
├── agent.py             ← LangGraph StateGraph; main consumer loop run_planner()
├── registry.py          ← AgentRegistry, AgentRegistryEntry, default registrations
│                           (each entry: agent_type, produce_topic, consume_topic,
│                            intent_description, supports_hyde, input_contract_builder)
├── classifier.py        ← detect_complexity(), classify_intent(), assess_learner_level()
├── rewriter.py          ← rewrite_query() LLM call
├── hyde.py              ← generate_hyde_doc() LLM call
├── guardrails.py        ← check_guardrails() → ALLOWED | WARN | BLOCKED
├── payload_builder.py   ← build_payload(entry, planner_state) per agent type
├── validator.py         ← validate_query(), validate_agent_response()
│                           checks: non-empty, MIN_CONTENT_LENGTH, request_id match,
│                           schema conformance, malformed JSON detection
├── synthesizer.py       ← synthesize_response() — combines agent outputs, calibrates
│                           to learner_level, produces synthesized_content
├── kafka_client.py      ← KafkaProducer / KafkaConsumer wrappers (confluent-kafka)
│                           produce(topic, message), consume(topics, timeout)
│                           deduplication by request_id + agent_type
├── llm_client.py        ← call_llm(messages, config) — same pattern as rag_agent
├── prompts.py           ← LEARNER_LEVEL_PROMPT, INTENT_CLASSIFICATION_PROMPT,
│                           QUERY_REWRITE_PROMPT, GUARDRAIL_PROMPT, HYDE_PROMPT,
│                           LEARNING_PLAN_PROMPT, SYNTHESIS_PROMPT
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

**Structure Decision**: Single Python agent module following the established `rag_agent/` pattern.
Shared schemas at repository root (`project/schemas.py`). Each responsibility is an independent
module file to support parallel development across team members.

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

### Message Correlation and Deduplication

- Every produced message carries the originating `request_id`.
- `kafka_client.py` maintains an in-memory `seen_messages: set[tuple[str,str]]` of
  `(request_id, agent_type)` to deduplicate duplicate Kafka deliveries within a session.
- Stale messages whose `request_id` does not match any active request are logged and discarded.

---

## LangGraph Pipeline Design

### Node Responsibilities

| Node | Trigger condition | LLM call? | Kafka I/O |
|------|------------------|-----------|----------|
| `validate_query` | Always | No | Consume: `init-planner` |
| `assess_learner_level` | Valid query | Yes (LEARNER_LEVEL_PROMPT) | — |
| `produce_clarification` | level_confidence < 0.65 AND not already clarified | No | Produce: `clarify-user-level` |
| `wait_for_clarification` | Clarification produced | No | Consume: `user-clarification-response` (timeout 120s) |
| `check_guardrails` | After level known | Yes (GUARDRAIL_PROMPT) | — |
| `rewrite_query` | COMPLEX or word_count < 5 | Yes (QUERY_REWRITE_PROMPT) | — |
| `plan_learning_path` | After rewrite/level | Yes (LEARNING_PLAN_PROMPT) | — |
| `generate_hyde_doc` | RAG in plan AND (short query OR conf < 0.85) | Yes (HYDE_PROMPT) | — |
| `dispatch_agents` | Learning plan ready | No | Produce: `rag`, `teaching`, `quiz` (parallel) |
| `collect_responses` | After dispatch | No | Consume: `rag-complete`, `material-compiled`, `quiz-complete` |
| `validate_responses` | Responses collected | No | — |
| `retry_agent` | Response invalid AND retries < MAX_RETRIES | No | Re-produce to agent topic |
| `synthesize_response` | All valid responses collected | Yes (SYNTHESIS_PROMPT) | — |
| `emit_result` | Synthesis complete | No | Produce: `planner-response` |

### Conditional Edge Logic

```
validate_query
  → emit_result[failed]          if schema invalid / empty query / bad UUID
  → assess_learner_level         if valid

assess_learner_level
  → produce_clarification        if confidence < 0.65 AND first time in session
  → check_guardrails             if confidence ≥ 0.65 OR already clarified

produce_clarification → wait_for_clarification

wait_for_clarification
  → check_guardrails             after response received (level updated)
  → check_guardrails             after timeout (level defaults to intermediate)

check_guardrails
  → emit_result[failed]          if BLOCKED
  → rewrite_query                if ALLOWED/WARN AND (COMPLEX or short)
  → plan_learning_path           if ALLOWED/WARN AND SIMPLE

rewrite_query → plan_learning_path

plan_learning_path
  → generate_hyde_doc            if RAG_AGENT in plan AND (short OR conf < 0.85)
  → dispatch_agents              otherwise

generate_hyde_doc → dispatch_agents

dispatch_agents → collect_responses

collect_responses
  → validate_responses           when all expected responses received OR timeout

validate_responses
  → retry_agent                  for each invalid response (if retries < MAX_RETRIES)
  → synthesize_response          when all valid OR max retries exhausted

retry_agent → dispatch_agents[single agent re-dispatch] → collect_responses

synthesize_response → emit_result[complete | partial]
```

### LLM Call Budget per Path

| Path | Nodes with LLM calls | Max calls |
|------|---------------------|-----------|
| SIMPLE, 1 agent, clear level | assess_level, plan | 2 |
| SIMPLE, 2 agents, clear level | assess_level, plan, synthesize | 3 |
| COMPLEX, RAG + Teaching + HyDE | assess_level, guardrail, rewrite, plan, hyde, synthesize | 6 |
| With clarification round-trip | + clarification question gen | +1 |
| With 1 agent retry (re-plan) | + rewrite, synthesize | +2 |

---

## Response Validation Design

Every agent response is validated in `validator.py` before reaching synthesis:

| Check | Rule | On failure |
|-------|------|-----------|
| Schema conformance | Response parses against pydantic model | Retry dispatch |
| Non-empty primary field | `compiled_material` / `teaching_content` / `questions` not empty/null | Retry dispatch |
| MIN_CONTENT_LENGTH | Primary field ≥ 100 characters | Flag `vague`, retry with augmented prompt |
| request_id match | Response `request_id` == dispatched `request_id` | Discard (stale/misrouted) |
| Status check | `status` != `failed` | Mark agent as failed; no retry |
| JSON integrity | Valid UTF-8 JSON, no truncation markers | Retry dispatch |

Retry prompt augmentation adds to the original prompt:
```
[RETRY {n}/{MAX}] Previous response was rejected: {reason}.
Please provide a more complete and detailed response (minimum 100 characters).
```

---

## System Architecture Overview

End-to-end architecture: user query → Kafka → Planner Orchestrator → parallel agent dispatch → response collection → synthesis → Kafka.

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                              AI TUTOR SYSTEM                                         ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

  ┌──────────────────────────────────────────────────────────────────────────┐
  │                            USER / APPLICATION LAYER                      │
  │                                                                          │
  │   Learner types a natural language query                                 │
  │   e.g. "Explain gradient descent from chapter 3"  (naive learner)        │
  │         "Derive backprop equations for MLP"        (advanced learner)    │
  │         "neural nets?"                             (ambiguous → clarify) │
  └──────────────────────┬───────────────────────────────────┬───────────────┘
                         │ produce                           ▲ consume
                         ▼                                   │
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                         KAFKA  MESSAGE  BROKER                           │
  │                                                                          │
  │   ──────────────────────────────────────────────────────────────────     │
  │   Topic: init-planner          ◄── User / App Layer produces here        │
  │   Topic: user-clarification-response ◄── Learner answers clarification   │
  │   Topic: planner-response      ──► App Layer consumes final answer       │
  │   Topic: clarify-user-level    ──► App Layer asks learner a question     │
  │   ──────────────────────────────────────────────────────────────────     │
  │   Topic: rag                   ──► RAG Agent consumes                    │
  │   Topic: teaching              ──► Teaching Agent consumes               │
  │   Topic: quiz                  ──► Quiz Agent consumes                   │
  │   Topic: rag-complete          ◄── RAG Agent produces results            │
  │   Topic: material-compiled     ◄── Teaching Agent produces results       │
  │   Topic: quiz-complete         ◄── Quiz Agent produces results           │
  └──────────┬───────────────────────────────────────────────┬───────────────┘
   consume   │  init-planner                                 │  produce
   ─────────────────────────────                            ─│──────────────
             ▼                                               │ planner-response
╔════════════════════════════════════════════════════════════╪══════════════╗
║           PLANNER AGENT  (Orchestrator)                    │              ║
║           planner_agent/agent.py  ─  LangGraph StateGraph  │              ║
║                                                            │              ║
║  ┌─────────────────────────────────────────────────────────│────────────┐ ║
║  │  [1] validate_query                                      │            │ ║
║  │       schema check │ UUID │ non-empty │ version check    │            │ ║
║  │       guardrail: prompt injection detection              │            │ ║
║  │            │ invalid ──────────────────────────────────► emit_result  │ ║
║  │            │ valid                                       │            │ ║
║  │            ▼                                             │            │ ║
║  │  [2] assess_learner_level  ◄──── LiteLLM                │            │ ║
║  │       LEARNER_LEVEL_PROMPT                               │            │ ║
║  │       naive │ intermediate │ advanced  +  confidence     │            │ ║
║  │            │ conf ≥ 0.65                                 │            │ ║
║  │            │                     conf < 0.65             │            │ ║
║  │            │           ┌─────────────────────────────┐   │            │ ║
║  │            │           │ [3] produce_clarification    │   │            │ ║
║  │            │           │  Kafka → clarify-user-level  │   │            │ ║
║  │            │           │ [4] wait_for_clarification   │   │            │ ║
║  │            │           │  Kafka ← user-clarification  │   │            │ ║
║  │            │           │  (timeout 120s → intermediate│   │            │ ║
║  │            │           └─────────────┬───────────────┘   │            │ ║
║  │            └────────────────────────►│                   │            │ ║
║  │                                      ▼                   │            │ ║
║  │  [5] check_guardrails  ◄──── LiteLLM (COMPLEX only)      │            │ ║
║  │       GUARDRAIL_PROMPT                                    │            │ ║
║  │       ALLOWED │ WARN │ BLOCKED                            │            │ ║
║  │            │ BLOCKED ──────────────────────────────────► emit_result  │ ║
║  │            │ ALLOWED/WARN                                 │            │ ║
║  │            ▼                                             │            │ ║
║  │  [6] rewrite_query  ◄──── LiteLLM  (if COMPLEX/short)   │            │ ║
║  │       QUERY_REWRITE_PROMPT                               │            │ ║
║  │       "neural nets?" → "Can you quiz me on the           │            │ ║
║  │        fundamentals of neural networks?"                 │            │ ║
║  │            │                                             │            │ ║
║  │            ▼                                             │            │ ║
║  │  [7] plan_learning_path  ◄──── LiteLLM                  │            │ ║
║  │       LEARNING_PLAN_PROMPT                               │            │ ║
║  │       → LearningPlan { required_agents,                  │            │ ║
║  │           parallel_groups, depth, objective }            │            │ ║
║  │            │                                             │            │ ║
║  │            │ if RAG + short/conf<0.85                    │            │ ║
║  │            ├──► [8] generate_hyde_doc ◄── LiteLLM        │            │ ║
║  │            │         HYDE_PROMPT                         │            │ ║
║  │            │         hypothetical passage prepended       │            │ ║
║  │            │         to RAGAgentInput.user_prompt         │            │ ║
║  │            ▼                                             │            │ ║
║  │  [9] dispatch_agents  (PARALLEL)                        │            │ ║
║  │    Kafka produce → rag       (RAGAgentInput)             │            │ ║
║  │    Kafka produce → teaching  (TeachingAgentInput)        │            │ ║
║  │    Kafka produce → quiz      (QuizAgentInput) [optional] │            │ ║
║  │            │                                             │            │ ║
║  │            ▼                                             │            │ ║
║  │  [10] collect_responses                                  │            │ ║
║  │    Kafka consume ← rag-complete       (RAGAgentOutput)   │            │ ║
║  │    Kafka consume ← material-compiled  (TeachingOutput)   │            │ ║
║  │    Kafka consume ← quiz-complete      (QuizAgentOutput)  │            │ ║
║  │    dedup by (request_id, agent_type)                     │            │ ║
║  │    timeout: 120s per agent                               │            │ ║
║  │            │                                             │            │ ║
║  │            ▼                                             │            │ ║
║  │  [11] validate_responses  (validator.py)                 │            │ ║
║  │    ✓ schema conformance (pydantic)                       │            │ ║
║  │    ✓ non-empty primary content field                     │            │ ║
║  │    ✓ content ≥ MIN_CONTENT_LENGTH (100 chars)            │            │ ║
║  │    ✓ request_id match                                    │            │ ║
║  │    ✓ status != failed                                    │            │ ║
║  │    ✓ valid UTF-8 JSON                                    │            │ ║
║  │    invalid + retries left ──► retry_agent ──► [9]        │            │ ║
║  │    invalid + max retries  ──► mark partial               │            │ ║
║  │            │                                             │            │ ║
║  │            ▼                                             │            │ ║
║  │  [12] synthesize_response  ◄──── LiteLLM                │            │ ║
║  │       SYNTHESIS_PROMPT                                   │            │ ║
║  │       calibrated to learner_level                        │            │ ║
║  │       combines: study_material + teaching_content + quiz │            │ ║
║  │            │                                             │            │ ║
║  │            ▼                                             │            │ ║
║  │  [13] emit_result                                        │            │ ║
║  │       PlannerResponse { complete │ partial │ failed }    │            │ ║
║  └──────────────────────────────────────────────────────────┼────────────┘ ║
║                                                             │              ║
║    AgentRegistry  (registry.py)                             │              ║
║    ┌────────────────────────────────────────────────────┐   │              ║
║    │ RAG_AGENT       produce:rag       consume:rag-complete  │              ║
║    │ TEACHING_AGENT  produce:teaching  consume:material-compiled            ║
║    │ QUIZ_EVAL_AGENT produce:quiz      consume:quiz-complete  │              ║
║    │ [FUTURE_AGENT]  produce:X         consume:X-complete    │              ║
║    └────────────────────────────────────────────────────┘   │              ║
╚═════════════════════════════════════════════════════════════╪══════════════╝
                           parallel dispatch                  │
          ┌─────────────────────┬──────────────────┐         │
          ▼                     ▼                  ▼         │
  ╔═══════════════╗   ╔══════════════════╗  ╔════════════════╗│
  ║   RAG AGENT   ║   ║  TEACHING AGENT  ║  ║ QUIZ & EVAL    ║│
  ║ rag_agent/    ║   ║ teaching_agent/  ║  ║ AGENT          ║│
  ║               ║   ║                  ║  ║ quiz_agent/    ║│
  ║ consumes:rag  ║   ║ consumes:teaching║  ║ consumes:quiz  ║│
  ║               ║   ║                  ║  ║                ║│
  ║ LangGraph     ║   ║  LangGraph       ║  ║  LangGraph     ║│
  ║ PDF extract   ║   ║  explanation     ║  ║  question gen  ║│
  ║ relevance     ║   ║  calibrated to   ║  ║  + answer eval ║│
  ║ scoring       ║   ║  learner_level   ║  ║                ║│
  ║               ║   ║                  ║  ║                ║│
  ║ produces:     ║   ║ produces:        ║  ║ produces:      ║│
  ║ rag-complete  ║   ║ material-compiled║  ║ quiz-complete  ║│
  ╚═══════╦═══════╝   ╚════════╦═════════╝  ╚═══════╦════════╝│
          │                    │                    │         │
          └──────────┬─────────┘                    │         │
                     ▼                              ▼         │
  ┌────────────────────────────────────────────────────────────│──────────┐
  │                       DATA & TOOL LAYER                    │          │
  │                                                            │          │
  │  ┌──────────────┐  ┌─────────────────┐  ┌────────────────────────┐   │
  │  │ PDF / File   │  │  LLM Providers  │  │   MCP Servers          │   │
  │  │ System       │  │  (via LiteLLM)  │  │  (Model Context Proto) │   │
  │  │              │  │                 │  │                        │   │
  │  │ *.pdf files  │  │ OpenAI GPT-4o   │  │  filesystem MCP        │   │
  │  │ PyMuPDF      │  │ Anthropic Claude │  │  → file read/write     │   │
  │  │ extract      │  │ local Ollama    │  │                        │   │
  │  │ (RAG Agent)  │  │ vLLM endpoint   │  │  web-search MCP        │   │
  │  │              │  │                 │  │  → live web results    │   │
  │  │              │  │ env vars:       │  │                        │   │
  │  │              │  │ *_LLM_MODEL     │  │  memory MCP            │   │
  │  │              │  │ *_API_BASE      │  │  → cross-session store │   │
  │  │              │  │ *_API_KEY       │  │                        │   │
  │  └──────────────┘  └─────────────────┘  │  future custom tools   │   │
  │                                         └────────────────────────┘   │
  │  ┌──────────────┐  ┌─────────────────┐  ┌────────────────────────┐   │
  │  │ Vector Store │  │ Session / State │  │  Kafka Broker          │   │
  │  │ (future v2)  │  │ Store           │  │  (confluent-kafka)     │   │
  │  │              │  │                 │  │                        │   │
  │  │ ChromaDB /   │  │ Redis (v2):     │  │  All agent topics      │   │
  │  │ FAISS        │  │ learner profile │  │  Consumer groups       │   │
  │  │ pre-indexed  │  │ session history │  │  Manual offset commit  │   │
  │  │ retrieval    │  │ level cache     │  │  Dedup by request_id   │   │
  │  └──────────────┘  └─────────────────┘  └────────────────────────┘   │
  └───────────────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────────────┐
  │                    SHARED INFRASTRUCTURE                              │
  │                                                                       │
  │  project/schemas.py   ← ALL agent input/output pydantic models        │
  │                          single source of truth for Kafka contracts    │
  │                                                                       │
  │  */kafka_client.py    ← KafkaProducer/Consumer wrapper per agent      │
  │  */llm_client.py      ← call_llm(messages, config) same pattern       │
  │  */config.py          ← env-var loaders (LLM + Kafka) per module      │
  └───────────────────────────────────────────────────────────────────────┘
```

### Data Flow Summary

```
Learner Query
    │
    ▼ Kafka: init-planner
Planner Agent (LangGraph Orchestrator)
    ├── [1]  validate_query          (schema, UUID, injection guard)
    ├── [2]  assess_learner_level    (1 LLM call)
    ├── [3-4] clarify? ─────────────► Kafka: clarify-user-level
    │                   ◄──────────── Kafka: user-clarification-response
    ├── [5]  check_guardrails        (1 LLM call, COMPLEX only)
    ├── [6]  rewrite_query           (1 LLM call, if COMPLEX/short)
    ├── [7]  plan_learning_path      (1 LLM call)
    ├── [8]  generate_hyde_doc       (1 LLM call, RAG + vague only)
    ├── [9]  dispatch_agents ────────► Kafka: rag | teaching | quiz (parallel)
    │
    ├── [10] collect_responses ◄───── Kafka: rag-complete | material-compiled | quiz-complete
    ├── [11] validate_responses      (pydantic, length, id-match, retry loop)
    ├── [12] synthesize_response     (1 LLM call, calibrated to learner_level)
    └── [13] emit_result ────────────► Kafka: planner-response
```

  ┌─────────────────────────────────────────────────────────────┐
  │                        USER LAYER                           │
  │                                                             │
  │   User types a natural language query                       │
  │   e.g. "Explain gradient descent from chapter 3"            │
  │         "Quiz me on neural networks"                        │
  │         "Teach me backpropagation step by step"             │
  └──────────────────────────┬──────────────────────────────────┘
                             │  PlannerInput
                             │  { request_id, user_query,
                             │    session_context?,
                             │    available_files?,
                             │    schema_version }
                             ▼
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                     PLANNER AGENT  (Orchestrator / Router)                           ║
║                     planner_agent/agent.py  ─  LangGraph StateGraph                 ║
║                                                                                      ║
║  ┌─────────────────────────────────────────────────────────────────────────────────┐ ║
║  │                       PIPELINE NODES                                            │ ║
║  │                                                                                 │ ║
║  │  [1] validate_input ──► schema check, UUID verify, empty-query guard            │ ║
║  │         │                                                                        │ ║
║  │         ▼                                                                        │ ║
║  │  [2] detect_complexity                                                           │ ║
║  │         │  heuristic: word count, connectors, vague single-word                 │ ║
║  │         │  LLM confirm on edge cases only                                        │ ║
║  │         │                                                                        │ ║
║  │         ├──── SIMPLE ────────────────────────────────────┐                      │ ║
║  │         │                                                 │                      │ ║
║  │         └──── COMPLEX / short (<5 words)                 │                      │ ║
║  │                  │                                        │                      │ ║
║  │                  ▼                                        │                      │ ║
║  │  [3] rewrite_query  ◄─────── LiteLLM ────────────────────┼──── (skip if SIMPLE) │ ║
║  │       QUERY_REWRITE_PROMPT                                │                      │ ║
║  │       "neural nets?" → "Can you quiz me on the           │                      │ ║
║  │        fundamentals of neural networks?"                  │                      │ ║
║  │                  │                                        │                      │ ║
║  │                  ▼                                        ▼                      │ ║
║  │  [4] classify_intent ◄──────── LiteLLM ─────────────────────────────────────── │ ║
║  │       INTENT_CLASSIFICATION_PROMPT                                               │ ║
║  │       Scores query against each AgentRegistryEntry.intent_description            │ ║
║  │       Returns: list[IntentCandidate { agent_type, confidence_score, reasoning }] │ ║
║  │                  │                                                               │ ║
║  │         ┌────────┴─────────────────────────────────────────────────┐            │ ║
║  │         │  all scores < threshold (0.6)      top score ≥ threshold  │            │ ║
║  │         ▼                                         │                 │            │ ║
║  │    emit ambiguous ◄─(max retries hit)             │ COMPLEX?        │ SIMPLE?    │ ║
║  │                                                   ▼                 │            │ ║
║  │                              [5] check_guardrails ◄── LiteLLM       │            │ ║
║  │                                   GUARDRAIL_PROMPT                  │            │ ║
║  │                                   ALLOWED │ WARN │ BLOCKED          │            │ ║
║  │                                        │          │                 │            │ ║
║  │                                   BLOCKED         │ (merge paths)   │            │ ║
║  │                                        │          ▼                 ▼            │ ║
║  │                                   emit failed  [6] generate_hyde_doc             │ ║
║  │                                                  (if top=RAG_AGENT               │ ║
║  │                                                   AND short/conf<0.85)           │ ║
║  │                                                   HYDE_PROMPT ◄── LiteLLM        │ ║
║  │                                                   hypothetical passage            │ ║
║  │                                                   prepended to user_prompt        │ ║
║  │                                                        │                         │ ║
║  │                                                        ▼                         │ ║
║  │                              [7] build_payload ◄─── AgentRegistry               │ ║
║  │                                   registry.input_contract_builder(entry, state)  │ ║
║  │                                        │                                         │ ║
║  │                                        ▼                                         │ ║
║  │                              [8] validate_and_retry                              │ ║
║  │                                   pydantic schema check                          │ ║
║  │                                   invalid + retries left → back to [3]           │ ║
║  │                                   invalid + max retries  → emit ambiguous        │ ║
║  │                                        │                                         │ ║
║  │                                        ▼                                         │ ║
║  │                              [9] emit_result → PlannerOutput                     │ ║
║  └─────────────────────────────────────────────────────────────────────────────────┘ ║
║                                                                                      ║
║    ┌──────────────────────────────────────────────────────────────────────────────┐  ║
║    │  AgentRegistry  (planner_agent/registry.py)                                  │  ║
║    │                                                                              │  ║
║    │  RAG_AGENT      │ intent_description, keywords, supports_hyde=True,  builder │  ║
║    │  TEACHING_AGENT │ intent_description, keywords, supports_hyde=False, builder │  ║
║    │  QUIZ_EVAL_AGENT│ intent_description, keywords, supports_hyde=False, builder │  ║
║    │  [FUTURE_AGENT] │ → add one AgentRegistryEntry, zero other changes           │  ║
║    └──────────────────────────────────────────────────────────────────────────────┘  ║
╚═══════════════════════════════╦══════════════════════════════════════════════════════╝
                                │  PlannerOutput
                                │  { routing_decision: { target_agent,
                                │    confidence_score, constructed_payload,
                                │    query_was_rewritten, hyde_applied },
                                │    status, errors }
                                │
           ┌────────────────────┼────────────────────────────────┐
           │                    │                                │
           ▼                    ▼                                ▼
  ╔═══════════════╗   ╔══════════════════╗           ╔══════════════════════╗
  ║   RAG AGENT   ║   ║  TEACHING AGENT  ║           ║  QUIZ & EVAL AGENT   ║
  ║ rag_agent/    ║   ║ teaching_agent/  ║           ║  quiz_agent/         ║
  ║               ║   ║                  ║           ║                      ║
  ║ RAGAgentInput ║   ║TeachingAgentInput║           ║  QuizAgentInput      ║
  ║               ║   ║                  ║           ║                      ║
  ║ LangGraph     ║   ║  LangGraph       ║           ║  LangGraph           ║
  ║ page-by-page  ║   ║  explanation     ║           ║  question            ║
  ║ extraction    ║   ║  generation      ║           ║  generation +        ║
  ║ + relevance   ║   ║  loop            ║           ║  answer eval         ║
  ║ scoring       ║   ║                  ║           ║                      ║
  ╚═══════╦═══════╝   ╚════════╦═════════╝           ╚══════════╦═══════════╝
          │                    │                                 │
          │       ┌────────────┴──────────────────┐             │
          │       │                               │             │
          ▼       ▼                               ▼             ▼
  ┌───────────────────────────────────────────────────────────────────────────┐
  │                        DATA & TOOL LAYER                                  │
  │                                                                           │
  │  ┌─────────────────┐   ┌──────────────────┐   ┌────────────────────────┐ │
  │  │   PDF / File    │   │   LLM Providers  │   │   MCP Servers          │ │
  │  │   System        │   │   (via LiteLLM)  │   │  (Model Context        │ │
  │  │                 │   │                  │   │   Protocol)            │ │
  │  │  rag_agent/     │   │  OpenAI GPT-4o   │   │                        │ │
  │  │  tests/inputs/  │   │  Anthropic Claude │   │  filesystem MCP        │ │
  │  │  *.pdf          │   │  local Ollama    │   │  → file read/write     │ │
  │  │                 │   │  vLLM endpoint   │   │                        │ │
  │  │  PyMuPDF        │   │                  │   │  web-search MCP        │ │
  │  │  text/table/    │   │  Configured via  │   │  → live web results    │ │
  │  │  image extract  │   │  env vars:       │   │                        │ │
  │  │                 │   │  *_LLM_MODEL     │   │  memory MCP            │ │
  │  │  (RAG Agent     │   │  *_API_BASE      │   │  → cross-session       │ │
  │  │   responsibility│   │  *_API_KEY       │   │    context store       │ │
  │  │   only)         │   │                  │   │                        │ │
  │  └─────────────────┘   └──────────────────┘   │  custom MCP tools      │ │
  │                                                │  → future extensn.     │ │
  │  ┌─────────────────┐   ┌──────────────────┐   └────────────────────────┘ │
  │  │  Vector Store   │   │  Session / State │                               │
  │  │  (future v2)    │   │  Store           │                               │
  │  │                 │   │                  │                               │
  │  │  ChromaDB /     │   │  In-memory per   │                               │
  │  │  FAISS          │   │  request (v1)    │                               │
  │  │                 │   │                  │                               │
  │  │  Used by RAG    │   │  Redis / DB      │                               │
  │  │  Agent for      │   │  (future:        │                               │
  │  │  pre-indexed    │   │   multi-turn     │                               │
  │  │  retrieval      │   │   sessions)      │                               │
  │  └─────────────────┘   └──────────────────┘                               │
  └───────────────────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────────────────────────────────────────────────┐
  │                    SHARED INFRASTRUCTURE                                  │
  │                                                                           │
  │  project/schemas.py   ← PlannerInput, PlannerOutput, RoutingDecision,    │
  │                          RAGAgentInput, RAGAgentOutput, TeachingAgentInput│
  │                          QuizAgentInput — single source of truth          │
  │                                                                           │
  │  */llm_client.py      ← call_llm(messages, config) — same pattern in     │
  │                          each agent module (future: shared library)       │
  │                                                                           │
  │  */config.py          ← env-var loaders per agent module                 │
  └───────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Summary

```
User Query
    │
    ▼
PlannerInput ──► Planner Agent Pipeline (LangGraph)
                      │
                      ├── [optional] Query Rewriting       (1 LLM call)
                      ├── [optional] Guardrails check      (1 LLM call)
                      ├──           Intent Classification  (1 LLM call)
                      └── [optional] HyDE augmentation     (1 LLM call)
                                        │
                                        ▼
                              PlannerOutput { status, routing_decision }
                                        │
               ┌─────────────┬──────────┴──────────┬─────────────────┐
               ▼             ▼                      ▼                 ▼
          RAGAgentInput  TeachingAgentInput   QuizAgentInput   [Future]Input
               │             │                      │
               ▼             ▼                      ▼
          RAG Agent     Teaching Agent        Quiz Agent
          (PyMuPDF +    (LLM explanation      (LLM question
          LangGraph +    loop + LangGraph)     gen + eval +
          sentence-                            LangGraph)
          transformers)
               │             │                      │
               └──────┬──────┘                      │
                      ▼                             ▼
               LiteLLM (unified)           LiteLLM (unified)
               LLM Providers               LLM Providers
## Complexity Tracking

No constitution violations identified. Complexity is justified:

| Element | Why Needed |
|---------|-----------|
| Kafka async I/O | Decouples agent lifecycle; enables parallel dispatch without blocking; required for scalable multi-agent coordination |
| LangGraph StateGraph (13 nodes) | Explicit conditional branching (level gate, clarification loop, guardrail, rewrite, HyDE, parallel dispatch, validation, retry, synthesis) cannot be cleanly expressed as linear functions without sacrificing observability and testability |
| Learner level assessment | Core personalisation requirement; without it all responses are generic; isolated to `classifier.py` |
| Multi-turn clarification (Kafka loop) | Required for ambiguous queries; bounded to 1 clarification per session; timeout prevents indefinite blocking |
| HyDE augmentation node | Improves RAG precision for vague queries; isolated to `hyde.py`; ≤1 LLM call only when triggered |
| Response validation + retry loop | Agent responses can be empty or malformed; bounded retries (max 3) with augmented prompt prevent garbage reaching synthesis |
| Synthesis node | Combines outputs from heterogeneous agents into a coherent, level-calibrated response; cannot be avoided without degrading output quality |
| Guardrails node | Educational-scope safety; COMPLEX path only; isolated to `guardrails.py` |
