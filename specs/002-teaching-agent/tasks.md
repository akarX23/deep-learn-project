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

- [x] T018 Add `TeachingRequestEvent` to `project/schemas.py` (Planner Agent section, shared with the Planner):
      fields: `request_id` (str, required, non-empty), `sid` (str, session identifier),
      `user_prompt` (str, the topic), `user_level` (str, the learner level),
      `rag_compiled` (str, RAG-compiled context, default `""`);
      the worker maps these onto the core pipeline's `topic` / `output_mode` / `context` (see T021)

- [x] T019 Add `TeachingCompletionEvent` to `project/schemas.py` (Planner Agent section, shared with the Planner):
      fields: `request_id` (str, non-empty), `sid` (str), `user_level` (str, non-empty),
      `content` (str, default `""` — the serialized `TeachingContent` JSON, or `""` on error);
      validators: `request_id` / `user_level` non-empty. No `status`, timing, `tokens_used`,
      `model`, `errors`, or `source` fields — the completion event carries content only

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

- [~] T033 Update `.env.local` — add per-mode temperature and effort stubs under Teaching Agent
      section: `TEACHING_BEGINNER_TEMPERATURE`, `TEACHING_INTERMEDIATE_TEMPERATURE`,
      `TEACHING_ADVANCED_TEMPERATURE`, `TEACHING_BEGINNER_EFFORT`, `TEACHING_INTERMEDIATE_EFFORT`,
      `TEACHING_ADVANCED_EFFORT`; variables go in `.env.local` (not `.env.local.example`)
      NOTE: documentation-only — these stubs are NOT currently present in `.env.local`.
      `get_llm_config()` reads `TEACHING_{MODE}_TEMPERATURE` (fallback `TEACHING_TEMPERATURE`,
      default 0.7) and `TEACHING_{MODE}_EFFORT` (optional, `None` when unset) at runtime
      regardless. Re-add the stubs only if per-mode tuning is needed.

- [ ] T034 Remove the dead commented-out `TeachingCompletionEvent` block in
      `project/schemas.py` (Teaching Agent section, ~lines 411–433). It was superseded by the
      active planner-aligned `TeachingCompletionEvent` in the Planner Agent section and is now
      obsolete. Constitution Principle V — remove obsolete code paths.

**Checkpoint**: All Phase 2 tests pass; `"teaching"` and `"teaching-complete"` topics
registered in `project/topics.py`; worker boots and processes messages end-to-end

---

## Phase 3: Reflection Layer — Open

**Spec gate**: Phase 3 spec items (User Story 6, FR-029–FR-037, SC-011–SC-014) are a
PROPOSAL pending team sign-off — see the proposal section in `spec.md`. Do not implement
until ratified.
**Phase gate**: All Phase 2 tasks (T017–T034) complete before starting Phase 3.
**Each task reviewed and approved individually before implementation.**
**N=0 env var setting restores exact Phase 1 behavior at any time.**
**Task numbering**: Phase 3 starts at T035 (T034 is the Phase 2 schema-cleanup task).

---

### P3-A: Schema & Config (Blocking Prerequisites)

- [x] T035 Add `ReflectionCritique` to `project/schemas.py` (Teaching Agent section,
      internal models):
      fields: `quality_score` (int, ge=1, le=10), `issues` (list of dicts with keys
      `field: str`, `issue: str`, `severity: Literal["low","medium","high"]`),
      `revision_instructions` (str);
      validator: `revision_instructions` non-empty if `issues` is non-empty.
      Add `reflection_iterations` (int, ge=0, default=0) field to `TeachingMetadata`.
      **Note**: `ReflectionCritique` is internal — it MUST NOT appear in `TeachingAgentOutput`
      or `TeachingCompletionEvent`.

- [x] T036 Update `teaching_agent/config.py`:
      - Keep `LLMConfig` generic — NO new fields (T047-reconciled design); reflection
        settings are produced by the helper functions below
      - Add `get_reflection_config(output_mode: str) → LLMConfig` function:
        - `model`: `TEACHING_{MODE}_REFLECTION_MODEL` → `TEACHING_REFLECTION_MODEL`
          → `TEACHING_MODEL` (required if nothing else set)
        - `api_key`: `TEACHING_{MODE}_API_KEY` → `TEACHING_API_KEY` (same as generation)
        - `max_tokens`: `TEACHING_REFLECTION_MAX_TOKENS` → default 512
        - `temperature`: same resolution as generation (no separate reflection temperature)
        - `effort`: `None` (reflection calls do not use effort config)
      - Add `get_max_reflection_iterations(output_mode: str) → int` function:
        resolves `TEACHING_{MODE}_MAX_REFLECTION_ITERATIONS` →
        `TEACHING_MAX_REFLECTION_ITERATIONS` → default 1; clamps to ≥ 0

      **Checkpoint**: `get_reflection_config("beginner")` and
      `get_max_reflection_iterations("advanced")` return correctly with env vars set.

