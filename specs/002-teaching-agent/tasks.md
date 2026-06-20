# Tasks: Teaching Agent

**Input**: Design documents from `/specs/002-teaching-agent/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Organization**: Phase 1 (core pipeline) + Phase 2 (Kafka integration) + Phase 3 (reflection layer)
+ Phase 4 (token streaming) + Phase 5 (multi-turn conversation).
All Phase 2–5 tasks are reviewed and approved individually before implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: User story from spec.md (US1–US4 = core pipeline; US5 = Kafka integration; US6 = reflection; US7 = multi-turn conversation)

---

## Phase 1: Core Teaching Agent Pipeline ✅ Complete

### P1-A: Shared Schemas & Dependencies

- [x] T001 [US1–US4] Add `OutputMode`, `TeachingAgentInput`, `TeachingContent`,
      `TeachingMetadata`, `TeachingAgentOutput` to `project/schemas.py` (Teaching Agent section)
- [x] T002 Add `python-dotenv>=1.0.0` to `requirements.txt`

### P1-B: Teaching Agent Module Files

- [x] T003 [P] Create `teaching_agent/__init__.py` (empty module marker)
- [x] T004 [P] Create `teaching_agent/config.py`:
      `LLMConfig` dataclass, `get_llm_config(output_mode)` — resolves per-mode config from
      `TEACHING_{MODE}_MODEL` / `TEACHING_{MODE}_API_KEY` / `TEACHING_{MODE}_MAX_TOKENS` /
      `TEACHING_{MODE}_TEMPERATURE` / `TEACHING_{MODE}_EFFORT`
      with fallback to `TEACHING_MODEL` / `TEACHING_API_KEY` / default 4096 /
      `TEACHING_TEMPERATURE` (default 0.7); effort has no shared fallback (optional, no default);
      no hardcoded values in Python; calls `load_dotenv()`
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

## Phase 2: Kafka Integration (US5) — Complete ✅

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
      fields: `request_id` (str, required, non-empty), `user_prompt` (str),
      `user_level` (str), `rag_compiled` (str, default `""`), `sid` (str, non-empty
      Socket.IO session ID for frontend WebSocket routing);
      no validators beyond Pydantic field types

- [x] T019 Add `TeachingCompletionEvent` to `project/schemas.py` (Teaching Agent section):
      fields: `request_id` (str), `sid` (str), `user_level` (str),
      `content` (str, default `""`);
      validators: `request_id` and `user_level` non-empty

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
        `publish_teaching_complete`) — no `clock` (completion event has no timing fields)
      - `parse_event(payload: dict) → TeachingRequestEvent` — validates inbound payload
      - `build_completion_event(event, result) → TeachingCompletionEvent`
        — copies `request_id`, `sid`, `user_level` from the event; serializes
        `result.content` to JSON (`""` when content is None)
      - `process_request(payload: dict, producer=None) → TeachingCompletionEvent | None`:
        parse event → map `user_prompt → topic`, `user_level → output_mode`,
        `rag_compiled → context` → `agent.run()` → build completion event → publish;
        on parse failure: log error and return None (no publish);
        on agent failure: still publish completion event with empty `content` (always-publish rule)
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

- [x] T028 Update per-mode token ceilings to 4096 across all three modes (beginner / intermediate / advanced):
      update `MODE_MAX_TOKENS` in `teaching_agent/config.py`; update spec.md (FR-008, SC-005,
      acceptance criteria), plan.md (Constraints, Token-Ceiling Semantics), research.md (Decision 5),
      CLAUDE.md (Output mode rules table), and tasks.md (T004 description).
      Rationale: original 512/1024/2048 limits caused truncated JSON responses with verbose providers
      (e.g. Claude). Limits kept as 3 distinct placeholders so they can be tuned independently.

- [x] T029 Update `teaching_agent/config.py` for per-mode LLM configuration (FR-009, Decision 12):
      remove hardcoded `MODE_MAX_TOKENS` dict; update `get_llm_config(output_mode)` to resolve
      per-mode config from env vars with fallbacks:
      - model: `TEACHING_{MODE}_MODEL` → `TEACHING_MODEL` (required if no per-mode override)
      - api_key: `TEACHING_{MODE}_API_KEY` → `TEACHING_API_KEY`
      - max_tokens: `TEACHING_{MODE}_MAX_TOKENS` → default 4096
      - temperature: `TEACHING_{MODE}_TEMPERATURE` → `TEACHING_TEMPERATURE` → default 0.7
      - effort: `TEACHING_{MODE}_EFFORT` → no fallback (optional; `None` when unset)
      No hardcoded values remain in config.py; all defaults resolve from env/config files only.

- [~] T030 Update `.env.local` — add per-mode env var stubs (commented out) under Teaching Agent section:
      `TEACHING_BEGINNER_MODEL`, `TEACHING_BEGINNER_API_KEY`, `TEACHING_BEGINNER_MAX_TOKENS`,
      same for `INTERMEDIATE` and `ADVANCED`; shared `TEACHING_MODEL` / `TEACHING_API_KEY`
      remain as the active fallback defaults. Stubs are commented out so they act as
      in-place documentation without overriding the shared fallbacks.
      NOTE: documentation-only — these per-mode stubs are NOT currently present in `.env.local`;
      `get_llm_config()` resolves them at runtime regardless, and the shared `TEACHING_*`
      fallbacks are the active config. Re-add the stubs only if per-mode tuning is needed.

- [x] T031 Update `CLAUDE.md` env var table — add per-mode override rows
      (`TEACHING_{MODE}_MODEL`, `TEACHING_{MODE}_API_KEY`, `TEACHING_{MODE}_MAX_TOKENS`)
      with fallback description; update Output mode rules table to reference env vars.

- [x] T032 Update `teaching_agent/config.py` and `teaching_agent/llm_client.py` for per-mode
      temperature and effort (FR-009, Decision 12):
      - `LLMConfig`: add `effort: str | None = None` field
      - `get_llm_config()`: read `TEACHING_{MODE}_TEMPERATURE` (fallback: `TEACHING_TEMPERATURE`,
        default 0.7) and `TEACHING_{MODE}_EFFORT` (no fallback; `None` when unset)
      - `llm_client.py`: if `config.effort` is set and model string contains `"sonnet-4-6"` or
        `"opus-4-6"`, pass `output_config={"effort": config.effort}` as a kwarg to
        `litellm.completion()`; silently skip for all other models

- [x] T033 Update `.env.local` — add per-mode temperature and effort stubs under Teaching Agent
      section: `TEACHING_BEGINNER_TEMPERATURE`, `TEACHING_INTERMEDIATE_TEMPERATURE`,
      `TEACHING_ADVANCED_TEMPERATURE`, `TEACHING_BEGINNER_EFFORT`, `TEACHING_INTERMEDIATE_EFFORT`,
      `TEACHING_ADVANCED_EFFORT`; variables go in `.env.local` (not `.env.local.example`)
      NOTE: documentation-only — these stubs are NOT currently present in `.env.local`.
      `get_llm_config()` reads `TEACHING_{MODE}_TEMPERATURE` (fallback `TEACHING_TEMPERATURE`,
      default 0.7) and `TEACHING_{MODE}_EFFORT` (optional, `None` when unset) at runtime
      regardless. Re-add the stubs only if per-mode tuning is needed.

- [x] T034 Remove the dead commented-out `TeachingCompletionEvent` block in
      `project/schemas.py` (Teaching Agent section, ~lines 411–433). It was superseded by the
      active planner-aligned `TeachingCompletionEvent` in the Planner Agent section and is now
      obsolete. Constitution Principle V — remove obsolete code paths.

- [x] T034 Update `teaching_agent/handlers.py` for new `TeachingRequestEvent` /
      `TeachingCompletionEvent` schema (post-master-merge Planner Agent contract change):
      remove `clock` / timing fields; map `user_prompt→topic`, `user_level→output_mode`,
      `rag_compiled→context` for `agent.run()`; build completion event with `sid`,
      `user_level`, `content` (JSON string). Update `test_kafka_integration.py`: all 7 tests
      updated for new schema fields; old field usage commented out (not deleted) for reference.

**Checkpoint**: All Phase 2 tests pass; `"teaching"` and `"teaching-complete"` topics
registered in `project/topics.py`; worker boots and processes messages end-to-end

---

---

## Phase 4: Token Streaming (US6) — Complete ✅

**Goal**: Stream LLM output tokens field-by-field to the frontend via `"stream-tokens"` Kafka topic in real time, while continuing to deliver the complete response via `"teaching-complete"`. LLM output format switches from JSON to markdown with bold section headers.

**All Phase 4 tasks require explicit user approval before implementation. One task at a time.**

---

### P4-A: LLM Output Format Change (Blocking Prerequisite)

**Purpose**: Switch LLM from JSON mode to markdown bold-header format. All downstream Phase 4 tasks depend on this output format.

- [x] T035 Update `teaching_agent/prompts.py`:
      Replace JSON output instruction with markdown bold-header format in all 3 prompts.
      Each prompt now instructs the LLM to use `**Explanation**`, `**Diagram**`, `**Notes**`,
      `**Example**` as section headers with a blank line before each header.
      Remove the "Return ONLY a JSON object" instruction and JSON template from each prompt.
      Keep all per-mode content requirements (5-part structure, diagram rules, etc.) unchanged.

- [x] T036 Update `teaching_agent/llm_client.py`:
      - Remove `response_format={"type": "json_object"}` from `call_llm()` kwargs
      - Add `call_llm_stream(messages, config) → Iterator[tuple[str, int]]`:
        uses `stream=True`; yields `(delta: str, tokens_used: int)` tuples;
        `tokens_used` is `0` for all chunks except the last (populated from `usage.completion_tokens`
        in the final chunk via `stream_options={"include_usage": True}`);
        wraps all LiteLLM exceptions as `RuntimeError`

- [x] T037 Update `teaching_agent/helpers.py`:
      - Remove `parse_llm_response()`, `_JSON_FENCE_OPEN_RE`, and `import json`
      - Add `parse_markdown_response(raw: str) → dict`:
        splits on `**SectionName**` bold headers (case-insensitive);
        returns dict with keys `explanation`, `diagram`, `notes`, `example`;
        raises `ValueError` if `explanation` or `notes` sections are absent or empty;
        `diagram` and `example` default to `None` if section absent or empty
      - `build_messages()` and `build_error_output()` unchanged

**Checkpoint**: `python -m pytest teaching_agent/tests/test_teaching_agent.py -q -k "parse"` — all parse tests pass with updated markdown format

---

### P4-B: Streaming Field Extractor

**Purpose**: New component that processes raw LLM delta chunks and emits field-keyed token events.

- [x] T038 Create `teaching_agent/stream_parser.py`:
      - `StreamingFieldExtractor` class:
        - `__init__(self, token_callback: Callable[[str, str], None])`:
          `token_callback(field, token)` called for each token event
        - `feed(self, chunk: str) → None`:
          appends chunk to internal buffer; detects `**SectionName**` bold headers;
          on header detection: transitions state; for previous completed section that
          was being buffered (diagram): calls `token_callback("diagram", buffer)`;
          for streaming sections (explanation, notes, example): calls
          `token_callback(field, chunk)` immediately for each chunk
        - `finalize(self) → str`:
          flushes any remaining buffered content (diagram if stream ended without
          another header following); returns the complete raw markdown buffer
          (all chunks concatenated, including headers) for use as `TeachingCompletionEvent.content`
        - Internal state: `_current_field`, `_diagram_buffer`, `_raw_buffer`, `_chunk_buffer`
          (small lookahead for split headers)
      - Sections detected: `**Explanation**`, `**Diagram**`, `**Notes**`, `**Example**`
        (case-insensitive match on the header line)

**Checkpoint**: Unit tests in T042 pass for `StreamingFieldExtractor`

---

### P4-C: Agent and Kafka Updates

**Purpose**: Wire streaming into the agent pipeline and add the `stream-tokens` publisher.

- [x] T039 Update `teaching_agent/agent.py`:
      - Add `token_callback: Callable[[str, str], None]` parameter to `run()` (required,
        no default — callers always provide it; tests provide a no-op lambda)
      - Replace main LLM call (Step 4) with `call_llm_stream()` + `StreamingFieldExtractor`:
        instantiate extractor with `token_callback`; iterate `call_llm_stream()` feeding
        each `(delta, tokens_used)` to `extractor.feed(delta)`; capture final `tokens_used`
        from last chunk; call `extractor.finalize()` to get `raw_markdown` and flush diagram
      - Call `parse_markdown_response(raw_markdown)` instead of `parse_llm_response()`
      - Pass `raw_markdown` back to caller alongside `TeachingAgentOutput`:
        `run()` returns `tuple[TeachingAgentOutput, str]`
        (second element is `raw_markdown`; empty string `""` on any error path)
      - `_resolve_diagram()` retry stays as `call_llm()` (non-streaming); unchanged

- [x] T040 Update `teaching_agent/kafka.py`:
      - Add import: `StreamTokensEventBody` from `project.schemas`;
        `BackendStreamTopics` from `project.topics`
      - Add `publish_stream_token(producer: KafkaProducerProtocol, event: StreamTokensEventBody) → None`:
        serializes event with `event.model_dump()`;
        sends to `BackendStreamTopics.STREAM_TOKENS.value`;
        does NOT call `producer.flush()` (tokens are high-frequency; flush only on stream-complete)

- [x] T041 Update `teaching_agent/handlers.py`:
      - Add injectable `stream_publisher` dependency:
        `stream_publisher: Callable[[KafkaProducerProtocol, StreamTokensEventBody], None] = publish_stream_token`
      - In `process_request()`: build `token_callback` closure that publishes
        `StreamTokensEventBody(from_service="teaching-agent", sid=event.sid, data={"field": field, "token": token})`
        via `stream_publisher`
      - Update call to `agent.run()`: pass `token_callback`; unpack tuple result
        `(result, raw_markdown) = agent.run({...}, token_callback)`
      - After `agent.run()` returns (success or error): publish stream-complete sentinel:
        `StreamTokensEventBody(from_service="teaching-agent", sid=event.sid, data={"done": True, "tokens_used": N})`
        then call `producer.flush()` once
      - Update `build_completion_event()`: `content = raw_markdown if result.status == "ok" else ""`
        (replaces `result.content.model_dump_json()`)

**Checkpoint**: `python -m pytest teaching_agent/tests/test_kafka_integration.py -q` — all tests pass

---

### P4-D: Tests

**Purpose**: Full test coverage for Phase 4 changes.

- [x] T042 Create `teaching_agent/tests/test_stream_parser.py`:
      - `test_explanation_tokens_emitted_immediately` — chunks before `**Diagram**` header go to `explanation`
      - `test_diagram_buffered_and_emitted_complete` — diagram chunks buffered; emitted as one event on next header
      - `test_header_split_across_chunks` — `**Explan` + `ation**` across two chunks correctly detected
      - `test_finalize_flushes_trailing_diagram` — diagram at end of stream (no trailing header) emitted on `finalize()`
      - `test_notes_and_example_stream_immediately` — notes and example chunks forwarded per chunk
      - `test_finalize_returns_complete_raw_markdown` — full buffer including headers returned by `finalize()`
      - `test_empty_stream_no_callback` — empty input produces no callback calls

- [x] T043 Update `teaching_agent/tests/test_teaching_agent.py`:
      - Replace 10 `parse_llm_response` tests with `parse_markdown_response` tests using markdown-format inputs
      - Update all mock LLM responses from JSON strings to markdown bold-header strings
      - Update monkeypatch target: `teaching_agent.agent.call_llm` → `teaching_agent.agent.call_llm_stream`
        (mock must yield `(delta, 0)` tuples for intermediate chunks and `(delta, N)` for final chunk)
      - All integration tests pass a no-op `token_callback=lambda f, t: None` to `agent.run()`
      - `agent.run()` now returns a tuple — update all assertions to unpack `(result, raw_markdown)`

- [x] T044 Update `teaching_agent/tests/test_kafka_integration.py`:
      - Add `_FakeStreamPublisher`: captures all `StreamTokensEventBody` events in a list
      - Add `stream_publisher=fake_stream_publisher` to handler construction
      - Add `test_streaming_tokens_published_before_completion_event`
      - Add `test_stream_complete_sentinel_published_on_success`
      - Add `test_stream_complete_sentinel_published_on_error`
      - Add `test_diagram_field_in_stream_events`
      - Update `test_completion_event_preserves_request_correlation`: verify `content` is raw markdown string

- [x] T045 Update `teaching_agent/tests/conftest.py`:
      - Patch `teaching_agent.agent.call_llm_stream` instead of `teaching_agent.agent.call_llm`
      - Mock yields tuples: intermediate chunks `(delta, 0)`, final chunk `(last_delta, tokens_used)`
      - Table output still captures `model`, `tokens_used`, `time_s`

---

### P4-E: Validation

- [x] T046 Run full test suite: `python -m pytest teaching_agent/tests/ -q` — all tests pass
- [x] T047 Run sample outputs: `PYTHONPATH=. python teaching_agent/tests/run_samples.py` —
      verify all 9 outputs are in markdown format with correct bold section headers
- [x] T048 Manual end-to-end validation (requires worker running + Kafka up):
      publish a `TeachingRequestEvent`; verify `StreamTokensEventBody` events on `"stream-tokens"`
      with correct `field` keys; verify `TeachingCompletionEvent.content` is raw markdown on
      `"teaching-complete"`

---

---

### P4-F: RAG Context Priority Correction

**Purpose**: Correct an implementation error from Phase 1 where `context` was labelled and treated as "prior session history" rather than RAG-compiled course material. The fix updates all three prompt templates so the LLM is instructed to treat `context` as the primary reference source.

- [x] T049 Update `teaching_agent/prompts.py` — fix RAG context handling across all three mode prompts (FR-036):
      - Rename label from `"Prior session context: {context}"` to `"Reference material (compiled from course documents):\n{context}"`
      - Add explicit priority instruction immediately after the label (before the structure section):
        `"When reference material is provided above, use it as your PRIMARY source. Ground your explanation in that content. Only draw on general knowledge where the reference material is silent or incomplete."`
      - Replace trailing rule in Rules section:
        - Beginner: `"If prior session context is provided, briefly connect it to the new topic."` → `"If no reference material is provided above, explain from general knowledge."`
        - Intermediate: `"If prior session context is provided, build on it explicitly."` → `"If no reference material is provided above, explain from general knowledge."`
        - Advanced: `"If prior session context is provided, reference it where directly relevant."` → `"If no reference material is provided above, explain from general knowledge."`

**Checkpoint**: Run `PYTHONPATH=. python teaching_agent/tests/verify_phase4.py` with a non-empty `rag_compiled` context and verify the explanation draws from the provided material.

---

### P4-G: Mermaid Label Sanitizer (FR-045, FR-046)

**Purpose**: Fix Mermaid diagrams not rendering on the frontend when node labels contain
special characters (`:`, `()`, `%`, etc.). Two-part fix: a prompt instruction (prevention)
and a post-processing sanitizer in `helpers.py` called in `_resolve_diagram()` (defense-in-depth).

- [x] T061 [FR-046] Update `teaching_agent/prompts.py`:
      Add one rule line to the Rules section of all three mode prompts:
      `"- Always wrap Mermaid node label text in double quotes, e.g. A[\"Label text here\"]. Required when labels contain colons, parentheses, or special characters."`
      Placement: last bullet in the Rules list for each prompt.

- [x] T062 [FR-045] Add `sanitize_mermaid_labels(diagram: str) → str` to `teaching_agent/helpers.py`:
      - Regex `r'\[([^\[\]\n]+)\]'` matches square-bracket node labels
      - Skip labels already wrapped in double quotes (`inner.startswith('"') and inner.endswith('"')`)
      - If label contains any char from `frozenset(':(){}#%÷×≤≥≠')`, wrap in double quotes
      - Escape any existing `"` inside the label text as `&quot;` before wrapping
      - All other labels returned unchanged

