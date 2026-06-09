# Implementation Plan: Quiz Agent

**Branch**: `003-build-quiz-agent` | **Date**: 2026-06-08 | **Spec**: `/specs/003-quiz-agent/spec.md`
**Input**: Feature specification from `/specs/003-quiz-agent/spec.md`

## Summary

Implement a synchronous Quiz Agent that receives a detailed teaching explanation from the
Teaching Agent, generates a structured question set (MCQ single-answer, MCQ multiple-answer,
and exactly 4 descriptive questions), evaluates submitted answers, and returns a scored result
with per-question feedback, per-option wrong-answer explanations, topic deep-dives, and a list
of weak sub-concepts.

The agent uses LiteLLM as the LLM interface through its own `quiz_agent/llm_client.py` module
(not shared with other agents). Configuration is loaded from environment variables. No LangGraph
orchestration is used — the pipeline is a two-phase linear sequence (generate, then evaluate)
that does not require stateful loop orchestration.

Two LLM calls are made per quiz lifecycle:
1. **Question generation**: one call that produces all questions, options, per-option explanations,
   rubrics, and topic deep-dives as a single structured JSON payload.
2. **Descriptive grading**: one batched call that evaluates all 4 descriptive answers against
   their rubrics, returning numeric scores, model answers, and qualitative feedback.

MCQ grading is purely local (no LLM required).

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pydantic v2, litellm>=1.40.0, pytest>=8.0.0 (no new packages beyond existing requirements.txt)
**Storage**: N/A (pure in-memory; caller is responsible for session persistence of the Quiz object)
**Testing**: pytest
**Target Platform**: Linux runtime (local dev and container-ready execution)
**Project Type**: Agent module/library within a multi-agent backend
**Performance Goals**: Question generation ≤ 15s; descriptive grading ≤ 20s on developer hardware under a fast-endpoint model
**Constraints**: Synchronous execution only; two LLM calls per lifecycle (generation + grading); MCQ grading is local; JSON output only; no LangGraph
**Scale/Scope**: One synchronous request per invocation per phase; invoked by the Teaching Agent after content generation

## Constitution Check

*GATE: Must pass before implementation. Re-check after Phase 1 design.*

### Initial Gate Review (Pre-Research)

- Code Quality Gate: PASS. Responsibility boundaries are explicit by module:
  `project/schemas.py`, `quiz_agent/agent.py`, `quiz_agent/llm_client.py`,
  `quiz_agent/prompts.py`, `quiz_agent/validators.py`, `quiz_agent/helpers.py`,
  `quiz_agent/config.py`. No cross-agent module imports.
- Testing Gate: PASS. Planned tests cover: schema validation, MCQ scoring logic,
  descriptive grading, edge cases (short content, partial answers), error response structure,
  and full pipeline integration with monkeypatched LLM calls.
- UX Consistency Gate: PASS. Output format (JSON structure) is stable across invocations.
  Question structure per type is defined and enforced by prompt templates and validators.
- Performance Gate: PASS. Token ceilings define measurable budgets enforced at the
  LiteLLM call boundary. Wall-clock targets are stated and verifiable.
- Maintainability Gate: PASS. Config and prompt templates are centralized in dedicated
  modules. MCQ scoring logic is isolated in `helpers.py`. All non-obvious design decisions
  are documented in this plan.

## Project Structure

### Documentation (this feature)

```text
specs/003-quiz-agent/
├── plan.md                        # This file
├── data-model.md                  # Phase 1 output (to be created)
├── quickstart.md                  # Phase 1 output (to be created)
├── contracts/
│   └── quiz-agent-contract.md     # Phase 1 output (to be created)
├── checklists/
│   └── requirements.md            # Existing
└── tasks.md                       # Phase 2 output
```

### Source Code (repository root)

