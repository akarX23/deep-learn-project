"""Test suite for the Quiz Agent.

Covers:
  - MCQ scoring helpers (score_mcq_single, score_mcq_multi)
  - Result assembly (build_result, recommended_action thresholds)
  - Question-set validation (validate_question_set)
  - QuizAgent.generate() — schema, question counts, option structure,
    explanation fields, error paths, retry-on-deficit behaviour
  - QuizAgent.evaluate() — MCQ grading, descriptive grading, result schema,
    wrong-answer explanation surfacing, unanswered/empty-answer handling
  - Contract safety — output serialisation round-trip, error output schema,
    full pipeline integration

All LLM calls are monkeypatched; no real API keys are required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Lazy imports — the quiz_agent package does not exist yet; imports are done
# inside each test so that the file can be parsed (and test IDs collected)
# even before the implementation is present.  Once the package exists all
# imports will succeed and every test will run normally.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def inputs_dir() -> Path:
    return Path(__file__).parent / "inputs"


@pytest.fixture(scope="session")
def sample_input_data(inputs_dir: Path) -> dict:
    with open(inputs_dir / "sample_input.json", "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def short_teaching_content() -> str:
    """Content well below the 100-word minimum — triggers input validation error."""
    return "Gradient descent minimizes a loss function."


# ---------------------------------------------------------------------------
# Minimal in-memory quiz fixture (mirrors the expected Quiz schema shape).
# Used for evaluation tests without requiring a live generate() call.
# ---------------------------------------------------------------------------

SAMPLE_QUESTION_GENERATION_RESPONSE = json.dumps({
    "questions": [
        # --- mcq-single (×5) ---
        {
            "id": "q1",
            "type": "mcq-single",
            "prompt": "What does the learning rate control in gradient descent?",
            "sub_concept": "learning rate",
            "topic_deep_dive": "The learning rate is a hyperparameter that controls how large a step the optimizer takes at each iteration toward the minimum of the loss function.",
            "options": [
                {"id": "q1a", "text": "The size of each parameter update step", "is_correct": True,  "explanation": "Correct — the learning rate scales the gradient to determine step size."},
                {"id": "q1b", "text": "The number of training epochs",           "is_correct": False, "explanation": "Incorrect — epoch count is a separate hyperparameter unrelated to step size."},
                {"id": "q1c", "text": "The depth of the neural network",         "is_correct": False, "explanation": "Incorrect — network depth is an architectural choice, not an optimizer setting."},
                {"id": "q1d", "text": "The batch size used during training",      "is_correct": False, "explanation": "Incorrect — batch size controls how many examples are processed per step, not the step magnitude."},
            ],
        },
        {
            "id": "q2",
            "type": "mcq-single",
            "prompt": "Which gradient descent variant processes one sample per update?",
            "sub_concept": "SGD variants",
            "topic_deep_dive": "Stochastic Gradient Descent (SGD) updates the model parameters using the gradient computed from a single training example, making each step noisy but computationally cheap.",
            "options": [
                {"id": "q2a", "text": "Stochastic Gradient Descent (SGD)", "is_correct": True,  "explanation": "Correct — SGD uses exactly one sample per update."},
                {"id": "q2b", "text": "Mini-batch Gradient Descent",       "is_correct": False, "explanation": "Incorrect — mini-batch uses a small subset of samples, not a single one."},
                {"id": "q2c", "text": "Batch Gradient Descent",            "is_correct": False, "explanation": "Incorrect — batch gradient descent uses the entire dataset per update."},
                {"id": "q2d", "text": "Adam Optimizer",                    "is_correct": False, "explanation": "Incorrect — Adam is an adaptive learning-rate method, not defined by single-sample updates."},
            ],
        },
        {
            "id": "q3",
            "type": "mcq-single",
            "prompt": "What happens when the learning rate is too high?",
            "sub_concept": "learning rate",
            "topic_deep_dive": "A learning rate that is too large causes the optimizer to take oversized steps, potentially jumping over the minimum and causing the loss to diverge rather than converge.",
            "options": [
                {"id": "q3a", "text": "The optimizer overshoots the minimum",        "is_correct": True,  "explanation": "Correct — large steps risk jumping past the minimum."},
                {"id": "q3b", "text": "The optimizer converges more slowly",         "is_correct": False, "explanation": "Incorrect — slow convergence is caused by a learning rate that is too *low*, not too high."},
                {"id": "q3c", "text": "The model becomes more regularized",          "is_correct": False, "explanation": "Incorrect — regularization is controlled by weight-penalty terms, not the learning rate."},
                {"id": "q3d", "text": "The gradient magnitude increases indefinitely","is_correct": False, "explanation": "Incorrect — gradient magnitude depends on the loss landscape, not directly on the learning rate."},
            ],
        },
        {
            "id": "q4",
            "type": "mcq-single",
            "prompt": "What does the loss function measure?",
            "sub_concept": "loss function",
            "topic_deep_dive": "The loss function quantifies the discrepancy between the model's predicted outputs and the true target values. Minimizing it is the central objective of training.",
            "options": [
                {"id": "q4a", "text": "How far predictions are from actual values",  "is_correct": True,  "explanation": "Correct — the loss measures prediction error."},
                {"id": "q4b", "text": "The total number of model parameters",        "is_correct": False, "explanation": "Incorrect — parameter count is a model complexity metric, not a measure of prediction quality."},
                {"id": "q4c", "text": "The speed at which the model trains",         "is_correct": False, "explanation": "Incorrect — training speed is affected by hardware and batch size, not the loss value."},
                {"id": "q4d", "text": "The memory consumed during forward pass",     "is_correct": False, "explanation": "Incorrect — memory consumption is a system-level concern unrelated to the loss function."},
            ],
        },
        {
            "id": "q5",
            "type": "mcq-single",
            "prompt": "Convergence in gradient descent is indicated by which condition?",
            "sub_concept": "convergence",
            "topic_deep_dive": "Convergence occurs when the gradient magnitude approaches zero, meaning the algorithm has reached (or is very close to) a local or global minimum of the loss surface.",
            "options": [
                {"id": "q5a", "text": "Gradient magnitude approaches zero",  "is_correct": True,  "explanation": "Correct — a near-zero gradient means no further improvement is possible in the current direction."},
                {"id": "q5b", "text": "Loss value reaches exactly zero",     "is_correct": False, "explanation": "Incorrect — loss reaching zero is rarely achievable and not the general convergence criterion."},
                {"id": "q5c", "text": "Learning rate drops to zero",         "is_correct": False, "explanation": "Incorrect — the learning rate can be fixed; convergence is about the gradient, not the learning rate."},
                {"id": "q5d", "text": "Number of epochs exceeds a threshold","is_correct": False, "explanation": "Incorrect — hitting a maximum epoch count is an early-stopping criterion, not true convergence."},
            ],
        },
        # --- mcq-multi (×3) ---
        {
            "id": "q6",
            "type": "mcq-multi",
            "prompt": "Which of the following are adaptive learning-rate optimizers?",
            "sub_concept": "optimizer variants",
            "topic_deep_dive": "Adaptive optimizers like Adam, RMSProp, and Adagrad adjust the learning rate per-parameter during training, leading to faster and more stable convergence compared to fixed-rate SGD.",
            "options": [
                {"id": "q6a", "text": "Adam",            "is_correct": True,  "explanation": "Correct — Adam adapts learning rates using first and second moment estimates."},
                {"id": "q6b", "text": "RMSProp",         "is_correct": True,  "explanation": "Correct — RMSProp adapts the learning rate using a moving average of squared gradients."},
                {"id": "q6c", "text": "Batch Gradient Descent", "is_correct": False, "explanation": "Incorrect — batch GD uses a fixed learning rate; it is not an adaptive optimizer."},
                {"id": "q6d", "text": "Adagrad",         "is_correct": True,  "explanation": "Correct — Adagrad accumulates squared gradients to adapt the per-parameter learning rate."},
                {"id": "q6e", "text": "Standard SGD",    "is_correct": False, "explanation": "Incorrect — standard SGD uses a fixed global learning rate with no per-parameter adaptation."},
            ],
        },
        {
            "id": "q7",
            "type": "mcq-multi",
            "prompt": "Which factors contribute to slow convergence in gradient descent?",
            "sub_concept": "convergence",
            "topic_deep_dive": "Slow convergence is caused by a learning rate that is too small, poorly scaled features, saddle points in the loss landscape, or lack of momentum to maintain descent direction.",
            "options": [
                {"id": "q7a", "text": "Learning rate set too low",                "is_correct": True,  "explanation": "Correct — a very small step size requires many iterations to reach the minimum."},
                {"id": "q7b", "text": "Presence of saddle points in the loss surface", "is_correct": True, "explanation": "Correct — saddle points cause gradients near zero even when far from a true minimum."},
                {"id": "q7c", "text": "Using mini-batch instead of full-batch updates", "is_correct": False, "explanation": "Incorrect — mini-batch typically speeds convergence by adding noise that escapes flat regions."},
                {"id": "q7d", "text": "Poorly scaled input features",             "is_correct": True,  "explanation": "Correct — unscaled features create elongated loss contours that slow gradient descent."},
            ],
        },
        {
            "id": "q8",
            "type": "mcq-multi",
            "prompt": "Which techniques help prevent overfitting during optimization?",
            "sub_concept": "regularization",
            "topic_deep_dive": "Regularization methods such as L1 and L2 penalize large model weights, encouraging simpler models that generalize better to unseen data.",
            "options": [
                {"id": "q8a", "text": "L1 regularization (Lasso)", "is_correct": True,  "explanation": "Correct — L1 adds the absolute value of weights to the loss, penalizing large weights."},
                {"id": "q8b", "text": "L2 regularization (Ridge)", "is_correct": True,  "explanation": "Correct — L2 adds squared weights to the loss, discouraging large parameter values."},
                {"id": "q8c", "text": "Increasing the learning rate", "is_correct": False, "explanation": "Incorrect — a higher learning rate affects step size, not model complexity or overfitting."},
                {"id": "q8d", "text": "Dropout",                    "is_correct": True,  "explanation": "Correct — dropout randomly zeroes activations during training, acting as a regularizer."},
                {"id": "q8e", "text": "Reducing the number of epochs", "is_correct": False, "explanation": "Incorrect — fewer epochs is an early-stopping heuristic, not a regularization technique per se."},
            ],
        },
        # --- descriptive (×4) ---
        {
            "id": "q9",
            "type": "descriptive",
            "prompt": "Explain how the learning rate affects training stability and speed. What trade-offs must a practitioner consider when choosing its value?",
            "sub_concept": "learning rate",
            "rubric": [
                "Defines learning rate as the step-size scalar applied to the gradient",
                "Explains that too-high LR causes overshooting / divergence",
                "Explains that too-low LR causes slow convergence",
                "Mentions strategies such as learning rate schedules or adaptive optimizers",
                "Notes the trade-off between training speed and stability",
            ],
        },
        {
            "id": "q10",
            "type": "descriptive",
            "prompt": "Compare Stochastic Gradient Descent (SGD), mini-batch gradient descent, and batch gradient descent. Under what circumstances would you prefer each?",
            "sub_concept": "SGD variants",
            "rubric": [
                "Defines SGD as single-sample updates",
                "Defines mini-batch as subset-based updates",
                "Defines batch GD as full-dataset updates",
                "Discusses noise vs stability trade-off",
                "Provides a sensible usage recommendation for each variant",
            ],
        },
        {
            "id": "q11",
            "type": "descriptive",
            "prompt": "What is momentum in the context of gradient descent, and how does it help the optimizer escape flat regions or saddle points?",
            "sub_concept": "momentum",
            "rubric": [
                "Defines momentum as accumulated past gradient directions",
                "Explains how it dampens oscillation in narrow valleys",
                "Explains how it accelerates movement in consistent directions",
                "Mentions saddle points or flat loss regions as motivation",
                "Gives an intuitive analogy (e.g. ball rolling downhill)",
            ],
        },
        {
            "id": "q12",
            "type": "descriptive",
            "prompt": "Describe the roles of L1 and L2 regularization in an optimization objective. How do they differ in the type of solutions they encourage?",
            "sub_concept": "regularization",
            "rubric": [
                "States that regularization adds a penalty term to the loss",
                "Explains L1 promotes sparsity (many zero weights)",
                "Explains L2 encourages small but non-zero weights",
                "Compares the two in terms of feature selection vs weight shrinkage",
                "Connects regularization to preventing overfitting",
            ],
        },
    ]
})

SAMPLE_DESCRIPTIVE_GRADING_RESPONSE = json.dumps({
    "grades": [
        {
            "question_id": "q9",
            "score": 4,
            "max_score": 5,
            "model_answer": "The learning rate scales the gradient before it is subtracted from parameters. Too large a value causes oscillation or divergence; too small causes very slow progress. Practitioners often use learning rate schedules (e.g. cosine annealing) or switch to adaptive optimizers like Adam to balance speed and stability.",
            "feedback": "Good coverage of the trade-off. The answer would benefit from mentioning learning rate schedules explicitly.",
        },
        {
            "question_id": "q10",
            "score": 5,
            "max_score": 5,
            "model_answer": "SGD (single sample) is fast per step but noisy. Mini-batch balances noise and computational efficiency and is the most common choice. Full-batch GD is stable but expensive on large datasets. SGD is preferred for very large corpora; mini-batch is the default; batch GD suits small datasets.",
            "feedback": "Excellent — covers all three variants with clear usage guidance.",
        },
        {
            "question_id": "q11",
            "score": 3,
            "max_score": 5,
            "model_answer": "Momentum accumulates a velocity vector in directions of persistent gradient, helping the optimizer accelerate along ravines and slow down when the gradient changes direction. It reduces oscillation in narrow valleys and helps escape shallow saddle points.",
            "feedback": "Defines momentum and notes its effect on saddle points, but does not provide an intuitive analogy or discuss the dampening of oscillations in detail.",
        },
        {
            "question_id": "q12",
            "score": 4,
            "max_score": 5,
            "model_answer": "Both L1 and L2 add a penalty to the loss to discourage large weights. L1 (Lasso) produces sparse weight vectors — many weights become exactly zero — making it useful for feature selection. L2 (Ridge) shrinks all weights toward zero but rarely to exactly zero, producing smoother solutions. Both reduce overfitting.",
            "feedback": "Solid explanation of both. Could improve by contrasting scenarios where L1 is preferred over L2.",
        },
    ]
})


# ---------------------------------------------------------------------------
# Helper: build a minimal Quiz dict that matches the expected Quiz schema.
# ---------------------------------------------------------------------------

def _make_quiz(questions: list[dict] | None = None) -> dict:
    """Return a minimal Quiz-compatible dict for evaluation tests."""
    parsed = json.loads(SAMPLE_QUESTION_GENERATION_RESPONSE)
    return {
        "quiz_id": "test-quiz-001",
        "topic": "Gradient Descent Optimization",
        "questions": questions if questions is not None else parsed["questions"],
        "metadata": {
            "question_type_counts": {"mcq-single": 5, "mcq-multi": 3, "descriptive": 4},
            "total_questions": 12,
            "max_score": 35,
            "mcq_max_score": 15,
            "descriptive_max_score": 20,
            "ui_hints": {
                "mcq_single_input": "radio",
                "mcq_multi_input": "checkbox",
                "mcq_multi_hint_text": "Select all that apply",
                "descriptive_target_words": 150,
                "descriptive_soft_warning_below": 80,
            },
        },
    }


def _make_submitted_answers(all_correct_mcq: bool = True) -> list[dict]:
    """Build a plausible submitted-answers list for the sample quiz."""
    return [
        # mcq-single answers
        {"question_id": "q1",  "selected_option_ids": ["q1a"] if all_correct_mcq else ["q1b"]},
        {"question_id": "q2",  "selected_option_ids": ["q2a"] if all_correct_mcq else ["q2c"]},
        {"question_id": "q3",  "selected_option_ids": ["q3a"]},
        {"question_id": "q4",  "selected_option_ids": ["q4a"]},
        {"question_id": "q5",  "selected_option_ids": ["q5a"]},
        # mcq-multi answers (correct selections for q6: q6a, q6b, q6d)
        {"question_id": "q6",  "selected_option_ids": ["q6a", "q6b", "q6d"] if all_correct_mcq else ["q6a", "q6c"]},
        {"question_id": "q7",  "selected_option_ids": ["q7a", "q7b", "q7d"]},
        {"question_id": "q8",  "selected_option_ids": ["q8a", "q8b", "q8d"]},
        # descriptive answers
        {"question_id": "q9",  "free_text": "The learning rate determines how large each parameter update is. A high value can overshoot; a low one slows training."},
        {"question_id": "q10", "free_text": "SGD updates per sample, mini-batch per subset, and batch GD uses all data. Mini-batch is the most practical compromise."},
        {"question_id": "q11", "free_text": "Momentum accumulates past gradients to accelerate in consistent directions, helping escape saddle points."},
        {"question_id": "q12", "free_text": "L1 regularization encourages sparsity; L2 shrinks weights to small values. Both reduce overfitting by penalizing large weights."},
    ]


# ===========================================================================
# PHASE 2 — Foundational helpers
# ===========================================================================

class TestScoreMCQSingle:
    """Unit tests for helpers.score_mcq_single()."""

    def test_correct_selection_scores_one(self):
        from quiz_agent.helpers import score_mcq_single

        options = [
            {"id": "a", "is_correct": True},
            {"id": "b", "is_correct": False},
            {"id": "c", "is_correct": False},
            {"id": "d", "is_correct": False},
        ]
        assert score_mcq_single(options, selected_id="a") == 1

    def test_incorrect_selection_scores_zero(self):
        from quiz_agent.helpers import score_mcq_single

        options = [
            {"id": "a", "is_correct": True},
            {"id": "b", "is_correct": False},
            {"id": "c", "is_correct": False},
            {"id": "d", "is_correct": False},
        ]
        assert score_mcq_single(options, selected_id="b") == 0

    def test_no_selection_scores_zero(self):
        from quiz_agent.helpers import score_mcq_single

        options = [
            {"id": "a", "is_correct": True},
            {"id": "b", "is_correct": False},
        ]
        assert score_mcq_single(options, selected_id=None) == 0


class TestScoreMCQMulti:
    """Unit tests for helpers.score_mcq_multi()."""

    def test_all_correct_scores_full(self):
        from quiz_agent.helpers import score_mcq_multi

        options = [
            {"id": "a", "is_correct": True},
            {"id": "b", "is_correct": True},
            {"id": "c", "is_correct": False},
        ]
        # 2 correct selected, 0 wrong selected → 2/2 = 1.0 × max_points
        score = score_mcq_multi(options, selected_ids=["a", "b"], max_points=2)
        assert score == 2

    def test_partial_credit(self):
        from quiz_agent.helpers import score_mcq_multi

        options = [
            {"id": "a", "is_correct": True},
            {"id": "b", "is_correct": True},
            {"id": "c", "is_correct": False},
        ]
        # 1 correct, 0 wrong → 1/2 × 2 = 1
        score = score_mcq_multi(options, selected_ids=["a"], max_points=2)
        assert score == 1

    def test_wrong_selection_reduces_score(self):
        from quiz_agent.helpers import score_mcq_multi

        options = [
            {"id": "a", "is_correct": True},
            {"id": "b", "is_correct": True},
            {"id": "c", "is_correct": False},
        ]
        # 1 correct selected, 1 wrong selected → (1 − 1) / 2 × 2 = 0
        score = score_mcq_multi(options, selected_ids=["a", "c"], max_points=2)
        assert score == 0

    def test_score_floored_at_zero(self):
        from quiz_agent.helpers import score_mcq_multi

        options = [
            {"id": "a", "is_correct": True},
            {"id": "b", "is_correct": False},
            {"id": "c", "is_correct": False},
        ]
        # 0 correct, 2 wrong → (0 − 2) / 1 × 2 = -4 → floored to 0
        score = score_mcq_multi(options, selected_ids=["b", "c"], max_points=2)
        assert score == 0

    def test_no_selection_scores_zero(self):
        from quiz_agent.helpers import score_mcq_multi

        options = [
            {"id": "a", "is_correct": True},
            {"id": "b", "is_correct": True},
        ]
        assert score_mcq_multi(options, selected_ids=[], max_points=2) == 0


class TestBuildResultRecommendedAction:
    """Unit tests for helpers.build_result() recommended_action derivation."""

    def _make_minimal_outcomes(self, overall_score: int, max_score: int) -> dict:
        return {
            "overall_score": overall_score,
            "max_score": max_score,
            "mcq_subtotal": 0,
            "descriptive_subtotal": 0,
            "question_results": [],
            "weak_sub_concepts": [],
        }

    def test_below_50_recommends_reteach(self):
        from quiz_agent.helpers import build_result

        result = build_result(**self._make_minimal_outcomes(10, 30))
        assert result["recommended_action"] == "re-teach"

    def test_between_50_and_74_recommends_practice(self):
        from quiz_agent.helpers import build_result

        result = build_result(**self._make_minimal_outcomes(15, 30))
        assert result["recommended_action"] == "practice-more"

    def test_75_and_above_recommends_advance(self):
        from quiz_agent.helpers import build_result

        result = build_result(**self._make_minimal_outcomes(23, 30))
        assert result["recommended_action"] == "advance"

    def test_exactly_50_percent_recommends_practice(self):
        from quiz_agent.helpers import build_result

        result = build_result(**self._make_minimal_outcomes(15, 30))
        assert result["recommended_action"] == "practice-more"

    def test_exactly_75_percent_recommends_advance(self):
        from quiz_agent.helpers import build_result

        result = build_result(**self._make_minimal_outcomes(21, 28))
        assert result["recommended_action"] == "advance"


class TestValidateQuestionSet:
    """Unit tests for validators.validate_question_set()."""

    def test_valid_set_returns_no_errors(self):
        from quiz_agent.validators import validate_question_set

        parsed = json.loads(SAMPLE_QUESTION_GENERATION_RESPONSE)
        errors = validate_question_set(parsed, min_single=3, min_multi=2, required_descriptive=4)
        assert errors == []

    def test_missing_questions_key_returns_error(self):
        from quiz_agent.validators import validate_question_set

        errors = validate_question_set({}, min_single=3, min_multi=2, required_descriptive=4)
        assert any("questions" in e.lower() for e in errors)

    def test_too_few_mcq_single_returns_error(self):
        from quiz_agent.validators import validate_question_set

        parsed = json.loads(SAMPLE_QUESTION_GENERATION_RESPONSE)
        # Keep only 2 mcq-single (below min_single=3)
        parsed["questions"] = [q for q in parsed["questions"] if q["type"] != "mcq-single"][:0] + \
                               [q for q in parsed["questions"] if q["type"] == "mcq-single"][:2] + \
                               [q for q in parsed["questions"] if q["type"] != "mcq-single"]
        errors = validate_question_set(parsed, min_single=3, min_multi=2, required_descriptive=4)
        assert any("mcq-single" in e.lower() or "single" in e.lower() for e in errors)

    def test_wrong_descriptive_count_returns_error(self):
        from quiz_agent.validators import validate_question_set

        parsed = json.loads(SAMPLE_QUESTION_GENERATION_RESPONSE)
        # Remove one descriptive question
        descriptive = [q for q in parsed["questions"] if q["type"] == "descriptive"]
        others = [q for q in parsed["questions"] if q["type"] != "descriptive"]
        parsed["questions"] = others + descriptive[:3]  # only 3 descriptive
        errors = validate_question_set(parsed, min_single=3, min_multi=2, required_descriptive=4)
        assert any("descriptive" in e.lower() for e in errors)

    def test_mcq_single_without_four_options_returns_error(self):
        from quiz_agent.validators import validate_question_set

        parsed = json.loads(SAMPLE_QUESTION_GENERATION_RESPONSE)
        # Strip one option from the first mcq-single
        for q in parsed["questions"]:
            if q["type"] == "mcq-single":
                q["options"] = q["options"][:3]
                break
        errors = validate_question_set(parsed, min_single=3, min_multi=2, required_descriptive=4)
        assert any("option" in e.lower() or "4" in e for e in errors)

    def test_mcq_multi_with_too_few_options_returns_error(self):
        from quiz_agent.validators import validate_question_set

        parsed = json.loads(SAMPLE_QUESTION_GENERATION_RESPONSE)
        for q in parsed["questions"]:
            if q["type"] == "mcq-multi":
                q["options"] = q["options"][:2]  # below min 4
                break
        errors = validate_question_set(parsed, min_single=3, min_multi=2, required_descriptive=4)
        assert any("option" in e.lower() for e in errors)

    def test_descriptive_without_rubric_returns_error(self):
        from quiz_agent.validators import validate_question_set

        parsed = json.loads(SAMPLE_QUESTION_GENERATION_RESPONSE)
        for q in parsed["questions"]:
            if q["type"] == "descriptive":
                q.pop("rubric", None)
                break
        errors = validate_question_set(parsed, min_single=3, min_multi=2, required_descriptive=4)
        assert any("rubric" in e.lower() for e in errors)


# ===========================================================================
# PHASE 3 — QuizAgent.generate()
# ===========================================================================

class TestQuizAgentGenerate:
    """Tests for the generate() phase of QuizAgent."""

    def _patched_generate(self, monkeypatch, sample_input_data: dict) -> Any:
        """Run generate() with a monkeypatched LLM response."""
        monkeypatch.setattr(
            "quiz_agent.agent.call_llm",
            lambda messages, config: (SAMPLE_QUESTION_GENERATION_RESPONSE, 2400),
        )
        from quiz_agent.agent import QuizAgent

        agent = QuizAgent()
        return agent.generate(sample_input_data)

    def test_generate_returns_generated_status(self, monkeypatch, sample_input_data):
        output = self._patched_generate(monkeypatch, sample_input_data)
        assert output.status == "generated"

    def test_generate_returns_valid_quiz_schema(self, monkeypatch, sample_input_data):
        from project.schemas import QuizAgentOutput

        output = self._patched_generate(monkeypatch, sample_input_data)
        assert isinstance(output, QuizAgentOutput)
        assert output.quiz is not None

    def test_generate_question_type_counts(self, monkeypatch, sample_input_data):
        output = self._patched_generate(monkeypatch, sample_input_data)
        questions = output.quiz.questions
        assert sum(1 for q in questions if q.type == "mcq-single") >= 3
        assert sum(1 for q in questions if q.type == "mcq-multi") >= 2
        assert sum(1 for q in questions if q.type == "descriptive") == 4

    def test_generate_mcq_single_has_exactly_four_options(self, monkeypatch, sample_input_data):
        output = self._patched_generate(monkeypatch, sample_input_data)
        for q in output.quiz.questions:
            if q.type == "mcq-single":
                assert len(q.options) == 4, f"Question {q.id} has {len(q.options)} options, expected 4"

    def test_generate_mcq_multi_has_four_to_six_options(self, monkeypatch, sample_input_data):
        output = self._patched_generate(monkeypatch, sample_input_data)
        for q in output.quiz.questions:
            if q.type == "mcq-multi":
                assert 4 <= len(q.options) <= 6, f"Question {q.id} has {len(q.options)} options"

    def test_generate_mcq_options_have_explanations(self, monkeypatch, sample_input_data):
        output = self._patched_generate(monkeypatch, sample_input_data)
        for q in output.quiz.questions:
            if q.type in ("mcq-single", "mcq-multi"):
                for opt in q.options:
                    assert opt.explanation, f"Option {opt.id} missing explanation"
                assert q.topic_deep_dive, f"Question {q.id} missing topic_deep_dive"

    def test_generate_descriptive_questions_have_rubric(self, monkeypatch, sample_input_data):
        output = self._patched_generate(monkeypatch, sample_input_data)
        for q in output.quiz.questions:
            if q.type == "descriptive":
                assert q.rubric, f"Descriptive question {q.id} missing rubric"

    def test_generate_quiz_metadata_present(self, monkeypatch, sample_input_data):
        """Quiz metadata required by UI must be populated after generation."""
        output = self._patched_generate(monkeypatch, sample_input_data)
        meta = output.quiz.metadata
        assert meta is not None
        assert meta.question_type_counts["mcq-single"] >= 3
        assert meta.question_type_counts["mcq-multi"] >= 2
        assert meta.question_type_counts["descriptive"] == 4
        assert meta.total_questions == len(output.quiz.questions)
        assert meta.max_score > 0
        assert meta.ui_hints.mcq_single_input == "radio"
        assert meta.ui_hints.mcq_multi_input == "checkbox"
        assert meta.ui_hints.mcq_multi_hint_text == "Select all that apply"
        assert meta.ui_hints.descriptive_target_words == 150

    def test_generate_short_content_returns_error(self, monkeypatch, short_teaching_content):
        """Teaching content under the minimum length must return status='error' without an LLM call."""
        call_count = {"n": 0}

        def _should_not_be_called(messages, config):
            call_count["n"] += 1
            return ("", 0)

        monkeypatch.setattr("quiz_agent.agent.call_llm", _should_not_be_called)
        from quiz_agent.agent import QuizAgent

        output = QuizAgent().generate({
            "topic": "Gradient Descent",
            "teaching_content": short_teaching_content,
        })
        assert output.status == "error"
        assert call_count["n"] == 0

    def test_generate_llm_failure_returns_error(self, monkeypatch, sample_input_data):
        """An LLM RuntimeError must produce status='error' with no unhandled exception."""
        monkeypatch.setattr(
            "quiz_agent.agent.call_llm",
            lambda messages, config: (_ for _ in ()).throw(RuntimeError("provider unreachable")),
        )
        from quiz_agent.agent import QuizAgent

        output = QuizAgent().generate(sample_input_data)
        assert output.status == "error"
        assert output.errors

    def test_generate_retries_on_invalid_question_set(self, monkeypatch, sample_input_data):
        """Agent retries once on a deficit; errors on second failure."""
        call_count = {"n": 0}

        def _always_return_invalid(messages, config):
            call_count["n"] += 1
            # Return JSON with only 1 descriptive question (below required 4)
            invalid = json.loads(SAMPLE_QUESTION_GENERATION_RESPONSE)
            invalid["questions"] = [q for q in invalid["questions"] if q["type"] != "descriptive"][:0] + \
                                    [q for q in invalid["questions"] if q["type"] == "descriptive"][:1]
            return (json.dumps(invalid), 800)

        monkeypatch.setattr("quiz_agent.agent.call_llm", _always_return_invalid)
        from quiz_agent.agent import QuizAgent

        output = QuizAgent().generate(sample_input_data)
        assert output.status == "error"
        assert call_count["n"] == 2  # initial + one retry

    def test_generate_tokens_reported_in_metadata(self, monkeypatch, sample_input_data):
        monkeypatch.setattr(
            "quiz_agent.agent.call_llm",
            lambda messages, config: (SAMPLE_QUESTION_GENERATION_RESPONSE, 2400),
        )
        from quiz_agent.agent import QuizAgent

        output = QuizAgent().generate(sample_input_data)
        assert output.metadata.tokens_used == 2400


# ===========================================================================
# PHASE 4 — QuizAgent.evaluate()
# ===========================================================================

class TestQuizAgentEvaluate:
    """Tests for the evaluate() phase of QuizAgent."""

    def _patched_evaluate(self, monkeypatch, answers: list[dict] | None = None) -> Any:
        monkeypatch.setattr(
            "quiz_agent.agent.call_llm",
            lambda messages, config: (SAMPLE_DESCRIPTIVE_GRADING_RESPONSE, 900),
        )
        from quiz_agent.agent import QuizAgent

        agent = QuizAgent()
        quiz = _make_quiz()
        submitted = answers if answers is not None else _make_submitted_answers(all_correct_mcq=True)
        return agent.evaluate(quiz, submitted)

    def test_evaluate_returns_evaluated_status(self, monkeypatch):
        output = self._patched_evaluate(monkeypatch)
        assert output.status == "evaluated"

    def test_evaluate_returns_valid_result_schema(self, monkeypatch):
        from project.schemas import QuizAgentOutput

        output = self._patched_evaluate(monkeypatch)
        assert isinstance(output, QuizAgentOutput)
        assert output.result is not None

    def test_evaluate_overall_score_is_sum_of_sections(self, monkeypatch):
        output = self._patched_evaluate(monkeypatch)
        result = output.result
        assert result.overall_score == result.mcq_subtotal + result.descriptive_subtotal

    def test_evaluate_correct_mcq_single_adds_to_subtotal(self, monkeypatch):
        output = self._patched_evaluate(monkeypatch, _make_submitted_answers(all_correct_mcq=True))
        # All 5 mcq-single answered correctly → at least 5 points
        assert output.result.mcq_subtotal >= 5

    def test_evaluate_incorrect_mcq_single_scores_zero(self, monkeypatch):
        """Submitting wrong options for mcq-single reduces mcq_subtotal."""
        correct_output = self._patched_evaluate(monkeypatch, _make_submitted_answers(all_correct_mcq=True))
        wrong_output = self._patched_evaluate(monkeypatch, _make_submitted_answers(all_correct_mcq=False))
        assert wrong_output.result.mcq_subtotal < correct_output.result.mcq_subtotal

    def test_evaluate_wrong_mcq_exposes_explanation_panels(self, monkeypatch):
        """Incorrectly answered MCQ questions must carry explanation panel data in QuestionResult."""
        wrong_answers = _make_submitted_answers(all_correct_mcq=False)
        output = self._patched_evaluate(monkeypatch, wrong_answers)
        # q1 is answered wrong (q1b instead of q1a)
        q1_result = next(r for r in output.result.question_results if r.question_id == "q1")
        assert q1_result.wrong_answer_explanation, "Missing wrong-answer explanation for q1"
        assert q1_result.topic_deep_dive, "Missing topic deep-dive for q1"

    def test_evaluate_multi_correct_partial_credit(self, monkeypatch):
        """Partially correct mcq-multi answer receives partial credit (not 0 or full)."""
        partial_answers = _make_submitted_answers(all_correct_mcq=True)
        # Override q6 to select only 2 of 3 correct options
        for a in partial_answers:
            if a["question_id"] == "q6":
                a["selected_option_ids"] = ["q6a", "q6b"]  # miss q6d
        output = self._patched_evaluate(monkeypatch, partial_answers)
        q6_result = next(r for r in output.result.question_results if r.question_id == "q6")
        assert 0 < q6_result.score < q6_result.max_score

    def test_evaluate_multi_per_option_explanation_panels(self, monkeypatch):
        """Mishandled options on mcq-multi must each carry their own explanation panel."""
        partial_answers = _make_submitted_answers(all_correct_mcq=True)
        for a in partial_answers:
            if a["question_id"] == "q6":
                a["selected_option_ids"] = ["q6a", "q6c"]  # q6c is wrong; q6b and q6d missed
        output = self._patched_evaluate(monkeypatch, partial_answers)
        q6_result = next(r for r in output.result.question_results if r.question_id == "q6")
        assert q6_result.per_option_explanations, "Expected per-option explanation panels for q6"
        # q6c (selected-but-wrong) and q6b, q6d (missed-correct) should each have a panel
        panel_option_ids = {p["option_id"] for p in q6_result.per_option_explanations}
        assert "q6c" in panel_option_ids  # selected wrong
        assert "q6b" in panel_option_ids  # missed correct
        assert "q6d" in panel_option_ids  # missed correct
        assert q6_result.topic_deep_dive

    def test_evaluate_mcq_multi_score_floored_at_zero(self, monkeypatch):
        """Score for mcq-multi must never go negative."""
        all_wrong = _make_submitted_answers(all_correct_mcq=True)
        for a in all_wrong:
            if a["question_id"] == "q6":
                a["selected_option_ids"] = ["q6c", "q6e"]  # both wrong options
        output = self._patched_evaluate(monkeypatch, all_wrong)
        q6_result = next(r for r in output.result.question_results if r.question_id == "q6")
        assert q6_result.score >= 0

    def test_evaluate_unanswered_mcq_scores_zero(self, monkeypatch):
        """An MCQ with no selected options must score 0 without raising an error."""
        answers = _make_submitted_answers(all_correct_mcq=True)
        for a in answers:
            if a["question_id"] == "q1":
                a["selected_option_ids"] = []
        output = self._patched_evaluate(monkeypatch, answers)
        q1_result = next(r for r in output.result.question_results if r.question_id == "q1")
        assert q1_result.score == 0

    def test_evaluate_empty_descriptive_does_not_raise(self, monkeypatch):
        """Blank descriptive answers must be sent to grading LLM and produce a valid result."""
        answers = _make_submitted_answers(all_correct_mcq=True)
        for a in answers:
            if a["question_id"] == "q9":
                a["free_text"] = ""
        output = self._patched_evaluate(monkeypatch, answers)
        assert output.status == "evaluated"
        q9_result = next(r for r in output.result.question_results if r.question_id == "q9")
        assert q9_result.score >= 0

    def test_evaluate_descriptive_subtotal_sums_four_scores(self, monkeypatch):
        output = self._patched_evaluate(monkeypatch)
        graded = json.loads(SAMPLE_DESCRIPTIVE_GRADING_RESPONSE)
        expected_sum = sum(g["score"] for g in graded["grades"])
        assert output.result.descriptive_subtotal == expected_sum

    def test_evaluate_result_contains_weak_sub_concepts(self, monkeypatch):
        """Weak sub-concepts must be derived from low-scoring / wrong questions."""
        wrong_answers = _make_submitted_answers(all_correct_mcq=False)
        output = self._patched_evaluate(monkeypatch, wrong_answers)
        assert isinstance(output.result.weak_sub_concepts, list)

    def test_evaluate_recommended_action_reteach_on_low_score(self, monkeypatch):
        """Very low overall score should yield recommended_action='re-teach'."""
        all_wrong = [
            {"question_id": f"q{i}", "selected_option_ids": []} for i in range(1, 9)
        ] + [
            {"question_id": f"q{i}", "free_text": ""} for i in range(9, 13)
        ]
        # Patch grading to return zero scores
        zero_grades = json.dumps({
            "grades": [
                {"question_id": f"q{i}", "score": 0, "max_score": 5,
                 "model_answer": "...", "feedback": "No answer provided."}
                for i in range(9, 13)
            ]
        })
        monkeypatch.setattr(
            "quiz_agent.agent.call_llm",
            lambda messages, config: (zero_grades, 200),
        )
        from quiz_agent.agent import QuizAgent

        output = QuizAgent().evaluate(_make_quiz(), all_wrong)
        assert output.result.recommended_action == "re-teach"

    def test_evaluate_tokens_reported_in_metadata(self, monkeypatch):
        output = self._patched_evaluate(monkeypatch)
        assert output.metadata.tokens_used == 900


# ===========================================================================
# PHASE 5 — Contract safety & Teaching Agent integration
# ===========================================================================

class TestContractSafety:
    """Tests for schema validity, serialisation, and error-output contract."""

    def test_output_serialisation_roundtrip_generated(self, monkeypatch, sample_input_data):
        """QuizAgentOutput (generated) must survive a JSON serialise/deserialise cycle."""
        monkeypatch.setattr(
            "quiz_agent.agent.call_llm",
            lambda messages, config: (SAMPLE_QUESTION_GENERATION_RESPONSE, 2400),
        )
        from project.schemas import QuizAgentOutput
        from quiz_agent.agent import QuizAgent

        output = QuizAgent().generate(sample_input_data)
        roundtripped = QuizAgentOutput.model_validate_json(output.model_dump_json())
        assert roundtripped.status == output.status
        assert len(roundtripped.quiz.questions) == len(output.quiz.questions)

    def test_output_serialisation_roundtrip_evaluated(self, monkeypatch):
        """QuizAgentOutput (evaluated) must survive a JSON serialise/deserialise cycle."""
        monkeypatch.setattr(
            "quiz_agent.agent.call_llm",
            lambda messages, config: (SAMPLE_DESCRIPTIVE_GRADING_RESPONSE, 900),
        )
        from project.schemas import QuizAgentOutput
        from quiz_agent.agent import QuizAgent

        output = QuizAgent().evaluate(_make_quiz(), _make_submitted_answers())
        roundtripped = QuizAgentOutput.model_validate_json(output.model_dump_json())
        assert roundtripped.status == output.status
        assert roundtripped.result.overall_score == output.result.overall_score

    def test_error_output_schema_on_generate_failure(self, monkeypatch, sample_input_data):
        """Error output must have status='error', a non-empty errors list, and no quiz/result."""
        monkeypatch.setattr(
            "quiz_agent.agent.call_llm",
            lambda messages, config: (_ for _ in ()).throw(RuntimeError("fail")),
        )
        from quiz_agent.agent import QuizAgent

        output = QuizAgent().generate(sample_input_data)
        assert output.status == "error"
        assert output.errors
        assert output.quiz is None
        assert output.result is None

    def test_full_pipeline_integration(self, monkeypatch, sample_input_data):
        """Full generate() → evaluate() pipeline with both LLM calls monkeypatched."""
        call_responses = iter([
            (SAMPLE_QUESTION_GENERATION_RESPONSE, 2400),
            (SAMPLE_DESCRIPTIVE_GRADING_RESPONSE, 900),
        ])
        monkeypatch.setattr(
            "quiz_agent.agent.call_llm",
            lambda messages, config: next(call_responses),
        )
        from quiz_agent.agent import QuizAgent

        agent = QuizAgent()
        gen_output = agent.generate(sample_input_data)
        assert gen_output.status == "generated"

        eval_output = agent.evaluate(
            gen_output.quiz.model_dump(),
            _make_submitted_answers(all_correct_mcq=True),
        )
        assert eval_output.status == "evaluated"
        assert eval_output.result.overall_score > 0
        assert eval_output.result.recommended_action in ("re-teach", "practice-more", "advance")

    def test_quiz_metadata_passes_through_to_evaluate_output(self, monkeypatch):
        """UI metadata on the Quiz object must be accessible after evaluation."""
        monkeypatch.setattr(
            "quiz_agent.agent.call_llm",
            lambda messages, config: (SAMPLE_DESCRIPTIVE_GRADING_RESPONSE, 900),
        )
        from quiz_agent.agent import QuizAgent

        output = QuizAgent().evaluate(_make_quiz(), _make_submitted_answers())
        # Metadata lives on the quiz, which should be echoed in the output
        assert output.quiz is not None
        assert output.quiz.metadata.ui_hints.mcq_single_input == "radio"
        assert output.quiz.metadata.ui_hints.mcq_multi_hint_text == "Select all that apply"
