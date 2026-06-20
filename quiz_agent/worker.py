"""Standalone Kafka worker runtime for Quiz Agent event processing."""

from __future__ import annotations

import logging

from project.schemas import (
    ProgressUpdatePage,
    QuizCompletionEvent,
    QuizEvaluateRequestEvent,
    QuizEvaluationStreamPayload,
    QuizRequestEvent,
    StreamProgressUpdateEventBody,
    StreamTokensEventBody,
    SWOTAnalysis,
)
from quiz_agent.agent import QuizAgent
from quiz_agent.kafka import (
    create_consumer,
    create_producer,
    publish_quiz_complete,
    publish_stream_progress_update,
    publish_stream_tokens,
)

logger = logging.getLogger(__name__)
logging.getLogger("kafka").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)


def run() -> None:
    """Start the quiz agent consumer loop with routing based on message topic."""
    from project.topics import PlannerAgentTopics, QuizAgentTopics

    producer = create_producer()
    consumer = create_consumer()

    # Subscribe to both topics
    consumer.subscribe([PlannerAgentTopics.QUIZ_REQUEST.value, QuizAgentTopics.QUIZ_EVALUATE.value])

    logger.info("quiz-agent worker started, listening on quiz-request and quiz-evaluate")

    agent = QuizAgent()

    def handle_quiz_request(message) -> None:
        payload: dict = message.value
        event = QuizRequestEvent.model_validate(payload)

        def publish_progress(update: str) -> None:
            publish_stream_progress_update(
                producer,
                StreamProgressUpdateEventBody(
                    sid=event.sid,
                    for_page=ProgressUpdatePage.QUIZ,
                    update=update,
                ),
            )

        publish_progress("Starting quiz generation")

        teaching_content = "\n\n".join(event.teaching_materials.values())
        raw_input = {
            "topic": event.user_prompt,
            "teaching_content": teaching_content,
        }

        result = agent.generate(raw_input, progress_callback=publish_progress)

        if result.status == "generated" and result.quiz is not None:
            publish_progress(
                f"Questions generated: {len(result.quiz.questions)} total."
            )
            publish_progress("Quiz generation completed")
        else:
            publish_progress("Quiz generation failed")

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
                content=result.model_dump(),
            ),
        )

        logger.info("quiz request processed request_id=%s", event.request_id)

    def handle_quiz_evaluate(message) -> None:
        payload: dict = message.value
        event = QuizEvaluateRequestEvent.model_validate(payload)

        def publish_eval_progress(update: str) -> None:
            publish_stream_progress_update(
                producer,
                StreamProgressUpdateEventBody(
                    sid=event.sid,
                    for_page=ProgressUpdatePage.EVAL,
                    update=update,
                ),
            )

        publish_eval_progress("Starting quiz evaluation")

        eval_output = agent.evaluate(
            event.quiz,
            event.answers,
            progress_callback=publish_eval_progress,
        )
        quiz_topic = event.quiz.get("topic", "") if isinstance(event.quiz, dict) else getattr(event.quiz, "topic", "")

        swot: SWOTAnalysis | None = None

        if eval_output.status == "evaluated" and eval_output.result is not None:
            publish_eval_progress("Generating SWOT analysis")
            swot = agent.generate_swot(
                eval_output.result,
                quiz_topic,
                progress_callback=publish_eval_progress,
            )
            publish_eval_progress("Evaluation completed")
        else:
            publish_eval_progress("Evaluation failed")

        stream_payload = QuizEvaluationStreamPayload(
            result=eval_output.result.model_dump() if eval_output.result else {},
            swot=swot,
        )

        publish_stream_tokens(
            producer,
            StreamTokensEventBody(
                from_service="eval-agent",
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

    # Poll single consumer and route based on topic
    for message in consumer:
        if message.topic == QuizAgentTopics.QUIZ_EVALUATE.value:
            handle_quiz_evaluate(message)
        elif message.topic == PlannerAgentTopics.QUIZ_REQUEST.value:
            handle_quiz_request(message)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
