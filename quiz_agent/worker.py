"""Standalone Kafka worker runtime for Quiz Agent event processing."""

from __future__ import annotations

import logging

from project.schemas import (
    QuizCompletionEvent,
    QuizEvaluateRequestEvent,
    QuizEvaluationStreamPayload,
    QuizRequestEvent,
    StreamTokensEventBody,
)
from quiz_agent.agent import QuizAgent
from quiz_agent.kafka import (
    create_consumer,
    create_evaluation_consumer,
    create_producer,
    publish_quiz_complete,
    publish_stream_tokens,
)

logger = logging.getLogger(__name__)


def run() -> None:
    """Start the quiz agent consumer loop for quiz generation requests."""
    producer = create_producer()
    consumer = create_consumer()

    logger.info("quiz-agent worker started, listening on quiz-request")

    for message in consumer:
        payload: dict = message.value
        event = QuizRequestEvent.model_validate(payload)

        teaching_content = "\n\n".join(event.teaching_materials.values())
        raw_input = {
            "topic": event.user_prompt,
            "teaching_content": teaching_content,
        }

        result = QuizAgent().generate(raw_input)

        publish_stream_tokens(
            producer,
            StreamTokensEventBody(
                from_service="quiz-agent",
                sid=event.sid,
                data=result.model_dump(),
            ),
        )

        publish_quiz_complete(
            producer,
            QuizCompletionEvent(
                request_id=event.request_id,
                sid=event.sid,
            ),
        )

        logger.info("quiz request processed request_id=%s", event.request_id)


def run_evaluation() -> None:
    """Start the quiz agent consumer loop for answer evaluation requests."""
    producer = create_producer()
    consumer = create_evaluation_consumer()

    logger.info("quiz-agent eval worker started, listening on quiz-evaluate")

    agent = QuizAgent()

    for message in consumer:
        payload: dict = message.value
        event = QuizEvaluateRequestEvent.model_validate(payload)

        eval_output = agent.evaluate(event.quiz, event.answers)

        swot = agent.generate_swot(eval_output.result, event.quiz.get("topic", ""))

        stream_payload = QuizEvaluationStreamPayload(
            result=eval_output.result.model_dump() if eval_output.result else {},
            swot=swot,
        )

        publish_stream_tokens(
            producer,
            StreamTokensEventBody(
                from_service="quiz-agent",
                sid=event.sid,
                data=stream_payload.model_dump(),
            ),
        )

        publish_quiz_complete(
            producer,
            QuizCompletionEvent(
                request_id=event.request_id,
                sid=event.sid,
            ),
        )

        logger.info("quiz evaluation processed request_id=%s", event.request_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
