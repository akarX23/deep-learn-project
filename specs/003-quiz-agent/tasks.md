# Tasks: Quiz Agent

**Input**: Design documents from `/specs/003-quiz-agent/`
**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: Tests are required for this feature and are included in each user story.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`US1`, `US2`, `US3`) for story-phase tasks only
- All tasks include exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package structure and baseline tooling for the quiz agent module.

- [ ] T001 Create package directory and init file in `quiz_agent/__init__.py`
- [ ] T002 Create test directory structure in `quiz_agent/tests/__init__.py` and `quiz_agent/tests/inputs/.gitkeep`
- [ ] T003 [P] Add pytest configuration entry for quiz_agent tests in `pytest.ini`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared contracts and core abstractions required by all user stories.

**⚠️ CRITICAL**: No user story implementation starts before this phase completes.

- [ ] T004 Add `QuestionType` enum, `MCQOption`, `Question`, `Quiz`, `SubmittedAnswer`, `QuestionResult`, `QuizResult`, `QuizAgentInput`, and `QuizAgentOutput` schemas to `project/schemas.py`
- [ ] T005 [P] Implement `LLMConfig` dataclass and `get_generation_config()` / `get_grading_config()` loaders in `quiz_agent/config.py`
- [ ] T006 [P] Implement unified LiteLLM call wrapper `call_llm(messages, config) → str` with unconfigured-call guard in `quiz_agent/llm_client.py`
- [ ] T007 [P] Define `QUESTION_GENERATION_PROMPT` and `DESCRIPTIVE_GRADING_PROMPT` constants in `quiz_agent/prompts.py`
- [ ] T008 [P] Implement `score_mcq_single()`, `score_mcq_multi()`, `build_result()`, and `parse_generated_quiz()` helpers in `quiz_agent/helpers.py`
- [ ] T009 [P] Implement `validate_question_set(raw: dict) → list[str]` structural validator in `quiz_agent/validators.py`
- [ ] T010 Wire quiz_agent module exports in `quiz_agent/__init__.py`

**Checkpoint**: Shared schemas, config, LLM abstraction, helpers, and validator are ready for story work.

---

## Phase 3: User Story 1 — Generate Quiz from Teaching Content (Priority: P1) 🎯 MVP

**Goal**: Accept teaching content, call the LLM once, parse and validate the returned question set,
and return a `Quiz` object containing MCQ single-answer, MCQ multiple-answer, and exactly 4 descriptive
questions with pre-embedded explanations, rubrics, and topic deep-dives.

**Independent Test**: Call `QuizAgent.generate()` with a monkeypatched LLM response and confirm the
returned `Quiz` contains the correct question types, option structures, and embedded explanation fields.

### Tests for User Story 1 (REQUIRED)

- [ ] T011 [P] [US1] Add fixture loader for sample teaching content and expected question structure in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T012 [P] [US1] Implement `test_generate_returns_valid_quiz_schema` — verifies returned `Quiz` satisfies `QuizAgentOutput` schema in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T013 [P] [US1] Implement `test_generate_question_type_counts` — verifies correct counts of `mcq-single`, `mcq-multi`, and `descriptive` questions in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T014 [P] [US1] Implement `test_mcq_single_has_four_options` — verifies every `mcq-single` question has exactly 4 options in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T015 [P] [US1] Implement `test_mcq_multi_has_four_to_six_options` — verifies every `mcq-multi` question has 4–6 options in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T016 [P] [US1] Implement `test_mcq_options_have_explanations` — verifies each option carries a `wrong_explanation` or `correct_explanation` field and each question carries a `topic_deep_dive` in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T017 [US1] Implement `test_descriptive_questions_have_rubric` — verifies each `descriptive` question includes a non-empty `rubric` field in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T018 [US1] Implement `test_generate_short_content_returns_error` — verifies that teaching content under the minimum length returns `status: "error"` without an LLM call in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T019 [US1] Implement `test_generate_llm_failure_returns_error` — verifies that an LLM exception yields `status: "error"` and no unhandled exception in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T020 [US1] Implement `test_generate_retries_on_invalid_question_set` — verifies the agent retries once when `validate_question_set` reports deficits, then errors on second failure in `quiz_agent/tests/test_quiz_agent.py`

### Implementation for User Story 1

- [ ] T021 [US1] Implement teaching-content input guard (length check, truncation ceiling) in `quiz_agent/agent.py`
- [ ] T022 [US1] Implement `QuizAgent.generate()`: assemble generation prompt, call LLM, parse JSON response via `parse_generated_quiz()` in `quiz_agent/agent.py`
- [ ] T023 [US1] Integrate `validate_question_set()` into `generate()` with one retry on deficit, returning `status: "error"` on second failure in `quiz_agent/agent.py`
- [ ] T024 [US1] Add sample input fixture with representative teaching content in `quiz_agent/tests/inputs/sample_input.json`

**Checkpoint**: Quiz generation, validation, and error-path handling are working independently.

---

## Phase 4: User Story 2 — Evaluate Answers and Produce Scored Results (Priority: P2)

**Goal**: Accept a `Quiz` and a list of `SubmittedAnswer` objects, grade MCQ answers locally,
batch-grade all 4 descriptive answers via one LLM call, and return a `QuizResult` with overall
score, section subtotals, per-question feedback, per-option explanations, weak sub-concepts,
and a recommended next action.