- [x] T063 [FR-045] Update `teaching_agent/agent.py` — `_resolve_diagram()`:
      Call `sanitize_mermaid_labels(diagram_raw)` before `validate_mermaid()` on the initial
      check path. Similarly sanitize the retry result before its `validate_mermaid()` call.
      Import `sanitize_mermaid_labels` from `teaching_agent.helpers`.

- [x] T064 [FR-045] Add unit tests to `teaching_agent/tests/test_teaching_agent.py`:
      - `test_sanitize_labels_wraps_colon_in_label` — `A[Start: Step]` → `A["Start: Step"]`
      - `test_sanitize_labels_wraps_parens_in_label` — `A[Result (2 items)]` → `A["Result (2 items)"]`
      - `test_sanitize_labels_skips_already_quoted` — `A["Already: Quoted"]` → unchanged
      - `test_sanitize_labels_no_special_chars_unchanged` — `A[Plain label]` → unchanged
      - `test_sanitize_labels_escapes_inner_quotes` — `A[Say "hello"]` → `A["Say &quot;hello&quot;"]`

**Checkpoint**: All 5 new unit tests pass; existing 57 tests pass unchanged; a diagram with
`A[Start: Flip a Coin]` is correctly transformed to `A["Start: Flip a Coin"]` by the sanitizer.