```text
project/
└── schemas.py           # Add: QuestionType, MCQOption, Question, QuizMetadata, UIHints,
                         #      Quiz, SubmittedAnswer, QuestionResult, QuizResult,
                         #      QuizAgentInput, QuizAgentOutput

quiz_agent/
├── __init__.py
├── agent.py             # QuizAgent class: generate(input) → Quiz,
                         #                  evaluate(quiz, answers) → QuizResult
├── config.py            # LLMConfig dataclass, get_generation_config(), get_grading_config()
├── llm_client.py        # call_llm(messages, config) → tuple[str, int]; second element is
                         #   tokens_used (completion tokens); guards unconfigured calls
├── prompts.py           # QUESTION_GENERATION_PROMPT, DESCRIPTIVE_GRADING_PROMPT constants
├── validators.py        # validate_question_set(raw: dict) → list[str]; structural checks
├── helpers.py           # score_mcq_single(), score_mcq_multi(),
                         # build_result(), parse_generated_quiz()
└── tests/
    ├── __init__.py
    ├── test_quiz_agent.py
    └── inputs/
        └── sample_input.json
```

**Structure Decision**: Single Python agent module following the `rag_agent/` and
`teaching_agent/` layouts. Schemas in `project/schemas.py` (shared contract location).
No new top-level directories. No LangGraph — two sequential LLM calls managed by a plain class.

## Behavior Rules and Requirement Clarifications

These clarifications resolve interpretation questions left open by the spec. They are
binding design decisions, traceable to the listed spec requirements.

### Two-Phase API (FR-001, FR-011, FR-013)

The Quiz Agent exposes two explicit methods on the `QuizAgent` class:

| Method | Input | Output | LLM calls |
|--------|-------|--------|-----------|
| `generate(input: QuizAgentInput) → Quiz` | Teaching content + topic | Full question set with embedded explanations and rubrics | 1 |
| `evaluate(quiz: Quiz, answers: list[SubmittedAnswer]) → QuizResult` | Quiz + learner's answers | Scored result with feedback | 1 (descriptive grading) |

MCQ grading inside `evaluate()` is fully local (pure Python) — no LLM call required.
The single grading LLM call batches all 4 descriptive answers in one prompt.

### Pre-Generated Explanations (FR-011a, FR-012a)

All MCQ explanations (wrong-answer panels, should-have-selected panels, topic deep-dives)
are generated **during question generation** — embedded in the `MCQOption` and `Question`
objects returned by `generate()`. This design:

- Keeps evaluation latency low (MCQ grading is local; no explanation LLM call on submit).
- Grounds explanations in the teaching content at generation time, before any learner
  interaction.
- Means the generation LLM call carries a higher token budget (~3000 completion tokens)
  to accommodate full explanation coverage.

### Token-Ceiling Semantics (FR-002, FR-013)

| Call | `max_tokens` | What is bounded |
|------|-------------|-----------------|
| Question generation | 3000 | All questions + options + rubrics + explanations + topic deep-dives |
| Descriptive grading | 1200 | Scores + model answers + qualitative feedback for all 4 questions |

Completion token counts are reported in `QuizAgentOutput.metadata.tokens_used`.
`tokens_used` is set independently per phase: the **generation output** reports completion
tokens from the generation call; the **evaluation output** reports completion tokens from
the descriptive grading call. It is never a cumulative sum across both calls.
Teaching content passed to `generate()` is truncated by an input guard in `agent.py` if it
exceeds a safe prompt-token ceiling, to prevent total request size from exceeding the model
window.

### Question Count Rules (FR-003, FR-006, FR-007, FR-010)

The agent targets this default question distribution; the exact MCQ counts are controlled
via a configurable parameter (`QuizAgentInput.mcq_single_count`, `mcq_multi_count`) with
these defaults:

| Type | Default count | Min |
|------|---------------|-----|
| `mcq-single` | 5 | 3 |
| `mcq-multi` | 3 | 2 |
| `descriptive` | 4 | 4 (fixed by spec) |

If the generated question set does not meet the minimums, `validators.py` reports the deficit
and `agent.py` retries generation once. A second failure returns `status: "error"`.

