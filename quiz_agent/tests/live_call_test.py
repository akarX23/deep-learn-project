"""Live API call test — requires .env with QUIZ_MODEL and provider key set.

Run:
    PYTHONPATH=. python quiz_agent/tests/live_call_test.py

This makes real LLM calls (generation + evaluation). Not part of the automated pytest suite.
"""

import json
from pathlib import Path

from quiz_agent.agent import QuizAgent
from quiz_agent.config import get_generation_config, get_grading_config
from quiz_agent.llm_client import call_llm
from quiz_agent.prompts import QUESTION_GENERATION_PROMPT


# ---------------------------------------------------------------------------
# Step 1: Direct LLM call check (exposes the raw LiteLLM error if any)
# ---------------------------------------------------------------------------
print("=== Step 1: Direct LLM call (bypasses agent error-swallowing) ===")
cfg = get_generation_config()
print(f"model: {cfg.model}  max_tokens: {cfg.max_tokens}")

sample_content = (
    "Gradient descent is an iterative optimization algorithm used to minimize a "
    "loss function by moving in the direction of the steepest descent as defined by "
    "the negative of the gradient. The learning rate controls step size — too high "
    "causes overshooting, too low causes slow convergence. Variants include SGD, "
    "mini-batch GD, and batch GD. Adaptive optimizers such as Adam, RMSProp, and "
    "Adagrad adjust the learning rate per-parameter. Momentum accumulates past "
    "gradients to accelerate descent. Convergence is reached when the gradient "
    "magnitude approaches zero. L1 and L2 regularization penalize large weights."
)

prompt = QUESTION_GENERATION_PROMPT.format(
    teaching_content=sample_content,
    topic="Gradient Descent Optimization",
    mcq_single_count=5,
    mcq_multi_count=3,
)
messages = [{"role": "user", "content": prompt}]

try:
    content, tokens = call_llm(messages, cfg)
    print(f"SUCCESS — tokens_used: {tokens}")
    print(f"Response (first 300 chars): {content[:300]}\n")
except RuntimeError as exc:
    print(f"FAILED — {exc}\n")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# Step 2: Full generate() pipeline
# ---------------------------------------------------------------------------
print("=== Step 2: Full generate() pipeline ===")

sample_input = {
    "topic": "Gradient Descent Optimization",
    "teaching_content": sample_content,
    "mcq_single_count": 5,
    "mcq_multi_count": 3,
}

agent = QuizAgent()
generate_result = agent.generate(sample_input)
print(generate_result.model_dump_json(indent=2))

assert generate_result.status == "generated", (
    f"Expected status='generated', got '{generate_result.status}'\n"
    f"Errors: {generate_result.errors}"
)
assert generate_result.quiz is not None, "quiz should not be None on success"
assert len(generate_result.quiz.questions) == 12, (
    f"Expected 12 questions, got {len(generate_result.quiz.questions)}"
)
assert generate_result.metadata is not None, "metadata should not be None"
assert generate_result.metadata.tokens_used > 0, "tokens_used should be > 0"

print("\ngenerate() PASSED.")


# ---------------------------------------------------------------------------
# Step 3: Full evaluate() pipeline — submit answers for the generated quiz
# ---------------------------------------------------------------------------
print("\n=== Step 3: Full evaluate() pipeline ===")

quiz = generate_result.quiz

# Build a submitted-answers list — pick the first option for every MCQ question
# and supply a non-empty free_text for every descriptive question.
submitted_answers = []
for q in quiz.questions:
    if q.type.value in ("mcq-single", "mcq-multi"):
        # Select the first option as the answer (may or may not be correct)
        submitted_answers.append({
            "question_id": q.id,
            "selected_option_ids": [q.options[0].id],
            "free_text": "",
        })
    else:  # descriptive
        submitted_answers.append({
            "question_id": q.id,
            "selected_option_ids": [],
            "free_text": (
                "The learning rate controls the step size during gradient descent. "
                "A high learning rate can overshoot the minimum while a low one converges slowly. "
                "Adaptive methods like Adam adjust the learning rate per parameter automatically."
            ),
        })

evaluate_result = agent.evaluate(quiz.model_dump(), submitted_answers)
print(evaluate_result.model_dump_json(indent=2))

assert evaluate_result.status == "evaluated", (
    f"Expected status='evaluated', got '{evaluate_result.status}'\n"
    f"Errors: {evaluate_result.errors}"
)
assert evaluate_result.result is not None, "result should not be None on success"
assert 0.0 <= evaluate_result.result.overall_percentage <= 100.0, (
    f"overall_percentage out of range: {evaluate_result.result.overall_percentage}"
)
assert evaluate_result.result.recommended_action in ("re-teach", "practice-more", "advance"), (
    f"Unexpected recommended_action: {evaluate_result.result.recommended_action}"
)
assert evaluate_result.metadata is not None, "metadata should not be None"

print(
    f"\nScore: {evaluate_result.result.overall_score}/{evaluate_result.result.max_score} "
    f"({evaluate_result.result.overall_percentage:.1f}%)"
)
print(f"Recommended action: {evaluate_result.result.recommended_action}")
print("\nevaluate() PASSED.")
print("\nLive call test PASSED.")
