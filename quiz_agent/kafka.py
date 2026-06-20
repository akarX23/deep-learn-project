"""Kafka gateway for the Quiz Agent."""

from __future__ import annotations

import json
import logging
import os

from kafka import KafkaConsumer, KafkaProducer

from project.schemas import QuizCompletionEvent, StreamProgressUpdateEventBody, StreamTokensEventBody
from project.topics import AgentCompletionTopics, BackendStreamTopics, PlannerAgentTopics, QuizAgentTopics

logger = logging.getLogger(__name__)


def _bootstrap_servers() -> str:
    servers = os.environ.get("BACKEND_KAFKA_BOOTSTRAP_SERVERS", "").strip()
    if not servers:
        raise RuntimeError("BACKEND_KAFKA_BOOTSTRAP_SERVERS is required")
    return servers


def create_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=_bootstrap_servers(),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def create_consumer() -> KafkaConsumer:
    consumer = KafkaConsumer(
        bootstrap_servers=_bootstrap_servers(),
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="quiz-service-consumer",
        client_id="quiz-service-consumer",
    )
    consumer.subscribe([PlannerAgentTopics.QUIZ_REQUEST.value])
    return consumer


def create_evaluation_consumer() -> KafkaConsumer:
    consumer = KafkaConsumer(
        bootstrap_servers=_bootstrap_servers(),
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="quiz-eval-consumer",
        client_id="quiz-eval-consumer",
    )
    consumer.subscribe([QuizAgentTopics.QUIZ_EVALUATE.value])
    return consumer


def publish_stream_tokens(producer: KafkaProducer, event: StreamTokensEventBody) -> None:
    producer.send(BackendStreamTopics.STREAM_TOKENS.value, event.model_dump())
    producer.flush()


def publish_quiz_complete(producer: KafkaProducer, event: QuizCompletionEvent) -> None:
    producer.send(AgentCompletionTopics.QUIZ_COMPLETE.value, event.model_dump())
    producer.flush()


def publish_stream_progress_update(
    producer: KafkaProducer,
    event: StreamProgressUpdateEventBody,
) -> None:
    producer.send(BackendStreamTopics.STREAM_PROGRESS_UPDATE.value, event.model_dump())
    producer.flush()
