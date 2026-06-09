"""Quiz Agent — two-phase synchronous pipeline (generate + evaluate)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from pydantic import ValidationError

from project.schemas import (
    MCQOption,
    PerOptionExplanation,
    Question,
    QuestionResult,
    QuestionType,
    Quiz,
    QuizAgentInput,
    QuizAgentMetadata,
    QuizAgentOutput,
    QuizResult,
    SubmittedAnswer,
)
from quiz_agent.config import get_generation_config, get_grading_config
from quiz_agent.helpers import (
    build_error_output,
    build_quiz_from_parsed,
    build_result,
    parse_generated_quiz,
    parse_grading_response,
    score_mcq_multi,
    score_mcq_single,
)
from quiz_agent.llm_client import call_llm
from quiz_agent.prompts import DESCRIPTIVE_GRADING_PROMPT, QUESTION_GENERATION_PROMPT
from quiz_agent.validators import validate_question_set

# Teaching content is truncated to this character limit before being sent to the LLM
# to prevent the total request exceeding the model context window.
_MAX_CONTENT_CHARS = 8000

# Minimum word count for teaching content to attempt quiz generation.
_MIN_CONTENT_WORDS = 100


class QuizAgent:
    """Synchronous Quiz Agent.

    Phase 1 — generate(input):  Produce a structured Quiz from teaching content.
    Phase 2 — evaluate(quiz, answers):  Score all submitted answers and return a QuizResult.

    All failure paths return QuizAgentOutput(status='error'). No unhandled exceptions propagate.
    """

    # ------------------------------------------------------------------
    # Phase 1: generate
    # ------------------------------------------------------------------

    def generate(self, raw_input: dict[str, Any]) -> QuizAgentOutput:
        """Generate a Quiz from teaching content.

        Returns QuizAgentOutput with status='generated' on success,
        or status='error' with populated errors list on failure.
        """
        # Step 1: validate input
        try:
            agent_input = QuizAgentInput(**raw_input)
        except (ValidationError, TypeError) as exc:
            topic = raw_input.get("topic", "") if isinstance(raw_input, dict) else ""
            return build_error_output(topic, os.getenv("QUIZ_MODEL", "unknown"), [str(exc)])

        topic = agent_input.topic
        model_name = os.getenv("QUIZ_MODEL", "unknown")

        # Step 2: enforce minimum content length
        word_count = len(agent_input.teaching_content.split())
        if word_count < _MIN_CONTENT_WORDS:
            return build_error_output(
                topic,
                model_name,
                [
                    f"Teaching content too short to generate a complete quiz "
                    f"({word_count} words; minimum is {_MIN_CONTENT_WORDS})"
                ],
            )

        # Step 3: truncate oversized content
        content = agent_input.teaching_content[:_MAX_CONTENT_CHARS]

        # Step 4: load config
        try:
            config = get_generation_config()
        except RuntimeError as exc:
            return build_error_output(topic, model_name, [str(exc)])

        model_name = config.model

        # Step 5: call LLM (with one retry on validation deficit)
        prompt = QUESTION_GENERATION_PROMPT.format(
            teaching_content=content,
            topic=topic,
            mcq_single_count=agent_input.mcq_single_count,
            mcq_multi_count=agent_input.mcq_multi_count,
        )
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(2):
            try:
                raw_response, tokens_used = call_llm(messages, config)
            except RuntimeError as exc:
                return build_error_output(topic, model_name, [str(exc)])

            try:
                parsed = parse_generated_quiz(raw_response)
            except ValueError as exc:
                return build_error_output(topic, model_name, [str(exc)])

            errors = validate_question_set(
                parsed,
                min_single=max(1, agent_input.mcq_single_count - 2),
                min_multi=max(1, agent_input.mcq_multi_count - 1),
                required_descriptive=4,
            )
            if not errors:
                break
            if attempt == 1:
                return build_error_output(
                    topic,
                    model_name,
                    [f"Question set failed validation after retry: {'; '.join(errors)}"],
                )

        # Step 6: assemble Quiz
        try:
            quiz = build_quiz_from_parsed(parsed, topic)
        except (ValidationError, KeyError, ValueError) as exc:
            return build_error_output(topic, model_name, [f"Quiz assembly failed: {exc}"])

        return QuizAgentOutput(
            status="generated",
            quiz=quiz,
            result=None,
            metadata=QuizAgentMetadata(topic=topic, tokens_used=tokens_used, model=model_name),
            errors=[],
        )

    # ------------------------------------------------------------------
    # Phase 2: evaluate
    # ------------------------------------------------------------------

    def evaluate(
        self,
        quiz_data: dict[str, Any] | Quiz,
        answers: list[dict[str, Any] | SubmittedAnswer],
    ) -> QuizAgentOutput:
        """Evaluate submitted answers against the Quiz and return a QuizResult.

        Returns QuizAgentOutput with status='evaluated' on success,
        or status='error' on failure.
        """
        # Step 1: normalise inputs
        try:
            quiz = Quiz.model_validate(quiz_data) if isinstance(quiz_data, dict) else quiz_data
            submitted = [
                SubmittedAnswer(**a) if isinstance(a, dict) else a
                for a in answers
            ]
        except (ValidationError, TypeError) as exc:
            return build_error_output("unknown", os.getenv("QUIZ_MODEL", "unknown"), [str(exc)])

        topic = quiz.topic
        model_name = os.getenv("QUIZ_MODEL", "unknown")

        # Build lookup maps
        questions_by_id: dict[str, Question] = {q.id: q for q in quiz.questions}
        answers_by_qid: dict[str, SubmittedAnswer] = {a.question_id: a for a in submitted}

        # Step 2: grade MCQ questions locally
        question_results: list[QuestionResult] = []
        mcq_subtotal = 0.0
        descriptive_questions: list[Question] = []

        for question in quiz.questions:
            answer = answers_by_qid.get(question.id)

            if question.type == QuestionType.MCQ_SINGLE:
                selected_id = (answer.selected_option_ids[0] if answer and answer.selected_option_ids else None)
                score = score_mcq_single(question.options, selected_id)
                mcq_subtotal += score
                is_correct = score == 1

                wrong_expl: str | None = None
                deep_dive: str | None = None
                per_option: list[PerOptionExplanation] = []

                if not is_correct:
                    deep_dive = question.topic_deep_dive
                    if selected_id:
                        for opt in question.options:
                            if opt.id == selected_id:
                                wrong_expl = opt.explanation
                                break

                question_results.append(
                    QuestionResult(
                        question_id=question.id,
                        score=score,
                        max_score=question.max_points,
                        is_correct=is_correct,
                        wrong_answer_explanation=wrong_expl,
                        topic_deep_dive=deep_dive,
                        per_option_explanations=per_option,
                    )
                )

            elif question.type == QuestionType.MCQ_MULTI:
                selected_ids = answer.selected_option_ids if answer else []
                score = score_mcq_multi(question.options, selected_ids, question.max_points)
                mcq_subtotal += score

                selected_set = set(selected_ids)
                correct_set = {o.id for o in question.options if o.is_correct}
                is_fully_correct = selected_set == correct_set
                per_option: list[PerOptionExplanation] = []
                deep_dive: str | None = None

                if not is_fully_correct:
                    deep_dive = question.topic_deep_dive
                    # wrong-selected options
                    for opt in question.options:
                        if opt.id in selected_set and not opt.is_correct:
                            per_option.append(PerOptionExplanation(
                                option_id=opt.id,
                                explanation_type="wrong-selected",
                                explanation=opt.explanation,
                            ))
                        # missed correct options
                        elif opt.is_correct and opt.id not in selected_set:
                            per_option.append(PerOptionExplanation(
                                option_id=opt.id,
                                explanation_type="missed-correct",
                                explanation=opt.explanation,
                            ))

                question_results.append(
                    QuestionResult(
                        question_id=question.id,
                        score=score,
                        max_score=question.max_points,
                        topic_deep_dive=deep_dive,
                        per_option_explanations=per_option,
                    )
                )

            elif question.type == QuestionType.DESCRIPTIVE:
                descriptive_questions.append(question)

        # Step 3: grade descriptive questions via one LLM call
        try:
            config = get_grading_config()
        except RuntimeError as exc:
            return build_error_output(topic, model_name, [str(exc)])

        model_name = config.model
        descriptive_subtotal = 0.0

        if descriptive_questions:
            answers_block = self._build_answers_block(
                descriptive_questions, answers_by_qid
            )
            grading_prompt = DESCRIPTIVE_GRADING_PROMPT.format(
                topic=topic,
                answers_block=answers_block,
            )
            grading_messages = [{"role": "user", "content": grading_prompt}]

            try:
                grading_raw, tokens_used = call_llm(grading_messages, config)
            except RuntimeError as exc:
                return build_error_output(topic, model_name, [str(exc)])

            try:
                grading_parsed = parse_grading_response(grading_raw)
            except ValueError as exc:
                return build_error_output(topic, model_name, [str(exc)])

            grades_by_qid: dict[str, dict] = {
                g["question_id"]: g for g in grading_parsed["grades"]
            }

            for question in descriptive_questions:
                grade = grades_by_qid.get(question.id, {})
                score = min(float(grade.get("score", 0)), float(question.max_points))
                descriptive_subtotal += score
                question_results.append(
                    QuestionResult(
                        question_id=question.id,
                        score=score,
                        max_score=question.max_points,
                        model_answer=grade.get("model_answer"),
                        feedback=grade.get("feedback"),
                    )
                )
        else:
            tokens_used = 0

        # Step 4: assemble QuizResult
        overall_score = mcq_subtotal + descriptive_subtotal
        # Recompute max_score from actual question max_points (authoritative source)
        max_score = sum(q.max_points for q in quiz.questions)

        # Derive weak sub-concepts: questions scoring below 50% of their max
        weak_sub_concepts: list[str] = []
        seen_sub = set()
        for qr in question_results:
            q = questions_by_id.get(qr.question_id)
            if q and qr.max_score > 0 and (qr.score / qr.max_score) < 0.5:
                if q.sub_concept not in seen_sub:
                    weak_sub_concepts.append(q.sub_concept)
                    seen_sub.add(q.sub_concept)

        result_dict = build_result(
            overall_score=overall_score,
            max_score=max_score,
            mcq_subtotal=mcq_subtotal,
            descriptive_subtotal=descriptive_subtotal,
            question_results=question_results,
            weak_sub_concepts=weak_sub_concepts,
        )

        try:
            quiz_result = QuizResult(**result_dict)
        except ValidationError as exc:
            return build_error_output(topic, model_name, [str(exc)])

        return QuizAgentOutput(
            status="evaluated",
            quiz=quiz,
            result=quiz_result,
            metadata=QuizAgentMetadata(topic=topic, tokens_used=tokens_used, model=model_name),
            errors=[],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_answers_block(
        self,
        descriptive_questions: list[Question],
        answers_by_qid: dict[str, SubmittedAnswer],
    ) -> str:
        """Format descriptive Q&A pairs for the grading prompt."""
        lines: list[str] = []
        for q in descriptive_questions:
            answer = answers_by_qid.get(q.id)
            free_text = answer.free_text if answer else ""
            rubric_str = "\n  - ".join(q.rubric)
            lines.append(
                f"Question ID: {q.id}\n"
                f"Prompt: {q.prompt}\n"
                f"Max Score: {q.max_points}\n"
                f"Rubric key points:\n  - {rubric_str}\n"
                f"Learner Answer:\n{free_text or '(no answer provided)'}\n"
            )
        return "\n---\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entrypoint (T044 — dev tooling; generates a quiz from stdin/file input)
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(description="Quiz Agent — generate a quiz from teaching content")
    parser.add_argument("--input", required=True, help="Path to JSON input file")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as fh:
        raw = json.load(fh)

    output = QuizAgent().generate(raw)
    print(output.model_dump_json(indent=2))
    if output.status == "error":
        sys.exit(1)


if __name__ == "__main__":
    _main()