---

---

## Phase 5: Multi-Turn Conversation (US7) — Planned

**Goal**: Let the Teaching Agent answer follow-up queries with prior conversation as context.
The Planner sends prior turns in a new optional `chat_history` field; the agent threads them
into the LLM message list ahead of the current structured prompt. Every turn keeps the
existing 4-section structured output — no follow-up branch, no conversational mode, no
auto-detection. Empty `chat_history` (default) reproduces single-turn behavior exactly.

**All Phase 5 tasks require explicit user approval before implementation. One task at a time.**

---

### P5-A: Schema (Blocking Prerequisite)

**Purpose**: Add `chat_history` to the inbound event and the agent input. All other P5 tasks depend on this.

- [x] T050 [US7] Add `chat_history` to `project/schemas.py` (Teaching Agent section):
      - `TeachingRequestEvent`: `chat_history: list[dict] = Field(default_factory=list)` —
        prior turns, oldest→newest, each `{"role": "user"|"assistant", "content": str}`,
        EXCLUDING the current query
      - `TeachingAgentInput`: mirror the same field with the same default
      - default `[]` keeps every existing caller/test and the first-query path unchanged
      - (decision §4.1) optionally add a light validator rejecting entries without a valid
        `role` or with empty `content`; default recommendation = `list[dict]` + light validator