### Re-generation on Failure (spec Edge Cases, FR-003)

| Failure mode | Handling |
|--------------|----------|
| Teaching content too short (< 100 words) | Input validation fails before any LLM call; `status: "error"` with message "Teaching content too short to generate a complete quiz" |
| Generated set below minimum question counts | Retry generation once; second failure → `status: "error"` |
| Duplicate question detected | `validators.py` flags duplicates; agent retries once |
| LLM call fails or returns non-JSON | `status: "error"`, `tokens_used: 0`, no unhandled exception |

### MCQ Scoring Semantics (FR-011, FR-012)

| Type | Scoring rule |
|------|-------------|
| `mcq-single` | 1 point if the single selected option is the correct option; 0 otherwise |
| `mcq-multi` | `max(0, correct_selected − incorrect_selected) / total_correct_options` × max_points, floored at 0 |

Implemented in `helpers.py::score_mcq_single()` and `helpers.py::score_mcq_multi()`.

### Unanswered Questions on Evaluate (spec Edge Cases)

- MCQ with no selected options: scored 0. No error raised.
- Descriptive with empty/blank text: sent to grading LLM as empty string; rubric scoring
  reflects the absence of content naturally. No error raised.
- Partial answer submission (subset of questions answered): valid input; unsubmitted questions
  treated as empty/no-selection.

### Status Semantics (FR-024)

| `QuizAgentOutput.status` | Condition |
|--------------------------|-----------|
| `"generated"` | `generate()` completed with a valid question set meeting minimum counts |
| `"evaluated"` | `evaluate()` completed with a valid `QuizResult` |
| `"error"` | Any unrecoverable failure in either phase |

### Recommended Next Action Derivation (FR-015)

Computed deterministically in `helpers.py::build_result()` from `overall_percentage`:

| Percentage range | `recommended_action` |
|-----------------|----------------------|
| < 50% | `"re-teach"` |
| 50–74% | `"practice-more"` |
| ≥ 75% | `"advance"` |

No LLM involvement.

## Complexity Tracking

No constitution violations identified. Complexity is justified by:
- Two question-type categories (MCQ and descriptive) requiring distinct scoring strategies.
- Pre-generated per-option explanations embedded in the question structure (direct spec requirement FR-011a, FR-012a).
- Batched descriptive grading in a single LLM call (performance constraint).
- Input guard on teaching content length (robustness requirement from spec edge cases).

All complexity is traceable to spec requirements rather than architectural overhead.

## Scope Boundary: Frontend and Deferred Requirements

This plan covers the **backend Quiz Agent module only**. The following spec requirements
are UI-layer or persistence concerns outside the current iteration scope:

| FR | Requirement | Deferral reason |
|---|---|---|
| FR-004 | Quiz button trigger in Teaching Agent UI | Frontend integration |
| FR-008 | Live word-count indicator in text area | Frontend UI component |
| FR-016 | Visual language / design system compliance | Frontend styling |
| FR-017 | Single scrollable view with progress indicator | Frontend layout |
| FR-018 | `<input type="radio">` / `<input type="checkbox">` rendering | Frontend HTML |
| FR-019 | Live word-count display (`"87 / ~150 words"`) | Frontend UI component |
| FR-020 | Submit button disabled until all MCQs answered | Frontend form validation |
| FR-021 | Inline validation + scroll to first unanswered MCQ | Frontend form validation |
| FR-022 | WCAG 2.1 Level AA keyboard / screen-reader navigation | Frontend accessibility |
| FR-023 | `sessionStorage` persistence of quiz state | Frontend session management |
| FR-025 | Retake flow (new generation call on button click) | Frontend UX + agent call |
| FR-026 | Quiz history per topic | Future work — requires persistent storage layer; contradicts current `Storage: N/A` constraint; deferred to v2 |

The backend agent is responsible only for producing and evaluating schema-valid `QuizAgentOutput`
payloads. Session persistence, rendering, and form-control behaviour are the responsibility
of the frontend integration layer.
