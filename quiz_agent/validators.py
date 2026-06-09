"""Structural validator for the Quiz Agent question-generation response."""

from __future__ import annotations

_MCQ_SINGLE_REQUIRED_OPTIONS = 4
_MCQ_MULTI_MIN_OPTIONS = 4
_MCQ_MULTI_MAX_OPTIONS = 6


def validate_question_set(
    parsed: dict,
    min_single: int = 3,
    min_multi: int = 2,
    required_descriptive: int = 4,
) -> list[str]:
    """Validate the structural integrity of a parsed question-generation response.

    Returns a list of error strings. An empty list means the set is valid.
    """
    errors: list[str] = []

    if not isinstance(parsed, dict):
        errors.append("Response is not a JSON object")
        return errors

    if "questions" not in parsed:
        errors.append("Response missing required 'questions' key")
        return errors

    questions = parsed["questions"]
    if not isinstance(questions, list) or len(questions) == 0:
        errors.append("'questions' must be a non-empty list")
        return errors

    single_count = 0
    multi_count = 0
    descriptive_count = 0

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            errors.append(f"Question at index {i} is not an object")
            continue

        q_id = q.get("id", f"index-{i}")
        q_type = q.get("type", "")

        if q_type == "mcq-single":
            single_count += 1
            options = q.get("options", [])
            if len(options) != _MCQ_SINGLE_REQUIRED_OPTIONS:
                errors.append(
                    f"Question {q_id} (mcq-single) must have exactly "
                    f"{_MCQ_SINGLE_REQUIRED_OPTIONS} options, got {len(options)}"
                )
            correct_count = sum(1 for o in options if isinstance(o, dict) and o.get("is_correct"))
            if correct_count != 1:
                errors.append(
                    f"Question {q_id} (mcq-single) must have exactly 1 correct option, "
                    f"got {correct_count}"
                )
            for j, opt in enumerate(options):
                if isinstance(opt, dict) and not opt.get("explanation", "").strip():
                    errors.append(
                        f"Question {q_id} option index {j} is missing 'explanation'"
                    )

        elif q_type == "mcq-multi":
            multi_count += 1
            options = q.get("options", [])
            if not (_MCQ_MULTI_MIN_OPTIONS <= len(options) <= _MCQ_MULTI_MAX_OPTIONS):
                errors.append(
                    f"Question {q_id} (mcq-multi) must have {_MCQ_MULTI_MIN_OPTIONS}–"
                    f"{_MCQ_MULTI_MAX_OPTIONS} options, got {len(options)}"
                )
            correct_count = sum(1 for o in options if isinstance(o, dict) and o.get("is_correct"))
            if correct_count < 2:
                errors.append(
                    f"Question {q_id} (mcq-multi) must have at least 2 correct options, "
                    f"got {correct_count}"
                )
            for j, opt in enumerate(options):
                if isinstance(opt, dict) and not opt.get("explanation", "").strip():
                    errors.append(
                        f"Question {q_id} option index {j} is missing 'explanation'"
                    )

        elif q_type == "descriptive":
            descriptive_count += 1
            rubric = q.get("rubric", [])
            if not isinstance(rubric, list) or len(rubric) == 0:
                errors.append(
                    f"Question {q_id} (descriptive) must have a non-empty 'rubric' list"
                )

        else:
            errors.append(f"Question {q_id} has unknown type: '{q_type}'")

    if single_count < min_single:
        errors.append(
            f"Quiz has {single_count} mcq-single question(s); minimum is {min_single}"
        )
    if multi_count < min_multi:
        errors.append(
            f"Quiz has {multi_count} mcq-multi question(s); minimum is {min_multi}"
        )
    if descriptive_count != required_descriptive:
        errors.append(
            f"Quiz has {descriptive_count} descriptive question(s); "
            f"exactly {required_descriptive} are required"
        )

    return errors