**Checkpoint**: `python -c "from project.schemas import TeachingAgentInput; assert TeachingAgentInput(topic='x', output_mode='beginner').chat_history == []"` passes

---

### P5-B: Message Building (Core Change)

**Purpose**: Make message construction history-aware. This is the only behavioral change.

- [x] T051 [US7] Update `teaching_agent/helpers.py`:
      `build_messages(prompt: str, chat_history: list[dict] | None = None) -> list[dict[str, str]]`
      returns `[*(chat_history or []), {"role": "user", "content": prompt}]`.
      Backward compatible: `chat_history=None`/`[]` → `[{"role": "user", "content": prompt}]`,
      identical to today; the structured prompt stays the final user message.

**Checkpoint**: `python -m pytest teaching_agent/tests/test_teaching_agent.py -q -k "build_messages"` passes

---

### P5-C: Agent + Handler Wiring

**Purpose**: Pass `chat_history` from the event through `run()` into `build_messages()`.

- [x] T052 [US7] Update `teaching_agent/agent.py`: in `run()`, change the structured-step
      message construction from `messages = build_messages(prompt)` to
      `messages = build_messages(prompt, agent_input.chat_history)`. No branch, no new method;
      Steps 5–9 (extractor, parse, diagram, reflection N=0, assembly) unchanged.

