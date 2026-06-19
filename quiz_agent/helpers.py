"""Pure deterministic helpers for the Quiz Agent pipeline."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Sequence
from typing import Any

from project.schemas import (
    MCQOption,
    PerOptionExplanation,
    Question,
    QuestionResult,
    QuestionType,
    Quiz,
    QuizAgentMetadata,
    QuizAgentOutput,
    QuizMetadata,
    QuizResult,
    UIHints,
)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def score_mcq_single(options: Sequence[dict | MCQOption], selected_id: str | None) -> int:
    """Return 1 if selected_id is the correct option, 0 otherwise."""
    if not selected_id:
        return 0
    for opt in options:
        opt_id = opt["id"] if isinstance(opt, dict) else opt.id
        is_correct = opt["is_correct"] if isinstance(opt, dict) else opt.is_correct
        if opt_id == selected_id and is_correct:
            return 1
    return 0


def score_mcq_multi(
    options: Sequence[dict | MCQOption],
    selected_ids: list[str],
    max_points: int = 2,
) -> float:
    """Partial-credit scoring for multiple-answer MCQ.

    score = max(0, correct_selected - incorrect_selected) / total_correct * max_points
    """
    correct_ids = set()
    for opt in options:
        opt_id = opt["id"] if isinstance(opt, dict) else opt.id
        is_correct = opt["is_correct"] if isinstance(opt, dict) else opt.is_correct
        if is_correct:
            correct_ids.add(opt_id)

    selected = set(selected_ids)
    correct_selected = len(selected & correct_ids)
    incorrect_selected = len(selected - correct_ids)
    total_correct = len(correct_ids)

    if total_correct == 0:
        return 0

    raw = (correct_selected - incorrect_selected) / total_correct * max_points
    return max(0.0, raw)


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        m = _JSON_FENCE_RE.match(text)
        if m:
            return m.group(1).strip()
    return text


def parse_generated_quiz(raw: str) -> dict[str, Any]:
    """Parse the LLM's raw question-generation response into a dict.

    Raises:
        ValueError: If the response is not valid JSON or lacks a 'questions' key.
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned an empty response")
    text = _strip_fences(raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict) or "questions" not in parsed:
        raise ValueError("LLM response missing 'questions' key")
    return parsed


def parse_grading_response(raw: str) -> dict[str, Any]:
    """Parse the LLM's descriptive-grading response into a dict.

    Raises:
        ValueError: If the response is not valid JSON or lacks a 'grades' key.
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned an empty grading response")
    text = _strip_fences(raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Grading response is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict) or "grades" not in parsed:
        raise ValueError("Grading response missing 'grades' key")
    return parsed


def parse_swot_response(raw: str) -> dict[str, Any]:
    """Parse the LLM's SWOT analysis response into a dict.

    Raises:
        ValueError: If the response is not valid JSON or lacks required SWOT keys.
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned an empty SWOT response")
    text = _strip_fences(raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"SWOT response is not valid JSON: {exc}") from exc
    for key in ("strengths", "weaknesses", "opportunities", "threats"):
        if key not in parsed:
            raise ValueError(f"SWOT response missing '{key}' key")
    return parsed


def parse_mcq_options_response(raw: str, question_id: str | None = None) -> dict[str, Any]:
    """Parse the LLM's MCQ option-expansion response into a normalized dict.

    Accepted response shapes:
    - {"options": [...], "topic_deep_dive": "..."}
    - {"question": {"options": [...], "topic_deep_dive": "..."}}
    - {"questions": [{...}, ...]}  # falls back to first or matching question_id
    """
    if not raw or not raw.strip():
        raise ValueError("LLM returned an empty MCQ options response")
    text = _strip_fences(raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"MCQ options response is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("MCQ options response must be a JSON object")

    candidate: dict[str, Any] | None = None

    if "options" in parsed:
        candidate = parsed
    elif isinstance(parsed.get("question"), dict):
        candidate = parsed["question"]
    elif isinstance(parsed.get("questions"), list):
        questions = [q for q in parsed["questions"] if isinstance(q, dict)]
        if question_id:
            candidate = next((q for q in questions if q.get("id") == question_id), None)
        if candidate is None and questions:
            candidate = questions[0]

    if candidate is None:
        raise ValueError("MCQ options response missing an options payload")

    options = candidate.get("options")
    if not isinstance(options, list):
        raise ValueError("MCQ options response missing 'options' list")

    topic_deep_dive = candidate.get("topic_deep_dive", "")
    if topic_deep_dive is None:
        topic_deep_dive = ""

    return {
        "options": options,
        "topic_deep_dive": str(topic_deep_dive),
    }


# ---------------------------------------------------------------------------
# Quiz assembly
# ---------------------------------------------------------------------------


def build_quiz_from_parsed(parsed: dict, topic: str) -> Quiz:
    """Convert a parsed generation response dict into a Quiz model instance."""
    questions: list[Question] = []
    for q in parsed["questions"]:
        options = [MCQOption(**o) for o in q.get("options", [])]
        questions.append(
            Question(
                id=q["id"],
                type=QuestionType(q["type"]),
                prompt=q["prompt"],
                sub_concept=q["sub_concept"],
                max_points=q.get("max_points", 1),
                options=options,
                topic_deep_dive=q.get("topic_deep_dive"),
                rubric=q.get("rubric", []),
            )
        )

    type_counts: dict[str, int] = {"mcq-single": 0, "mcq-multi": 0, "descriptive": 0}
    mcq_max = 0
    desc_max = 0
    for q in questions:
        type_counts[q.type.value] = type_counts.get(q.type.value, 0) + 1
        if q.type in (QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTI):
            mcq_max += q.max_points
        else:
            desc_max += q.max_points

    metadata = QuizMetadata(
        question_type_counts=type_counts,
        total_questions=len(questions),
        max_score=mcq_max + desc_max,
        mcq_max_score=mcq_max,
        descriptive_max_score=desc_max,
        ui_hints=UIHints(),
    )

    return Quiz(
        quiz_id=str(uuid.uuid4()),
        topic=topic,
        questions=questions,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Result assembly
# ---------------------------------------------------------------------------


def build_result(
    overall_score: float,
    max_score: int,
    mcq_subtotal: float,
    descriptive_subtotal: float,
    question_results: list[QuestionResult],
    weak_sub_concepts: list[str],
) -> dict[str, Any]:
    """Assemble a QuizResult dict including recommended_action derivation."""
    percentage = round(overall_score / max_score * 100, 1) if max_score > 0 else 0.0

    if percentage >= 75:
        recommended_action = "Move to next Topic"
    elif percentage >= 50:
        recommended_action = "Review Notes and Retake Quiz"
    else:
        recommended_action = "Retake the Course"

    return {
        "overall_score": overall_score,
        "max_score": max_score,
        "overall_percentage": percentage,
        "mcq_subtotal": mcq_subtotal,
        "descriptive_subtotal": descriptive_subtotal,
        "question_results": question_results,
        "weak_sub_concepts": weak_sub_concepts,
        "recommended_action": recommended_action,
    }


# ---------------------------------------------------------------------------
# Error output
# ---------------------------------------------------------------------------


def build_error_output(topic: str, model: str, errors: list[str]) -> QuizAgentOutput:
    """Build a schema-valid QuizAgentOutput with status='error'."""
    return QuizAgentOutput(
        status="error",
        quiz=None,
        result=None,
        metadata=QuizAgentMetadata(topic=topic, tokens_used=0, model=model),
        errors=errors,
    )
