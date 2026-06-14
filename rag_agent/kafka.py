"""Kafka gateway for the RAG service."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Protocol

import logging

from project.schemas import RAGCompletionEvent, TopicPresenceCheckResult
from project.topics import PlannerTopics, RAGTopics
from rag_agent.utils.helpers import (
    apply_kafka_security_options,
    get_kafka_runtime_config,
)

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


def _producer_kwargs(config: dict[str, object]) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "bootstrap_servers": config["bootstrap_servers"],
        "client_id": config["client_id"],
    }
    apply_kafka_security_options(kwargs, config)
    return kwargs


def _consumer_kwargs(config: dict[str, object]) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "bootstrap_servers": config["bootstrap_servers"],
        "client_id": config["client_id"],
        "group_id": config["consumer_group_id"],
        "enable_auto_commit": True,
        "auto_offset_reset": "earliest",
    }
    apply_kafka_security_options(kwargs, config)
    return kwargs


def create_producer(config: dict[str, object] | None = None) -> KafkaProducerProtocol:
    """Create a Kafka producer using shared runtime configuration."""

    try:
        from kafka import KafkaProducer
    except Exception as exc:
        raise RuntimeError(
            "kafka-python is required for producer initialization"
        ) from exc

    runtime_config = config or get_kafka_runtime_config()
    return KafkaProducer(
        **_producer_kwargs(runtime_config),
        value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
    )


def create_consumer(
    config: dict[str, object] | None = None,
    topics: Iterable[str] | None = None,
) -> KafkaConsumerProtocol:
    """Create a Kafka consumer and optionally subscribe it to topics."""

    try:
        from kafka import KafkaConsumer
    except Exception as exc:
        raise RuntimeError(
            "kafka-python is required for consumer initialization"
        ) from exc

    runtime_config = config or get_kafka_runtime_config()
    consumer = KafkaConsumer(
        **_consumer_kwargs(runtime_config),
        value_deserializer=lambda payload: json.loads(payload.decode("utf-8")),
    )
    if topics:
        consumer.subscribe(list(topics))
    return consumer


def create_kafka_connectors_from_env() -> tuple[
    KafkaProducerProtocol, KafkaConsumerProtocol, dict[str, object]
]:
    """Initialize producer and consumer directly from environment variables."""

    # TODO: Add connector health checks and bounded retry strategy for startup.
    runtime_config = get_kafka_runtime_config()
    producer = create_producer(runtime_config)
    consumer = create_consumer(runtime_config)
    return producer, consumer, runtime_config


def consumer_subscribe_rag(consumer: KafkaConsumerProtocol) -> None:
    """Subscribe the consumer to the inbound RAG topic."""

    consumer.subscribe([PlannerTopics.RAG.value])


def poll_records(
    consumer: KafkaConsumerProtocol,
    timeout_ms: int,
) -> dict[object, list[ConsumerRecordProtocol]]:
    """Poll Kafka for a batch of records."""

    return consumer.poll(timeout_ms=timeout_ms)


def publish_rag_complete(
    producer: KafkaProducerProtocol, event: RAGCompletionEvent
) -> None:
    """Publish a completion event to Kafka."""

    producer.send(RAGTopics.RAG_COMPLETE.value, event.model_dump())
    producer.flush()


def check_required_topics(
    consumer: KafkaConsumerProtocol,
    required_topics: Iterable[str],
) -> TopicPresenceCheckResult:
    """Check Kafka metadata for required topic presence."""

    # TODO: Add metadata fetch timeout handling and structured diagnostics.
    required = list(required_topics)
    existing = sorted(consumer.topics())
    missing = sorted([topic for topic in required if topic not in existing])
    warning_message = None
    if missing:
        warning_message = "Missing required Kafka topics at startup: " + ", ".join(
            missing
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
