# Test Fixtures: Quiz Agent

## Files

### `sample_input.json`
Representative `QuizAgentInput` payload with ~110 words of teaching content about Gradient Descent Optimization. Sufficient to pass the 100-word minimum guard in `agent.py`.

Fields: `topic`, `teaching_content`, `mcq_single_count`, `mcq_multi_count`.

## Test Design Notes

- All tests in `test_quiz_agent.py` monkeypatch `quiz_agent.agent.call_llm` — no real LLM calls are made and no API keys are required.
- `SAMPLE_QUESTION_GENERATION_RESPONSE`: a pre-built valid JSON payload with 5 mcq-single (max_points=1), 3 mcq-multi (max_points=2), and 4 descriptive (max_points=5) questions. Max score = 5×1 + 3×2 + 4×5 = 31.
- `SAMPLE_DESCRIPTIVE_GRADING_RESPONSE`: scores of 4, 5, 3, 4 for questions q9–q12 (max 5 each).
- `_make_quiz()`: builds a minimal Quiz-compatible dict from the sample generation response, suitable for evaluation tests without a live generate() call.
- `_make_submitted_answers(all_correct_mcq=True/False)`: produces a full answer list covering all 12 questions. Set `all_correct_mcq=False` to exercise wrong-answer explanation paths.
