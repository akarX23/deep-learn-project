# Quiz Agent

Synchronous two-phase agent: **generate** a quiz from teaching content, then **evaluate** submitted answers.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `QUIZ_MODEL` | `gpt-4o-mini` | LiteLLM model string |
| `QUIZ_API_BASE` | — | Optional API base URL (required if no API key) |
| `QUIZ_API_KEY` | — | Optional API key (required if no API base) |
| `QUIZ_TEMPERATURE` | `0.2` | Temperature for generation; `0.1` for grading |
| `QUIZ_GENERATION_MAX_TOKENS` | `3000` | Completion token ceiling for question generation |
| `QUIZ_GRADING_MAX_TOKENS` | `1200` | Completion token ceiling for descriptive grading |

At least one of `QUIZ_API_BASE` or `QUIZ_API_KEY` must be set for real LLM calls. Tests monkeypatch `quiz_agent.agent.call_llm` directly and require no environment variables.

## Running the agent (CLI)

```bash
python -m quiz_agent.agent --input quiz_agent/tests/inputs/sample_input.json
```

## Running tests

```bash
pytest quiz_agent/tests/test_quiz_agent.py -q
```

## Architecture

| Module | Role |
|---|---|
| `quiz_agent/agent.py` | `QuizAgent` class: `generate(input) → QuizAgentOutput`, `evaluate(quiz, answers) → QuizAgentOutput` |
| `quiz_agent/config.py` | `LLMConfig` dataclass; `get_generation_config()`, `get_grading_config()` |
| `quiz_agent/llm_client.py` | `call_llm(messages, config) → tuple[str, int]` LiteLLM wrapper |
| `quiz_agent/prompts.py` | `QUESTION_GENERATION_PROMPT`, `DESCRIPTIVE_GRADING_PROMPT` |
| `quiz_agent/validators.py` | `validate_question_set(raw, ...) → list[str]` structural checks |
| `quiz_agent/helpers.py` | `score_mcq_single`, `score_mcq_multi`, `build_result`, `parse_generated_quiz`, `build_error_output` |
| `project/schemas.py` | Shared Pydantic v2 schemas: `QuizAgentInput`, `QuizAgentOutput`, `Quiz`, `QuizMetadata`, `UIHints`, `Question`, `MCQOption`, `SubmittedAnswer`, `QuizResult`, `QuestionResult` |

## Two-Phase Lifecycle

```
QuizAgentInput
  → QuizAgent.generate()          # 1 LLM call (generation)
      validate input length
      call LLM → parse JSON
      validate_question_set()     # retry once on deficit
      build_quiz_from_parsed()
  → QuizAgentOutput(status="generated", quiz=Quiz)

Quiz + list[SubmittedAnswer]
  → QuizAgent.evaluate()          # 1 LLM call (grading)
      grade MCQs locally (no LLM)
      batch-grade descriptive answers via single LLM call
      build_result()              # recommended_action derivation
  → QuizAgentOutput(status="evaluated", quiz=Quiz, result=QuizResult)
```