- [x] T053 [US7] Update `teaching_agent/handlers.py`: in `process_request()`, add
      `"chat_history": event.chat_history` to the dict passed to `agent.run()`. token_callback,
      publish flow, sentinel, and `build_completion_event` unchanged.

**Checkpoint**: `python -m pytest teaching_agent/tests/test_kafka_integration.py -q` passes

---

### P5-D: Tests

**Purpose**: Cover the multi-turn path; confirm single-turn regression is intact.

- [x] T054 [US7] Update `teaching_agent/tests/test_teaching_agent.py`:
      - `build_messages` regression: `None`/`[]` → single user message
      - `build_messages` multi-turn: prior turns prepended in order, current prompt last
      - schema: `chat_history` defaults to `[]`; populated entries parse; (if validated) bad
        role / empty content rejected
      - `run()` with non-empty `chat_history`: prior turns appear in the messages fed to
        `call_llm_stream`; output is still the parsed 4-section `TeachingContent`; `status == "ok"`
      - existing single-turn tests stay green unchanged

- [x] T055 [US7] Update `teaching_agent/tests/test_kafka_integration.py`:
      - handler maps `event.chat_history` into `run()` (assert via a capturing fake agent)
      - request with `chat_history` → exactly one `teaching-complete` publish + stream tokens
        + done sentinel (publish-once preserved)
      - backward compat: event without `chat_history` → identical to today