---

### P3-B: Prompt Templates

- [ ] T037 [P] Add `REFLECTION_PROMPT_BY_MODE` to `teaching_agent/prompts.py`:
      Three constants (`BEGINNER_REFLECTION_PROMPT`, `INTERMEDIATE_REFLECTION_PROMPT`,
      `ADVANCED_REFLECTION_PROMPT`) + `REFLECTION_PROMPT_BY_MODE` dict.
      Each template:
      - Placeholders: `{topic}`, `{output_mode}`, `{current_output}` (TeachingContent as JSON)
      - Instructs the LLM to return ONLY a JSON object with:
        `quality_score` (int 1–10), `issues` (list of `{field, issue, severity}`),
        `revision_instructions` (string: what to fix, direct instructions for the revision call)
      - Mode-specific critique focus:
        - beginner: clarity of analogy, jargon level, diagram simplicity, example accessibility
        - intermediate: technical accuracy, code correctness, trade-off completeness
        - advanced: formal correctness, edge-case coverage, depth of internals discussion
      - Same JSON-only rules as generation prompts (no markdown fences, escape newlines)

- [ ] T038 [P] Add `REVISION_PROMPT_BY_MODE` to `teaching_agent/prompts.py`:
      Three constants (`BEGINNER_REVISION_PROMPT`, `INTERMEDIATE_REVISION_PROMPT`,
      `ADVANCED_REVISION_PROMPT`) + `REVISION_PROMPT_BY_MODE` dict.
      Each template:
      - Placeholders: `{topic}`, `{output_mode}`, `{context}`, `{current_output}`,
        `{revision_instructions}`
      - Instructs the LLM to return a JSON object with the same structure as the generation
        prompt response: `explanation`, `diagram`, `notes`, `example`
      - Emphasises: "Improve the following output based on the revision instructions.
        Preserve what works. Do not reinvent from scratch."
      - Mode-specific rules mirror the corresponding generation prompt (beginner diagram
        required, intermediate/advanced diagram conditional, etc.)

      **Checkpoint**: Both dicts have keys `"beginner"`, `"intermediate"`, `"advanced"`.

---

### P3-C: Agent Logic

- [ ] T039 Add `_reflect()` method to `TeachingAgent` in `teaching_agent/agent.py`:
      ```
      _reflect(
          current_content: TeachingContent,
          topic: str,
          output_mode: str,
          config: LLMConfig,          # reflection config from get_reflection_config()
          tokens_accumulator: list[int]  # mutable; append critique tokens_used here
      ) → ReflectionCritique | None
      ```
      - Serialise `current_content` to JSON string
      - Render `REFLECTION_PROMPT_BY_MODE[output_mode]` with `{topic}`, `{output_mode}`,
        `{current_output}`
      - Call `call_llm(messages, config)` — wrap in try/except RuntimeError → return None
      - Parse response with `parse_llm_response()` — wrap in try/except ValueError → return None
      - Validate: `quality_score` is int 1–10, `revision_instructions` is non-empty string;
        on validation failure → return None
      - Append `tokens_used` from this call to `tokens_accumulator`
      - Return `ReflectionCritique(**parsed)`

- [ ] T040 Add `_revise()` method to `TeachingAgent` in `teaching_agent/agent.py`:
      ```
      _revise(
          current_content: TeachingContent,
          critique: ReflectionCritique,
          topic: str,
          output_mode: str,
          context: str,
          config: LLMConfig,          # generation config (same model and ceiling as initial)
          tokens_accumulator: list[int]
      ) → TeachingContent | None
      ```
      - Serialise `current_content` to JSON string
      - Render `REVISION_PROMPT_BY_MODE[output_mode]` with all placeholders
      - Call `call_llm(messages, config)` — wrap in try/except RuntimeError → return None
      - Parse with `parse_llm_response()` — wrap in try/except ValueError → return None
      - Validate and resolve diagram via `_resolve_diagram()` (same rules as initial generation)
      - Assemble revised `TeachingContent` — wrap in try/except (ValidationError, KeyError)
        → return None
      - Append `tokens_used` from this call to `tokens_accumulator`
      - Return revised `TeachingContent`