**Independent Test**: Call `QuizAgent.evaluate()` with a fixed `Quiz` and known answers (monkeypatched
grading LLM) and confirm `QuizResult` scores match expected values for all MCQ types and descriptive grading.

### Tests for User Story 2 (REQUIRED)

- [ ] T025 [US2] Implement `test_score_mcq_single_correct` — verifies a correct single-answer selection scores 1 point in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T026 [US2] Implement `test_score_mcq_single_incorrect` — verifies an incorrect single-answer selection scores 0 in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T027 [US2] Implement `test_score_mcq_multi_partial_credit` — verifies partial-credit formula for multi-answer MCQ in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T028 [US2] Implement `test_score_mcq_multi_floored_at_zero` — verifies score does not go negative when more wrong than right in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T029 [US2] Implement `test_evaluate_returns_valid_result_schema` — verifies returned `QuizResult` satisfies schema with overall_score, mcq_subtotal, descriptive_subtotal, and weak_sub_concepts in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T030 [US2] Implement `test_evaluate_wrong_mcq_exposes_explanations` — verifies per-option explanation panels and topic_deep_dive are present in `QuestionResult` for wrong/missed options in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T031 [US2] Implement `test_evaluate_recommended_action_thresholds` — verifies `recommended_action` values across the three percentage bands in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T032 [US2] Implement `test_evaluate_empty_descriptive_answer` — verifies blank descriptive answers are sent to grading LLM and produce a valid (low) score without errors in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T033 [US2] Implement `test_evaluate_unanswered_mcq_scores_zero` — verifies MCQ with no selection scores 0 in `quiz_agent/tests/test_quiz_agent.py`

### Implementation for User Story 2

- [ ] T034 [US2] Implement `QuizAgent.evaluate()`: route submitted answers by question type in `quiz_agent/agent.py`
- [ ] T035 [US2] Integrate `score_mcq_single()` and `score_mcq_multi()` for all MCQ answers in `quiz_agent/agent.py`
- [ ] T036 [US2] Implement batched descriptive grading: assemble grading prompt (all 4 answers + rubrics), call LLM once, parse grading response in `quiz_agent/agent.py`
- [ ] T037 [US2] Implement `build_result()` in `quiz_agent/helpers.py`: assemble `QuizResult` from per-question outcomes, compute subtotals, derive weak sub-concepts, and compute `recommended_action` in `quiz_agent/helpers.py`
- [ ] T038 [US2] Ensure per-option wrong-answer explanation panels are surfaced from the `MCQOption` fields into `QuestionResult` for all mishandled options in `quiz_agent/agent.py`

**Checkpoint**: Full evaluation pipeline — local MCQ grading, batched descriptive grading, result assembly — is working independently.

---

## Phase 5: User Story 3 — Return Structured Result to Teaching Agent (Priority: P3)

**Goal**: Guarantee that `QuizAgentOutput` is a contract-safe, schema-valid response in both
the generation and evaluation phases, including error paths, and that serialization round-trips
cleanly to support Teaching Agent integration.

**Independent Test**: Verify that `QuizAgentOutput` serializes to JSON and deserializes back
without data loss for both `status: "generated"` and `status: "evaluated"` payloads, and that
error responses carry the expected structure.

### Tests for User Story 3 (REQUIRED)

- [ ] T039 [US3] Implement `test_output_serialization_roundtrip` — serialize `QuizAgentOutput` to JSON and back via Pydantic and verify field equality in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T040 [US3] Implement `test_error_output_schema` — verify `status: "error"` output includes `errors` list and no `quiz`/`result` fields in `quiz_agent/tests/test_quiz_agent.py`
- [ ] T041 [US3] Implement `test_full_pipeline_integration` — monkeypatch both LLM calls (generation + grading), run `generate()` then `evaluate()`, and verify a complete valid `QuizAgentOutput` in `quiz_agent/tests/test_quiz_agent.py`

### Implementation for User Story 3

- [ ] T042 [US3] Implement `build_error_output()` helper for consistent error response assembly in `quiz_agent/helpers.py`
- [ ] T043 [US3] Ensure all error exit paths in `agent.py` return schema-valid `QuizAgentOutput` with `status: "error"` and populated `errors` list
- [ ] T044 [US3] Add synchronous CLI entrypoint for local standalone invocation of the generate phase in `quiz_agent/agent.py`

**Checkpoint**: Contract-safe output, error-path coverage, and Teaching Agent integration handshake are complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality pass across all user stories.

- [ ] T045 [P] Document environment variables and execution workflow in `quiz_agent/README.md`
- [ ] T046 [P] Add fixture assumptions and test coverage notes in `quiz_agent/tests/inputs/README.md`
- [ ] T047 Run full test suite and confirm all quiz_agent tests pass in `quiz_agent/tests/test_quiz_agent.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2; establishes MVP question generation.
- **Phase 4 (US2)**: Depends on US1 (requires a valid `Quiz` object to evaluate).
- **Phase 5 (US3)**: Depends on US1 and US2 (contract covers both phases).
- **Phase 6 (Polish)**: Depends on completion of desired user stories.

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational completion.
- **US2 (P2)**: Depends on US1 `Quiz` schema and generation output.
- **US3 (P3)**: Depends on both US1 and US2 output structures.

### Within Each User Story

- Write tests first and confirm failing expectations before implementation.
- Implement helpers/validators before integrating agent pipeline behaviors.