---

### P5-E: Optional Hardening, Docs & Validation

- [ ] T056 [US7] (optional, decision §4.3) Defensive history cap:
      `teaching_agent/config.py` `get_max_history_turns()` reading `TEACHING_MAX_HISTORY_TURNS`
      (unset → no cap); `agent.run()` keeps the most recent N turns before `build_messages`.
      Skip unless a cap is wanted.

- [ ] T057 [US7] (optional, decision §4.4) Conversation-aware prompt nudge in
      `teaching_agent/prompts.py` — one line per `PROMPT_BY_MODE` template. Add only if quality
      testing shows the model drifting between chat and structured output.

- [x] T058 [US7] Update docs for `chat_history`: `specs/002-teaching-agent/data-model.md`
      (input/event schema) and `specs/002-teaching-agent/contracts/teaching-agent-contract.md`
      (input contract) updated. `CLAUDE.md` not changed — it does not document the Teaching
      input shape (RAG-focused).

- [x] T059 [US7] Run offline suite + lint:
      offline subset (test_teaching_agent.py + test_kafka_integration.py = 55 passed;
      test_stream_parser.py + test_worker_runtime.py = 13 passed) green; `ruff check` on all
      changed files passes. (Pre-existing ruff errors in untouched `test_context_priority.py`
      are out of scope per the Phase-5-only decision.)

- [ ] T060 [US7] Manual two-turn validation (real LLM, gated): first query (structured output)
      → follow-up with turn 1 in `chat_history`; verify the answer references the prior turn
      while still returning the 4-section format.

---

---

---

## Phase 6: Guardrail Classification (US8) — Planned

**Goal**: Insert a fast LLM classification step (Step 0) before the main teaching pipeline.
Non-learning inputs (`greeting`, `off_topic`, `unclear`) receive canned responses without
invoking the main LLM call. `valid_question` inputs proceed to Step 1 unchanged.
Follow-up queries (non-empty `chat_history`) skip the guardrail entirely.
No schema changes required — `content=None` is already valid; canned text travels as `raw_markdown`.

**All Phase 6 tasks require explicit user approval before implementation. One task at a time.**

---

### P6-A: Prompt (Blocking Prerequisite)

**Purpose**: Add the classification prompt to `teaching_agent/prompts.py`. All other Phase 6 tasks depend on it.

- [ ] T065 [US8] Add `GUARDRAIL_PROMPT` to `teaching_agent/prompts.py`:
      A tight classification prompt that instructs the LLM to return ONLY a JSON object:
      `{"category": "greeting|off_topic|unclear|valid_question", "reason": "<one line>"}`.
      No markdown, no fences, no other text. The prompt lists the 4 categories with clear
      decision criteria (e.g. "greeting: a salutation with no learning intent").
      Uses `response_format={"type": "json_object"}` in the LLM call.

**Checkpoint**: `python -c "from teaching_agent.prompts import GUARDRAIL_PROMPT; print(GUARDRAIL_PROMPT[:80])"` prints first 80 chars

