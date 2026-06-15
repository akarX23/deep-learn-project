"""Planner agent worker.

A single :func:`run_worker` runs one Kafka consumer subscribed to the init topic
and every agent-completion topic. Each message is routed by ``message.topic``:

* ``init-planner`` -> validate payload (``PlannerRequestEvent``) and start a new
  workflow via :meth:`PlannerAgent.run`.
* completion topics (``rag-complete``, ``teaching-complete``, ``quiz-complete``)
  -> extract the produced outputs and resume the paused workflow via
  :meth:`PlannerAgent.resume`.

The loop logs each stage with request correlation and never dies on a single bad
message (FR-014, FR-016, FR-021).
"""

from __future__ import annotations

import logging

from planner_agent.agent import PlannerAgent
from planner_agent.kafka import make_consumer
from project.schemas import (
    PlannerRequestEvent,
    QuizCompletionEvent,
    RAGCompletionEvent,
    TeachingCompletionEvent,
)
from project.topics import AgentCompletionTopics, PlannerTopics, RAGTopics

logger = logging.getLogger(__name__)

COMPLETION_TOPICS: tuple[str, ...] = (
    RAGTopics.RAG_COMPLETE.value,
    AgentCompletionTopics.TEACHING_COMPLETE.value,
    AgentCompletionTopics.QUIZ_COMPLETE.value,
)


def parse_completion_event(
    topic: str, payload: dict[str, object]
) -> tuple[str, dict[str, object]]:
    """Validate a completion payload and extract ``(request_id, resume outputs)``.

    The returned outputs dict is delivered verbatim to the pending ``interrupt()``
    call when the workflow is resumed. Teaching completions are self-describing
    (each carries its own ``user_level``) so out-of-order resumes are safe. Raises
    ``ValueError`` for an unrecognized topic and lets schema validation errors
    propagate to the caller for logging.
    """

    if topic == RAGTopics.RAG_COMPLETE.value:
        rag = RAGCompletionEvent(**payload)
        return rag.request_id, {"rag_compiled": rag.compiled_material}
    if topic == AgentCompletionTopics.TEACHING_COMPLETE.value:
        teaching = TeachingCompletionEvent(**payload)
        return teaching.request_id, {
            "user_level": teaching.user_level,
            "content": teaching.content,
        }
    if topic == AgentCompletionTopics.QUIZ_COMPLETE.value:
        quiz = QuizCompletionEvent(**payload)
        return quiz.request_id, {"quiz_content": quiz.quiz_content}
    raise ValueError(f"Unknown completion topic: {topic}")


def _handle_init_event(agent: PlannerAgent, payload: dict[str, object]) -> None:
    """Validate an init-planner payload and start a new workflow."""

    request = PlannerRequestEvent(**payload)
    logger.info("Validated init-planner event for sid=%s", request.sid)
    agent.run(payload)


def _handle_completion_event(
    agent: PlannerAgent, topic: str, payload: dict[str, object]
) -> None:
    """Extract completion outputs and resume the matching workflow."""

    request_id, outputs = parse_completion_event(topic, payload)
    logger.info("[%s] Extracted outputs %s from '%s'", request_id, list(outputs), topic)
    agent.resume(request_id, outputs)


def run_worker(agent: PlannerAgent | None = None) -> None:
    """Consume init and completion events on a single consumer and route them."""

    agent = agent or PlannerAgent()
    consumer = make_consumer(PlannerTopics.INIT_PLANNER.value, *COMPLETION_TOPICS)
    topics = [PlannerTopics.INIT_PLANNER.value, *COMPLETION_TOPICS]
    logger.info("Planner worker listening on %s", topics)
    for message in consumer:
        topic = message.topic
        logger.info("Received event on topic '%s'", topic)
        try:
            if topic == PlannerTopics.INIT_PLANNER.value:
                _handle_init_event(agent, message.value)
            else:
                _handle_completion_event(agent, topic, message.value)
            logger.info("Finished processing event on topic '%s'", topic)
        except Exception as exc:  # noqa: BLE001 - keep the worker alive
            logger.exception("Failed to process event on '%s': %s", topic, exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_worker()
