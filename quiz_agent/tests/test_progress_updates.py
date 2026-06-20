"""Progress callback tests for quiz/evaluation stage updates."""

from __future__ import annotations

from typing import Any

from quiz_agent.agent import QuizAgent
from quiz_agent.helpers import parse_swot_response


def test_expand_mcq_parallel_emits_incremental_progress(monkeypatch) -> None:
    agent = QuizAgent()
    progress_messages: list[str] = []

    def fake_expand_single_mcq_question(question: dict[str, Any], *_args: Any) -> tuple[dict[str, Any], int]:
        updated = dict(question)
        updated["options"] = [
            {"id": "a", "text": "A", "is_correct": True, "explanation": "ok"},
            {"id": "b", "text": "B", "is_correct": False, "explanation": "no"},
            {"id": "c", "text": "C", "is_correct": False, "explanation": "no"},
            {"id": "d", "text": "D", "is_correct": False, "explanation": "no"},
        ]
        updated["topic_deep_dive"] = "deep dive"
        return updated, 5

    monkeypatch.setattr(agent, "_expand_single_mcq_question", fake_expand_single_mcq_question)

    stem_parsed = {
        "questions": [
            {
                "id": "q1",
                "type": "mcq-single",
                "prompt": "P1",
                "sub_concept": "S1",
                "max_points": 1,
            },
            {
                "id": "q2",
                "type": "mcq-multi",
                "prompt": "P2",
                "sub_concept": "S2",
                "max_points": 2,
            },
            {
                "id": "q3",
                "type": "descriptive",
                "prompt": "P3",
                "sub_concept": "S3",
                "max_points": 5,
                "rubric": ["r1"],
            },
        ]
    }

    parsed, tokens_used = agent._expand_mcq_questions_parallel(
        stem_parsed,
        topic="Topic",
        content="Content",
        config=object(),
        progress_callback=progress_messages.append,
    )

    assert tokens_used == 10
    assert len(parsed["questions"]) == 3
    assert "MCQ questions generated: 1/2." in progress_messages
    assert "MCQ questions generated: 2/2." in progress_messages


def test_generate_swot_emits_ready_progress(monkeypatch) -> None:
    agent = QuizAgent()
    progress_messages: list[str] = []

    quiz_result = {
        "overall_score": 10,
        "max_score": 20,
        "overall_percentage": 50,
        "mcq_subtotal": 5,
        "descriptive_subtotal": 5,
        "question_results": [],
        "weak_sub_concepts": ["concept-1"],
        "recommended_action": "revise",
    }

    def fake_call_llm(_messages: list[dict[str, str]], _config: Any) -> tuple[str, int]:
        return (
            '{"strengths":["s"],"weaknesses":["w"],"opportunities":["o"],"threats":["t"]}',
            11,
        )

    monkeypatch.setattr("quiz_agent.agent.call_llm", fake_call_llm)
    monkeypatch.setattr("quiz_agent.agent.parse_swot_response", parse_swot_response)

    from project.schemas import QuizResult

    swot = agent.generate_swot(
        QuizResult.model_validate(quiz_result),
        topic="Topic",
        progress_callback=progress_messages.append,
    )

    assert swot.strengths == ["s"]
    assert "Generating SWOT feedback." in progress_messages
    assert "SWOT analysis ready." in progress_messages