---

### P6-B: Config (Blocking Prerequisite)

**Purpose**: Add guardrail model config to `teaching_agent/config.py`. Depends on P6-A.

- [ ] T066 [US8] Add `get_guardrail_config()` to `teaching_agent/config.py`:
      - Reads `TEACHING_GUARDRAIL_ENABLED` (default `"true"`); returns `None` when disabled
      - Reads `TEACHING_GUARDRAIL_MODEL` → fallback `TEACHING_MODEL` (raises `RuntimeError`
        if neither set, consistent with `get_llm_config` pattern)
      - Reads `TEACHING_GUARDRAIL_API_KEY` → fallback `TEACHING_API_KEY` (optional)
      - Returns `LLMConfig` with `max_tokens=128`, `temperature=0.0` (classification is
        deterministic; no temperature variation needed)

**Checkpoint**: `python -c "from teaching_agent.config import get_guardrail_config"` imports cleanly

---

### P6-C: Guardrail Module

**Purpose**: New `teaching_agent/guardrail.py` with the classifier and canned responses. Depends on P6-A + P6-B.

- [ ] T067 [US8] Create `teaching_agent/guardrail.py`:
      - `_VALID_CATEGORIES: frozenset[str] = frozenset({"greeting", "off_topic", "unclear", "valid_question"})`
      - `_CANNED_RESPONSES: dict[str, str]` with exact canned text per category
        (greeting / off_topic / unclear; no entry for valid_question)
      - `get_canned_response(category: str) → str | None`:
        returns the canned text or `None` if category is `valid_question` or unknown
      - `GuardrailClassifier` class:
        - `classify(topic: str, config: LLMConfig) → str`:
          builds `[{"role": "user", "content": GUARDRAIL_PROMPT.format(topic=topic)}]`;
          calls `call_llm(messages, config)` (the existing non-streaming call);
          parses response as JSON; extracts `category`; validates it is in `_VALID_CATEGORIES`;
          returns category string on success;
          returns `"valid_question"` on any exception or if `category` key absent/invalid (fail-open)

**Checkpoint**: `python -c "from teaching_agent.guardrail import GuardrailClassifier, get_canned_response; print(get_canned_response('greeting'))"` prints the greeting text

---

### P6-D: Agent Wiring

**Purpose**: Add Step 0 to `TeachingAgent.run()`. Depends on P6-A + P6-B + P6-C.

- [ ] T068 [US8] Update `teaching_agent/agent.py`:
      - Add `from teaching_agent.guardrail import GuardrailClassifier, get_canned_response`
      - Add `from teaching_agent.config import get_guardrail_config`
      - In `run()`, after input validation (Step 1) and BEFORE loading the main LLM config (Step 2),
        add Step 0 — Guardrail check:
        ```python
        # Step 0: Guardrail classification (skip when chat_history non-empty)
        if not agent_input.chat_history:
            guardrail_config = get_guardrail_config()
            if guardrail_config is not None:
                try:
                    category = GuardrailClassifier().classify(topic, guardrail_config)
                except Exception:
                    category = "valid_question"
                canned = get_canned_response(category)
                if canned is not None:
                    token_callback("explanation", canned)
                    return TeachingAgentOutput(
                        status="ok",
                        output_mode=OutputMode(output_mode),
                        content=None,
                        metadata=TeachingMetadata(
                            topic=topic,
                            tokens_used=0,
                            model=guardrail_config.model,
                        ),
                    ), canned
        ```
      - All existing steps 2–8 are unchanged.
      - `get_guardrail_config()` returning `None` means disabled — skip the block.
      - Any exception from `classify()` → `"valid_question"` (covered by the try/except above).

**Checkpoint**: `TEACHING_MODEL=<model> PYTHONPATH=. python -c "
from teaching_agent.agent import TeachingAgent
result, raw = TeachingAgent().run({'topic': 'Hi', 'output_mode': 'beginner', 'context': ''}, lambda f, t: print(f, t))
print(result.status, result.content, raw[:40])
"` prints `ok None Hi there!...`

---

### P6-E: Tests

**Purpose**: Full offline test coverage for guardrail feature.

- [ ] T069 [US8] Create `teaching_agent/tests/test_guardrail.py`:
      - `test_classify_greeting` — monkeypatch `teaching_agent.guardrail.call_llm` to return
        `('{"category": "greeting", "reason": "says hi"}', 10)`;
        assert `GuardrailClassifier().classify("Hi", config)` returns `"greeting"`
      - `test_classify_off_topic` — same pattern, category `"off_topic"`
      - `test_classify_unclear` — same pattern, category `"unclear"`
      - `test_classify_valid_question` — category `"valid_question"`
      - `test_classify_fails_open_on_exception` — monkeypatch raises `RuntimeError`;
        assert returns `"valid_question"`
      - `test_classify_fails_open_on_bad_json` — monkeypatch returns `("not json", 10)`;
        assert returns `"valid_question"`
      - `test_classify_fails_open_on_missing_category_key` — returns `('{"reason": "x"}', 10)`;
        assert returns `"valid_question"`
      - `test_get_canned_response_greeting` — returns non-empty string
      - `test_get_canned_response_valid_question` — returns `None`