- [ ] T041 Update `TeachingAgent.run()` in `teaching_agent/agent.py` to orchestrate the
      reflection loop:
      - After step 6 (initial diagram resolution), introduce:
        ```python
        tokens_accumulator = [tokens_used]        # start with generation tokens
        current_content = initial_content
        completed_iterations = 0
        max_iterations = get_max_reflection_iterations(output_mode)
        reflection_cfg = get_reflection_config(output_mode)

        for _ in range(max_iterations):
            critique = self._reflect(current_content, topic, output_mode,
                                     reflection_cfg, tokens_accumulator)
            if critique is None:
                break
            revised = self._revise(current_content, critique, topic, output_mode,
                                   context, config, tokens_accumulator)
            if revised is None:
                break
            current_content = revised
            completed_iterations += 1
        ```
      - Replace `tokens_used` with `sum(tokens_accumulator)` when assembling `TeachingMetadata`
      - Add `reflection_iterations=completed_iterations` to `TeachingMetadata` construction

      **Checkpoint**: `TeachingAgent().run({"topic": "binary search", "output_mode": "beginner",
      "context": ""})` with `TEACHING_MAX_REFLECTION_ITERATIONS=0` produces identical output
      to Phase 1; with `=1` adds one reflection cycle.

---

### P3-D: Tests

- [ ] T042 Add reflection tests to `teaching_agent/tests/test_teaching_agent.py`:
      (monkeypatch `call_llm` as in existing tests; no real LLM required)

      - `test_reflection_disabled_when_iterations_zero` — set env
        `TEACHING_MAX_REFLECTION_ITERATIONS=0`; verify `call_llm` called exactly once;
        `metadata.reflection_iterations == 0`

      - `test_reflection_runs_one_iteration_by_default` — monkeypatch `call_llm` to return
        valid generation JSON on first call, valid critique JSON on second call, valid
        revision JSON on third call; verify `call_llm` called exactly 3 times;
        `metadata.reflection_iterations == 1`; output is revision, not initial

      - `test_reflection_falls_back_on_critique_failure` — monkeypatch: first call returns
        valid generation JSON; second call raises RuntimeError; verify `call_llm` called
        exactly 2 times; `metadata.reflection_iterations == 0`; `status == "ok"`;
        output is initial generation

      - `test_reflection_falls_back_on_revision_failure` — monkeypatch: generation OK;
        critique OK; revision raises RuntimeError; verify `call_llm` called exactly 3 times;
        `metadata.reflection_iterations == 0`; `status == "ok"`; output is initial generation

      - `test_reflection_tokens_accumulated_across_all_calls` — monkeypatch: generation
        returns 100 tokens; critique returns 50 tokens; revision returns 120 tokens;
        verify `metadata.tokens_used == 270`

      - `test_reflection_two_iterations` — set env
        `TEACHING_MAX_REFLECTION_ITERATIONS=2`; monkeypatch 5 calls (gen + critique1 +
        rev1 + critique2 + rev2); verify `metadata.reflection_iterations == 2`;
        output is revision2

      - `test_reflection_preserves_diagram_rules_in_revision` — beginner mode; revision
        returns invalid Mermaid; verify fallback template applied; `diagram` is non-null

      - `test_metadata_reflection_iterations_is_zero_when_disabled` — N=0;
        verify `metadata.reflection_iterations == 0`

- [ ] T043 Update `.env.local` — add reflection env var stubs (commented out) under
      Teaching Agent section:
      `TEACHING_MAX_REFLECTION_ITERATIONS`, `TEACHING_REFLECTION_MODEL`,
      `TEACHING_REFLECTION_MAX_TOKENS`; per-mode:
      `TEACHING_BEGINNER_MAX_REFLECTION_ITERATIONS`,
      `TEACHING_INTERMEDIATE_MAX_REFLECTION_ITERATIONS`,
      `TEACHING_ADVANCED_MAX_REFLECTION_ITERATIONS`,
      `TEACHING_BEGINNER_REFLECTION_MODEL`, etc.
      Active default: `TEACHING_MAX_REFLECTION_ITERATIONS=1` (uncommented)

- [ ] T044 Update `CLAUDE.md` — add Reflection section under Teaching Agent:
      - Reflection env vars and defaults
      - How to disable: `TEACHING_MAX_REFLECTION_ITERATIONS=0`
      - `metadata.reflection_iterations` interpretation
      - Wall-clock budget table updated for reflection-on vs reflection-off

---

### P3-E: Validation

- [ ] T045 Run full test suite: `pytest teaching_agent/tests/ -q` — all tests must pass
      including new reflection tests (T042); existing Phase 1 and Phase 2 tests unaffected

- [ ] T046 Manual quality validation (requires real LLM):
      Run `run_samples.py` (or equivalent) for all 3 topics × 3 modes with reflection
      enabled and disabled. Compare outputs. Confirm revised outputs score higher on the
      structured rubric (clarity, structure adherence, example completeness) in ≥ 80% of
      the 9 topic/mode pairs.

---

### P3-F: Plan/Tasks Reconciliation & Added Coverage

These tasks resolve plan.md ↔ tasks.md consistency gaps found in the plan-vs-tasks audit
and add missing validation coverage. T047/T049/T050/T051/T053 are documentation
reconciliations (no production code); T048 and T052 add test/validation coverage and depend
on the T041 implementation existing.

