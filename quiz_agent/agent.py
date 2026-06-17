"""Quiz Agent — two-phase synchronous pipeline (generate + evaluate)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Module-level logger — writes to logs/quiz_agent.log (created if missing)
# ---------------------------------------------------------------------------
_LOG_DIR = Path(__file__).parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_log_handler_file = logging.FileHandler(_LOG_DIR / "quiz_agent.log", encoding="utf-8")
_log_handler_file.setLevel(logging.DEBUG)
_log_handler_file.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s"))

_log_handler_console = logging.StreamHandler(sys.stdout)
_log_handler_console.setLevel(logging.INFO)
_log_handler_console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

logger = logging.getLogger("quiz_agent")
logger.setLevel(logging.DEBUG)
logging.getLogger("kafka").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logger.addHandler(_log_handler_file)
logger.addHandler(_log_handler_console)
logger.propagate = False

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
    SWOTAnalysis,
)
from quiz_agent.config import get_generation_config, get_grading_config
from quiz_agent.helpers import (
    build_error_output,
    build_quiz_from_parsed,
    build_result,
    parse_generated_quiz,
    parse_grading_response,
    parse_swot_response,
    score_mcq_multi,
    score_mcq_single,
)
from quiz_agent.llm_client import call_llm
from quiz_agent.prompts import DESCRIPTIVE_GRADING_PROMPT, QUESTION_GENERATION_PROMPT, SWOT_ANALYSIS_PROMPT
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
        logger.info("================================================================")
        logger.info("PHASE 1 — generate() START")
        logger.info("================================================================")

        # Step 1: validate input
        logger.info("[STEP 1] Validating QuizAgentInput schema")
        logger.debug("[STEP 1] Raw input received:\n%s", json.dumps(raw_input, indent=2, default=str))
        try:
            agent_input = QuizAgentInput(**raw_input)
        except (ValidationError, TypeError) as exc:
            topic = raw_input.get("topic", "") if isinstance(raw_input, dict) else ""
            logger.error("[STEP 1] Input validation FAILED: %s", exc)
            return build_error_output(topic, os.getenv("QUIZ_MODEL", "unknown"), [str(exc)])
        logger.info("[STEP 1] QuizAgentInput validated OK — topic=%r mcq_single=%d mcq_multi=%d",
                    agent_input.topic, agent_input.mcq_single_count, agent_input.mcq_multi_count)

        topic = agent_input.topic
        model_name = os.getenv("QUIZ_MODEL", "unknown")

        # Step 2: enforce minimum content length
        word_count = len(agent_input.teaching_content.split())
        logger.info("[STEP 2] Content length check — word_count=%d (min=%d)", word_count, _MIN_CONTENT_WORDS)
        logger.debug("[STEP 2] Teaching content (first 500 chars):\n%s",
                     agent_input.teaching_content[:500])
        if word_count < _MIN_CONTENT_WORDS:
            logger.warning("Content too short (%d words; min %d)", word_count, _MIN_CONTENT_WORDS)
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
        truncated = len(agent_input.teaching_content) > _MAX_CONTENT_CHARS
        logger.info("[STEP 3] Content prepared — chars=%d truncated=%s", len(content), truncated)

        # Step 4: load config
        logger.info("[STEP 4] Loading LLM generation config")
        try:
            config = get_generation_config()
        except RuntimeError as exc:
            logger.error("[STEP 4] Config load failed: %s", exc)
            return build_error_output(topic, model_name, [str(exc)])
        model_name = config.model
        logger.info("[STEP 4] Config — model=%r temperature=%.2f max_tokens=%d",
                    config.model, config.temperature, config.max_tokens)

        # Step 5: call LLM (with one retry on validation deficit)
        prompt = QUESTION_GENERATION_PROMPT.format(
            teaching_content=content,
            topic=topic,
            mcq_single_count=agent_input.mcq_single_count,
            mcq_multi_count=agent_input.mcq_multi_count,
        )
        messages = [{"role": "user", "content": prompt}]
        logger.info("[STEP 5] Generation prompt assembled — prompt_chars=%d", len(prompt))
        logger.debug("[STEP 5] Full generation prompt:\n%s", prompt)

        for attempt in range(2):
            logger.info("[STEP 5] LLM generation call — attempt %d/2", attempt + 1)
            try:
                raw_response, tokens_used = call_llm(messages, config)
            except RuntimeError as exc:
                logger.error("[STEP 5] LLM call FAILED: %s", exc)
                return build_error_output(topic, model_name, [str(exc)])

            logger.info("[STEP 5] LLM response received — tokens_used=%d response_chars=%d",
                        tokens_used, len(raw_response))
            logger.debug("[STEP 5] Raw LLM response:\n%s", raw_response)

            try:
                parsed = parse_generated_quiz(raw_response)
            except ValueError as exc:
                logger.error("[STEP 5] JSON parse FAILED: %s", exc)
                return build_error_output(topic, model_name, [str(exc)])

            q_count = len(parsed.get("questions", []))
            logger.info("[STEP 5] Parsed %d questions from LLM response", q_count)

            errors = validate_question_set(
                parsed,
                min_single=max(1, agent_input.mcq_single_count - 2),
                min_multi=max(1, agent_input.mcq_multi_count - 1),
                required_descriptive=4,
            )
            if not errors:
                logger.info("[STEP 5] Question set validation PASSED (%d questions)", q_count)
                break
            logger.warning("[STEP 5] Validation errors (attempt %d): %s", attempt + 1, errors)
            if attempt == 1:
                return build_error_output(
                    topic,
                    model_name,
                    [f"Question set failed validation after retry: {'; '.join(errors)}"],
                )

        # Step 6: assemble Quiz
        logger.info("[STEP 6] Assembling Quiz schema object")
        try:
            quiz = build_quiz_from_parsed(parsed, topic)
        except (ValidationError, KeyError, ValueError) as exc:
            logger.error("[STEP 6] Quiz assembly FAILED: %s", exc)
            return build_error_output(topic, model_name, [f"Quiz assembly failed: {exc}"])

        output = QuizAgentOutput(
            status="generated",
            quiz=quiz,
            result=None,
            metadata=QuizAgentMetadata(topic=topic, tokens_used=tokens_used, model=model_name),
            errors=[],
        )
        logger.info("[STEP 6] Quiz assembled — quiz_id=%s total_questions=%d max_score=%d",
                    quiz.quiz_id, quiz.metadata.total_questions, quiz.metadata.max_score)
        logger.debug("[STEP 6] QuizAgentOutput schema:\n%s", output.model_dump_json(indent=2))
        logger.info("================================================================")
        logger.info("PHASE 1 — generate() DONE  status=generated  tokens_used=%d", tokens_used)
        logger.info("================================================================")
        return output

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
        logger.info("================================================================")
        logger.info("PHASE 2 — evaluate() START")
        logger.info("================================================================")

        # Step 1: normalise inputs
        logger.info("[STEP 1] Normalising Quiz and SubmittedAnswer inputs")
        try:
            quiz = Quiz.model_validate(quiz_data) if isinstance(quiz_data, dict) else quiz_data
            submitted = [
                SubmittedAnswer(**a) if isinstance(a, dict) else a
                for a in answers
            ]
        except (ValidationError, TypeError) as exc:
            logger.error("[STEP 1] Input normalisation FAILED: %s", exc)
            return build_error_output("unknown", os.getenv("QUIZ_MODEL", "unknown"), [str(exc)])

        topic = quiz.topic
        model_name = os.getenv("QUIZ_MODEL", "unknown")
        logger.info("[STEP 1] Inputs OK — quiz_id=%s topic=%r questions=%d answers=%d",
                    quiz.quiz_id, topic, len(quiz.questions), len(submitted))
        logger.debug("[STEP 1] Submitted answers:\n%s",
                     json.dumps([a.model_dump() for a in submitted], indent=2, default=str))

        # Build lookup maps
        questions_by_id: dict[str, Question] = {q.id: q for q in quiz.questions}
        answers_by_qid: dict[str, SubmittedAnswer] = {a.question_id: a for a in submitted}

        # Step 2: grade MCQ questions locally
        logger.info("[STEP 2] Grading MCQ questions locally")
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

        logger.info("[STEP 2] MCQ grading done — mcq_subtotal=%.2f (%d descriptive deferred)",
                    mcq_subtotal, len(descriptive_questions))
        for qr in question_results:
            logger.debug("[STEP 2] MCQ result — question_id=%s score=%.2f/%d is_correct=%s",
                         qr.question_id, qr.score, qr.max_score, qr.is_correct)

        # Step 3: grade descriptive questions via one LLM call
        logger.info("[STEP 3] Loading LLM grading config")
        try:
            config = get_grading_config()
        except RuntimeError as exc:
            logger.error("[STEP 3] Config load FAILED: %s", exc)
            return build_error_output(topic, model_name, [str(exc)])
        logger.info("[STEP 3] Config — model=%r temperature=%.2f max_tokens=%d",
                    config.model, config.temperature, config.max_tokens)

        model_name = config.model
        descriptive_subtotal = 0.0

        if descriptive_questions:
            logger.info("[STEP 3] Grading %d descriptive question(s) via LLM", len(descriptive_questions))
            answers_block = self._build_answers_block(
                descriptive_questions, answers_by_qid
            )
            grading_prompt = DESCRIPTIVE_GRADING_PROMPT.format(
                topic=topic,
                answers_block=answers_block,
            )
            grading_messages = [{"role": "user", "content": grading_prompt}]
            logger.info("[STEP 3] Grading prompt assembled — prompt_chars=%d", len(grading_prompt))
            logger.debug("[STEP 3] Full grading prompt:\n%s", grading_prompt)

            try:
                grading_raw, tokens_used = call_llm(grading_messages, config)
            except RuntimeError as exc:
                logger.error("[STEP 3] Grading LLM call FAILED: %s", exc)
                return build_error_output(topic, model_name, [str(exc)])

            logger.info("[STEP 3] Grading LLM response received — tokens_used=%d response_chars=%d",
                        tokens_used, len(grading_raw))
            logger.debug("[STEP 3] Raw grading LLM response:\n%s", grading_raw)

            try:
                grading_parsed = parse_grading_response(grading_raw)
            except ValueError as exc:
                logger.error("[STEP 3] Grading JSON parse FAILED: %s", exc)
                return build_error_output(topic, model_name, [str(exc)])

            logger.info("[STEP 3] Grading response parsed — %d grades received",
                        len(grading_parsed.get("grades", [])))

            grades_by_qid: dict[str, dict] = {
                g["question_id"]: g for g in grading_parsed["grades"]
            }

            for question in descriptive_questions:
                grade = grades_by_qid.get(question.id, {})
                score = min(float(grade.get("score", 0)), float(question.max_points))
                descriptive_subtotal += score
                logger.debug("[STEP 3] Descriptive result — question_id=%s score=%.1f/%d",
                             question.id, score, question.max_points)
                question_results.append(
                    QuestionResult(
                        question_id=question.id,
                        score=score,
                        max_score=question.max_points,
                        model_answer=grade.get("model_answer"),
                        feedback=grade.get("feedback"),
                        confidence_score=grade.get("confidence_score"),
                    )
                )
            logger.info("[STEP 3] Descriptive grading done — descriptive_subtotal=%.2f", descriptive_subtotal)
        else:
            tokens_used = 0
            logger.info("[STEP 3] No descriptive questions — skipping LLM grading call")

        # Step 4: assemble QuizResult
        logger.info("[STEP 4] Assembling QuizResult")
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

        eval_output = QuizAgentOutput(
            status="evaluated",
            quiz=quiz,
            result=quiz_result,
            metadata=QuizAgentMetadata(topic=topic, tokens_used=tokens_used, model=model_name),
            errors=[],
        )
        logger.info("[STEP 4] QuizResult — overall=%.1f/%d (%.1f%%) mcq=%.2f descriptive=%.2f",
                    overall_score, max_score, quiz_result.overall_percentage,
                    mcq_subtotal, descriptive_subtotal)
        logger.info("[STEP 4] weak_sub_concepts: %s", quiz_result.weak_sub_concepts)
        logger.info("[STEP 4] recommended_action: %s", quiz_result.recommended_action)
        logger.debug("[STEP 4] Full QuizAgentOutput schema:\n%s", eval_output.model_dump_json(indent=2))
        logger.info("================================================================")
        logger.info("PHASE 2 — evaluate() DONE  status=evaluated  score=%.1f/%d (%.1f%%)",
                    overall_score, max_score, quiz_result.overall_percentage)
        logger.info("================================================================")
        return eval_output

    # ------------------------------------------------------------------
    # Phase 3: generate_swot
    # ------------------------------------------------------------------

    def generate_swot(self, quiz_result: QuizResult, topic: str) -> SWOTAnalysis:
        """Generate a SWOT analysis from a completed QuizResult via one LLM call.

        Falls back to a minimal derived SWOT if the LLM call fails.
        """
        logger.info("================================================================")
        logger.info("PHASE 3 — generate_swot() START")
        logger.info("================================================================")

        strong_concepts = [
            qr.question_id
            for qr in quiz_result.question_results
            if qr.max_score > 0 and (qr.score / qr.max_score) >= 0.5
        ]
        weak_concepts = quiz_result.weak_sub_concepts

        try:
            config = get_grading_config()
        except RuntimeError as exc:
            logger.error("[SWOT] Config load FAILED — returning fallback: %s", exc)
            return SWOTAnalysis(
                strengths=["Completed the quiz"],
                weaknesses=weak_concepts or ["Areas need review"],
                opportunities=["Review weak sub-concepts"],
                threats=["Risk of knowledge gaps without targeted review"],
            )

        prompt = SWOT_ANALYSIS_PROMPT.format(
            topic=topic,
            overall_score=quiz_result.overall_score,
            max_score=quiz_result.max_score,
            overall_percentage=quiz_result.overall_percentage,
            strong_concepts=", ".join(strong_concepts) or "none",
            weak_concepts=", ".join(weak_concepts) or "none",
            recommended_action=quiz_result.recommended_action,
        )

        try:
            raw, _ = call_llm([{"role": "user", "content": prompt}], config)
            swot_data = parse_swot_response(raw)
            logger.info("[SWOT] SWOT analysis generated OK")
            return SWOTAnalysis(**swot_data)
        except Exception as exc:
            logger.warning("[SWOT] LLM SWOT generation failed — returning fallback: %s", exc)
            return SWOTAnalysis(
                strengths=["Completed the quiz"],
                weaknesses=weak_concepts or ["Areas need review"],
                opportunities=["Review weak sub-concepts"],
                threats=["Risk of knowledge gaps without targeted review"],
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