- [ ] T070 [US8] Update `teaching_agent/tests/test_teaching_agent.py`:
      - `test_guardrail_intercepts_greeting`:
        monkeypatch `teaching_agent.guardrail.call_llm` to return greeting category;
        call `TeachingAgent().run({"topic": "Hi", ...}, token_callback)`;
        assert `result.status == "ok"`, `result.content is None`,
        token_callback called once with `("explanation", <greeting text>)`,
        `raw_markdown` equals greeting canned text
      - `test_guardrail_intercepts_off_topic`:
        same but category `"off_topic"`, assert off-topic canned text
      - `test_guardrail_skipped_when_chat_history_non_empty`:
        monkeypatch guardrail `call_llm` to return greeting; also monkeypatch
        `teaching_agent.agent.call_llm_stream` to return normal markdown;
        pass `chat_history=[{"role": "user", "content": "prev"}]`;
        assert `result.content` is not None (full pipeline ran)
      - `test_guardrail_fails_open_on_exception`:
        monkeypatch guardrail `call_llm` to raise `RuntimeError`;
        also monkeypatch main `call_llm_stream` to return normal markdown;
        assert full pipeline ran (`result.content` not None)

---

### P6-F: Docs & Validation

- [ ] T071 [US8] Update `CLAUDE.md` — add guardrail env vars under Teaching Agent env var table:
      `TEACHING_GUARDRAIL_ENABLED` (default `true`) and `TEACHING_GUARDRAIL_MODEL`
      (falls back to `TEACHING_MODEL`); brief description in the same table format

- [ ] T072 [US8] Run full offline test suite and confirm all tests pass:
      `python -m pytest teaching_agent/tests/ -q`
      (guardrail tests use monkeypatched `call_llm` — no real LLM required)

---

---

## Phase 7: Example Verbosity Constraint (FR-051) — Planned

**Goal**: Prevent the LLM from choosing large input values in the `**Example**` section
(e.g. `fibonacci(50)`) that produce exhaustive step-by-step computation traces consuming the
full 4096-token ceiling and truncating the rest of the response. A single rule line added to
each mode prompt caps example inputs at small, illustrative sizes.

**All Phase 7 tasks require explicit user approval before implementation. One task at a time.**

---

- [ ] T073 [FR-051] Update `teaching_agent/prompts.py` — add one rule line to the Rules section
      of all three mode prompts (`BEGINNER_PROMPT`, `INTERMEDIATE_PROMPT`, `ADVANCED_PROMPT`):
      `"- In examples, use small, illustrative input values (e.g. n ≤ 10 for recursive algorithms,
      short strings for string operations). Never show a full computation trace for a large input —
      demonstrate the concept, not the arithmetic."`
      Placement: second-to-last bullet in the Rules list for each prompt (before the
      `"If no reference material is provided above, explain from general knowledge."` line).

- [ ] T074 [FR-051] Run full offline test suite to confirm no regressions:
      `python -m pytest teaching_agent/tests/ -q`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: Complete ✅
- **P2-A (T017–T019)**: No dependencies — start immediately; BLOCKS all other P2 phases
- **P2-B (T020)**: Depends on P2-A (needs `TeachingCompletionEvent` for `publish_teaching_complete`)
- **P2-C (T021)**: Depends on P2-A + P2-B (needs Kafka types and event schemas)
- **P2-D (T022)**: Depends on P2-B + P2-C (needs kafka.py and handlers.py)
- **P2-E (T023–T024)**: Depends on P2-B + P2-C + P2-D (tests all three files)
- **P2-F (T025–T034)**: Depends on P2-E completion
- **Phase 3 (T035–T053)**: P3-A→P3-E built per the Phase 3 Dependencies block;
  P3-F (T047–T053) are doc-reconciliation / added-coverage tasks, mostly independent
- **Phase 5 (T050–T060)**: P5-A (T050) BLOCKS all of P5; P5-B (T051) depends on P5-A;
  P5-C (T052–T053) depends on P5-A + P5-B; P5-D (T054–T055) depends on P5-C; P5-E
  (T056–T060) depends on P5-D. T056/T057 are optional.

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
(Phase 3) T035 → T036 → T037/T038 → T039/T040 → T041 → T042 → T043–T053
(Phase 5) T050 → T051 → T052 → T053 → T054 → T055 → [checkpoint] → T056–T060
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
