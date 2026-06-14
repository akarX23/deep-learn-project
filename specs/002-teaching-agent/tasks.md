# Tasks: Teaching Agent

**Input**: Design documents from `/specs/002-teaching-agent/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Organization**: Phase 1 (core pipeline, complete) + Phase 2 (Kafka integration, open).
All Phase 2 tasks are reviewed and approved individually before implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: User story from spec.md (US1–US4 = core pipeline; US5 = Kafka integration)

---

## Phase 1: Core Teaching Agent Pipeline ✅ Complete

### P1-A: Shared Schemas & Dependencies

- [x] T001 [US1–US4] Add `OutputMode`, `TeachingAgentInput`, `TeachingContent`,
      `TeachingMetadata`, `TeachingAgentOutput` to `project/schemas.py` (Teaching Agent section)
- [x] T002 Add `python-dotenv>=1.0.0` to `requirements.txt`

### P1-B: Teaching Agent Module Files

- [x] T003 [P] Create `teaching_agent/__init__.py` (empty module marker)
- [x] T004 [P] Create `teaching_agent/config.py`:
      `LLMConfig` dataclass, `MODE_MAX_TOKENS` dict (512/1024/2048),
      `get_llm_config(output_mode)` — reads `TEACHING_MODEL` (required, no default),
      `TEACHING_API_BASE`, `TEACHING_API_KEY`, `TEACHING_TEMPERATURE`; calls `load_dotenv()`
- [x] T005 [P] Create `teaching_agent/llm_client.py`:
      `call_llm(messages, config) → (content: str, tokens_used: int)`;
      passes `response_format={"type": "json_object"}`; only passes `api_key`/`api_base`
      when explicitly set; wraps all LiteLLM exceptions as `RuntimeError`
- [x] T006 [P] Create `teaching_agent/prompts.py`:
      `BEGINNER_PROMPT`, `INTERMEDIATE_PROMPT`, `ADVANCED_PROMPT` (with `{topic}` and
      `{context}` placeholders); `PROMPT_BY_MODE` dict; beginner marks diagram as REQUIRED
- [x] T007 [P] Create `teaching_agent/validators.py`:
      `validate_mermaid(diagram: str) → bool` — regex structural check; splits on `[\n;]`;
      requires recognized header keyword + at least one additional content segment
- [x] T008 [P] Create `teaching_agent/helpers.py`:
      `parse_llm_response(raw)` — strips fences only when whole response is fence-wrapped
      (uses `match()` not `search()`); validates `explanation` and `notes` non-empty;
      `build_messages(prompt)`, `build_error_output(topic, output_mode, model)`
- [x] T009 Create `teaching_agent/agent.py`:
      `TeachingAgent.run(raw_input)` — validate → config → prompt → LLM → parse → diagram
      → assemble output; `_resolve_diagram()` — retry once for beginner, fallback template;
      all failure paths return `status: "error"`, no unhandled exceptions; CLI entry point

### P1-C: Tests & Developer Tools

- [x] T010 [P] Create `teaching_agent/tests/__init__.py` (empty)
- [x] T011 [P] Create `teaching_agent/tests/inputs/sample_input.json` (beginner, loop topic)
- [x] T012 Update `pytest.ini` `testpaths` to include `teaching_agent/tests`
- [x] T013 Create `teaching_agent/tests/test_teaching_agent.py` (33 tests):
      schema tests (5), Mermaid validator tests (9), `parse_llm_response` tests (10),
      agent integration tests with real LLM calls (9)
- [x] T014 Create `teaching_agent/tests/live_call_test.py`:
      2-step smoke test — Step 1: direct `call_llm`; Step 2: full agent pipeline with assertions
- [x] T015 [P] Create `teaching_agent/tests/run_samples.py`:
      3 topics × 3 modes = 9 real LLM calls; saves each output to
      `teaching_agent/tests/outputs/<slug>_<mode>.json`; prints summary table
- [x] T016 [P] Create `teaching_agent/tests/inputs/loop.json`,
      `recursion.json`, `gradient_descent.json` (topic input fixtures)

---

## Phase 2: Kafka Integration (US5) — Open

**Each task is reviewed and approved before implementation.**
**All Kafka dependencies are injectable — no real Kafka connection required in tests.**

---

### P2-A: Shared Infrastructure (Blocking Prerequisites)

**Purpose**: Register topics in the project registry and add Kafka event schemas.
Backend service will auto-bootstrap `"teaching"` and `"teaching-complete"` on next startup.

**All P2-B through P2-E tasks depend on these schemas being present.**

- [x] T017 Update `project/topics.py`:
      add `TEACHING = "teaching"` to existing `PlannerTopics` enum (consistent with
      `PlannerTopics.RAG`); add new `TeachingTopics` enum with only
      `TEACHING_COMPLETE = "teaching-complete"`; include `TeachingTopics` in
      `get_all_topic_names()` return value; add `get_teaching_topic_names()` helper
      returning `[PlannerTopics.TEACHING, TeachingTopics.TEACHING_COMPLETE]` — used by
      `TeachingWorker.start()` for startup topic presence check (mirrors `get_rag_topic_names()`)

- [x] T018 Add `TeachingRequestEvent` to `project/schemas.py` (Teaching Agent section):
      fields: `request_id` (str, required, non-empty), `session_ctx` (dict, required, may be `{}`),
      `topic` (str), `output_mode` (str), `context` (str, default `""`),
      `created_at` (str | None), `source` (str | None);
      validators: `request_id` non-empty, `session_ctx` not null, `topic`/`output_mode` non-empty

- [x] T019 Add `TeachingCompletionEvent` to `project/schemas.py` (Teaching Agent section):
      fields: `request_id` (str), `session_ctx` (dict), `topic` (str), `output_mode` (str),
      `status` (str — `"ok"` or `"error"`), `content` (TeachingContent | None),
      `tokens_used` (int, ge=0), `model` (str), `started_at` (str), `completed_at` (str),
      `duration_ms` (int, ge=0), `errors` (list[str], default `[]`),
      `source` (str, default `"teaching-agent"`)

**Checkpoint**: `python -c "from project.topics import get_all_topic_names; assert 'teaching' in get_all_topic_names()"` passes

---

### P2-B: Kafka Gateway (`teaching_agent/kafka.py`)

**Purpose**: Pure I/O primitives and Protocol types. No business logic.

- [x] T020 Create `teaching_agent/kafka.py`:
      - `ConsumerRecordProtocol`, `KafkaConsumerProtocol`, `KafkaProducerProtocol` — Protocol types
        mirroring `rag_agent/kafka.py` exactly (enables fake implementations in tests)
      - `create_consumer(config, topics=None) → KafkaConsumerProtocol`
      - `create_producer(config) → KafkaProducerProtocol`
      - `consumer_subscribe_teaching(consumer)` — subscribes to `PlannerTopics.TEACHING`
        (not `TeachingTopics` — `"teaching"` is Planner-owned; mirrors `consumer_subscribe_rag`)
      - `publish_teaching_complete(producer, event: TeachingCompletionEvent)` — sends to
        `TeachingTopics.TEACHING_COMPLETE`, then `producer.flush()`
      - `poll_records(consumer, timeout_ms)`, `check_required_topics(consumer, required)`,
        `close_consumer(consumer)`, `close_producer(producer)`
      - Note: `KafkaRuntimeConfig` is added to `teaching_agent/config.py` (reads same
        `BACKEND_KAFKA_*` env vars as RAG agent; sets `client_id = "teaching-agent"`,
        `consumer_group_id = "teaching-agent-consumer"`); `kafka.py` imports it from there

**Checkpoint**: `python -c "from teaching_agent.kafka import KafkaConsumerProtocol"` passes

---

### P2-C: Request Handler (`teaching_agent/handlers.py`)

**Purpose**: Business logic bridge. Zero Kafka I/O — all Kafka interaction goes through injected `publisher` callable.

- [x] T021 Create `teaching_agent/handlers.py`:
      - `TeachingRequestEventHandler` class with injectable dependencies:
        `agent_factory` (default: `TeachingAgent`), `publisher` (default:
        `publish_teaching_complete`), `clock` (default: `datetime.now(UTC)`)
      - `parse_event(payload: dict) → TeachingRequestEvent` — validates inbound payload
      - `build_completion_event(event, result, started_at, completed_at) → TeachingCompletionEvent`
        — maps `TeachingAgentOutput` fields + timing into completion event;
        flattens `metadata.tokens_used` and `metadata.model` into top-level fields
      - `process_request(payload: dict, producer=None) → TeachingCompletionEvent | None`:
        parse event → extract `TeachingAgentInput` fields → `agent.run()` → build completion
        event → publish; on parse failure: log error and return None (no publish);
        on agent failure: still publish error completion event (always-publish rule)
      - `_isoformat_utc(dt: datetime) → str` — UTC ISO 8601 serialization helper
      - `_extract_request_id(payload: dict) → str` — returns `"unknown"` if absent

**Checkpoint**: Unit-testable without Kafka — `TeachingRequestEventHandler` instantiates with fake `agent_factory` and `publisher` lambda

---

### P2-D: Worker Lifecycle (`teaching_agent/worker.py`)

**Purpose**: Owns consumer/producer lifecycle and the background poll loop thread.

- [x] T022 Create `teaching_agent/worker.py`:
      - `process_consumer_batch(consumer, producer, handler, poll_timeout_ms) → int` —
        standalone function: poll once → dispatch each record → return count; errors logged
        per-record, loop continues
      - `TeachingWorker` class with injectable factories:
        `config`, `producer_factory`, `consumer_factory`, `handler_factory`
      - `start()` — create consumer + producer via factories; `consumer_subscribe_teaching()`;
        `check_required_topics(consumer, get_teaching_topic_names())` (warn if missing, do not
        abort; mirrors RAG worker pattern); start daemon thread running `_poll_loop()`;
        set `_startup_check_complete = True`
      - `_poll_loop(handler)` — loops while `stop_event` not set; calls
        `process_consumer_batch()`; logs poll_loop errors and continues
      - `stop()` — set `stop_event`; `thread.join(timeout=2)`;
        `close_consumer()`; `close_producer()`
      - `get_state() → WorkerRuntimeState` — returns running, stop_event_set,
        poll_thread_alive, startup_topic_check_complete, startup_topic_check_warnings
      - `main()` — configures logging; creates `TeachingWorker`; `worker.start()`;
        loops until `KeyboardInterrupt`; `worker.stop()`

**Checkpoint**: `TeachingWorker` starts and stops cleanly with fake consumer/producer factories

---

### P2-E: Tests

**Purpose**: Full offline test coverage for Kafka layer using Protocol-compatible fakes.

- [x] T023 Create `teaching_agent/tests/test_kafka_integration.py`:
      - `_FakeConsumer` (implements `KafkaConsumerProtocol`): `.poll()` returns pre-loaded
        records, `.topics()` returns configured set, `.close()` sets flag
      - `_FakeProducer` (implements `KafkaProducerProtocol`): captures `.send()` calls,
        tracks `.flush()` and `.close()`
      - `test_consumer_batch_dispatches_event_from_teaching_topic`
      - `test_request_handler_dispatches_to_teaching_agent`
      - `test_ingest_to_dispatch_flow_preserves_request_id`
      - `test_publish_teaching_complete_sends_to_correct_topic`
      - `test_completion_event_preserves_request_correlation`
      - `test_lifecycle_logging_covers_consume_process_and_publish` (caplog)
      - `test_error_stage_logged_when_processing_fails` (caplog)

- [x] T024 Create `teaching_agent/tests/test_worker_runtime.py`:
      - `_FakeConsumer`, `_FakeProducer`, `_Handler` local fakes
      - `test_worker_startup_and_shutdown_lifecycle`
      - `test_worker_loop_continues_when_idle`
      - `test_process_batch_continues_after_single_event_failure`
      - `test_startup_topic_check_passes_when_topics_exist`
      - `test_missing_topics_warn_and_worker_continues`
      - `test_latency_helper_returns_non_negative_value`

---

### P2-F: Integration & Validation

- [x] T025 Run full test suite including new Kafka tests:
      `pytest teaching_agent/tests/ -q` — all tests must pass
      (Kafka tests use fakes — no real Kafka needed)

- [x] T026 Update `CLAUDE.md` — confirm Teaching Agent Kafka section is accurate after
      implementation (worker run command, topic names, test file list)

- [x] T027 Manual end-to-end validation (optional, requires local Kafka):
      start backend service → verify `"teaching"` and `"teaching-complete"` topics bootstrapped;
      start `teaching_agent/worker.py`; publish a `TeachingRequestEvent` to `"teaching"`;
      verify `TeachingCompletionEvent` on `"teaching-complete"` with matching `request_id`

**Checkpoint**: All Phase 2 tests pass; `"teaching"` and `"teaching-complete"` topics
registered in `project/topics.py`; worker boots and processes messages end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: Complete ✅
- **P2-A (T017–T019)**: No dependencies — start immediately; BLOCKS all other P2 phases
- **P2-B (T020)**: Depends on P2-A (needs `TeachingCompletionEvent` for `publish_teaching_complete`)
- **P2-C (T021)**: Depends on P2-A + P2-B (needs Kafka types and event schemas)
- **P2-D (T022)**: Depends on P2-B + P2-C (needs kafka.py and handlers.py)
- **P2-E (T023–T024)**: Depends on P2-B + P2-C + P2-D (tests all three files)
- **P2-F (T025–T027)**: Depends on P2-E completion

### Within P2-A

- T017 (topics.py) and T018–T019 (schemas.py) can run in parallel
- T018 and T019 can also run in parallel (different schema classes)

### Implementation Order (sequential, one at a time per user approval)

```
T017 → T018 → T019 → [checkpoint]
T020 → [checkpoint]
T021 → [checkpoint]
T022 → [checkpoint]
T023 → T024 → [checkpoint]
T025 → T026 → T027
```

---

## Notes

- [P] tasks have no blocking dependency on incomplete tasks in the same phase
- All Phase 2 Kafka tests use Protocol-compatible fakes — no `pytest-mock`, no `unittest.mock`
- `KafkaRuntimeConfig` is read from `BACKEND_KAFKA_*` env vars; `teaching_agent/kafka.py`
  follows the same config pattern as `rag_agent/kafka.py`
- `WorkerRuntimeState` schema already exists in `project/schemas.py` (used by RAG worker);
  `TeachingWorker.get_state()` returns the same type
- Every Phase 2 task is implemented only after explicit user approval
