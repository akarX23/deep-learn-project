"""Kafka gateway for the RAG service."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Protocol

import logging

from project.schemas import RAGCompletionEvent, TopicPresenceCheckResult
from project.topics import PlannerTopics
from rag_agent.utils.helpers import KafkaRuntimeConfig

logger = logging.getLogger(__name__)


JsonPayload = dict[str, object]


class ConsumerRecordProtocol(Protocol):
    topic: str
    value: JsonPayload


class KafkaConsumerProtocol(Protocol):
    def subscribe(self, topics: list[str]) -> None: ...
    def poll(self, timeout_ms: int) -> dict[object, list[ConsumerRecordProtocol]]: ...
    def topics(self) -> set[str]: ...
    def close(self) -> None: ...


class KafkaProducerProtocol(Protocol):
    def send(self, topic: str, payload: JsonPayload) -> object: ...
    def flush(self) -> None: ...
    def close(self) -> None: ...


def create_producer(config: KafkaRuntimeConfig) -> KafkaProducerProtocol:
    """Create a Kafka producer using shared runtime configuration."""

    try:
        from kafka import KafkaProducer
    except Exception as exc:
        raise RuntimeError("kafka-python is required for producer initialization") from exc

    return KafkaProducer(
        **config.producer_kwargs(),
        value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
    )


def create_consumer(
    config: KafkaRuntimeConfig,
    topics: Iterable[str] | None = None,
) -> KafkaConsumerProtocol:
    """Create a Kafka consumer and optionally subscribe it to topics."""

    try:
        from kafka import KafkaConsumer
    except Exception as exc:
        raise RuntimeError("kafka-python is required for consumer initialization") from exc

    consumer = KafkaConsumer(
        **config.consumer_kwargs(),
        value_deserializer=lambda payload: json.loads(payload.decode("utf-8")),
    )
    if topics:
        consumer.subscribe(list(topics))
    return consumer


def consumer_subscribe_rag(consumer: KafkaConsumerProtocol) -> None:
    """Subscribe the consumer to the inbound RAG topic."""

    consumer.subscribe([PlannerTopics.RAG.value])


def poll_records(
    consumer: KafkaConsumerProtocol,
    timeout_ms: int,
) -> dict[object, list[ConsumerRecordProtocol]]:
    """Poll Kafka for a batch of records."""

    return consumer.poll(timeout_ms=timeout_ms)


def publish_rag_complete(producer: KafkaProducerProtocol, event: RAGCompletionEvent) -> None:
    """Publish a completion event to Kafka."""

    from project.topics import RAGTopics

    producer.send(RAGTopics.RAG_COMPLETE.value, event.model_dump())
    producer.flush()


def check_required_topics(
    consumer: KafkaConsumerProtocol,
    required_topics: Iterable[str],
) -> TopicPresenceCheckResult:
    """Check Kafka metadata for required topic presence."""

    required = list(required_topics)
    existing = sorted(consumer.topics())
    missing = sorted([topic for topic in required if topic not in existing])
    warning_message = None
    if missing:
        warning_message = (
            "Missing required Kafka topics at startup: " + ", ".join(missing)
        )
    return TopicPresenceCheckResult(
        required_topics=required,
        existing_topics=existing,
        missing_topics=missing,
        warning_message=warning_message,
    )


def close_consumer(consumer: KafkaConsumerProtocol | None) -> None:
    """Close consumer if available."""

    if consumer is not None:
        consumer.close()


def close_producer(producer: KafkaProducerProtocol | None) -> None:
    """Flush and close producer if available."""

    if producer is not None:
        producer.flush()
        producer.close()