- [ ] T047 [Gap A] Reconcile reflection config design — keep `LLMConfig` generic.
      `LLMConfig` retains only its existing fields (`model`, `api_base`, `api_key`,
      `temperature`, `max_tokens`, `effort`). Reflection settings are produced by helper
      functions, NOT added as `LLMConfig` fields:
      - `get_reflection_config(output_mode) → LLMConfig` returns a config whose `model` and
        `max_tokens` ARE the reflection model and reflection ceiling (default 512).
      - `get_max_reflection_iterations(output_mode) → int` returns the iteration count.
      Doc fixes: update **T036** to DROP the "add `reflection_model`, `reflection_max_tokens`,
      `max_reflection_iterations` fields to `LLMConfig`" line; update **plan.md**'s `config.py`
      Project-Structure entry to DROP "add … reflection_max_tokens field" (the `effort` field
      already exists from T032). No new `LLMConfig` fields are introduced.

- [ ] T048 [Gap B] Add a performance-budget validation task (FR-018-proposed, SC-007;
      Constitution Principle IV — budgets MUST be validated). Measure wall-clock per mode
      (beginner / intermediate / advanced) at N=0 and N=1 against a single pinned model +
      endpoint (FR-018 requires same-model comparison). Easiest path: extend `run_samples.py`
      to time each run and execute both passes.
      - Record results as a documented table (mode × N × seconds), e.g. written to
        `teaching_agent/tests/outputs/perf_<timestamp>.md` — satisfies plan.md's "measured at
        both settings … and documented" clause.
      - Flag budget breaches: N=1 beginner ≤15s / intermediate ≤25s / advanced ≤45s;
        N=0 ≤5 / 10 / 20s. Treat as regression-vs-Phase-1-baseline, not hard pass/fail on a
        slow free-tier endpoint.
      - Confirm no timeout at the advanced 4096-token ceiling on BOTH the generation and
        revision calls.
      Requires a reachable LLM endpoint (gated like T046).

- [ ] T049 [Gap C] Update `data-model.md` and `contracts/teaching-agent-contract.md` for
      Phase 3: add the internal `ReflectionCritique` entity (`quality_score`, `issues`,
      `revision_instructions`) and the new `TeachingMetadata.reflection_iterations` field.
      Note both are internal/metadata only — the external `TeachingAgentOutput` /
      `TeachingCompletionEvent` contract is otherwise unchanged.
      NOTE: while editing, also reconcile any residual stale Kafka-event shapes in those two
      docs left over from the planner-alignment schema change (separate pre-existing drift).

- [ ] T050 [Gap D] Reconcile `_reflect()` / `_revise()` signatures between plan.md and
      tasks.md. T039/T040 pass an explicit `tokens_accumulator: list[int]`; plan.md's
      "Agent Changes" section omits it. Adopt the explicit `tokens_accumulator` parameter as
      the canonical signature and update plan.md's "Agent Changes" to match (one consistent
      choice across both docs).

- [ ] T051 [Gap E] Fix T041's `run()` integration description: the reflection loop runs
      AFTER diagram resolution (step 5) and BEFORE final assembly (step 6) — not "after
      step 6". Replace the `initial_content` placeholder with the actual variable name used
      in `agent.py` (`content`), and align the snippet with the real `run()` structure.

- [ ] T052 [Gap F] Add an SC-014 regression test: with reflection enabled (N≥1), a single
      consumed `TeachingRequestEvent` results in exactly one `TeachingCompletionEvent`
      published. Add to `test_kafka_integration.py` (or T042) using the fake producer
      (assert exactly one `send()` call) with a monkeypatched multi-call `call_llm`. Confirms
      reflection — which lives inside `run()` — does not change the publish-once contract.

- [ ] T053 [Gap G] Refresh stale global sections of tasks.md now that Phase 3 exists:
      - Header **Organization** line — add Phase 3 (Reflection layer).
      - **[Story]** legend — add US6 = Reflection.
      - **Dependencies & Execution Order → Phase Dependencies** — fix "P2-F (T025–T027)" to
        "T025–T034" and add a Phase 3 entry.
      - **Implementation Order** block — extend beyond T027 (or reference the Phase 3
        Dependencies sub-block).

---

### Phase 3 Dependencies

```
T035 (schema) → T036 (config) → T037 (reflection prompts) → T039 (_reflect method)
T035 (schema) → T038 (revision prompts) → T040 (_revise method)
T039 + T040 → T041 (run() orchestration)
T041 → T042 (tests) → T045 (full suite)
T041 → T043 (.env.local) → T044 (CLAUDE.md)
T046 depends on T041 + real LLM env
```

T037 and T038 can run in parallel (different constants in the same file).
T039 and T040 can be developed in parallel (different methods) but both block T041.

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
