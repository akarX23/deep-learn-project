"""Kafka gateway for the RAG service."""

from __future__ import annotations

import json
from collections.abc import Iterable

import logging
from kafka import KafkaConsumer, KafkaProducer

from project.schemas import RAGCompletionEvent, TopicPresenceCheckResult
from project.topics import RAGTopics
from rag_agent.utils.helpers import get_kafka_runtime_config

logger = logging.getLogger(__name__)


JsonPayload = dict[str, object]

_SECURITY_CONFIG_TO_KAFKA = {
    "security_protocol": "security_protocol",
    "sasl_mechanism": "sasl_mechanism",
    "sasl_username": "sasl_plain_username",
    "sasl_password": "sasl_plain_password",
    "ssl_cafile": "ssl_cafile",
}


def _security_kwargs(config: dict[str, object]) -> dict[str, object]:
    return {
        kafka_key: config_key_value
        for config_key, kafka_key in _SECURITY_CONFIG_TO_KAFKA.items()
        if (config_key_value := config.get(config_key))
    }


def _producer_kwargs(config: dict[str, object]) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "bootstrap_servers": config["bootstrap_servers"],
        "client_id": config["client_id"],
    }
    kwargs.update(_security_kwargs(config))
    return kwargs


def _consumer_kwargs(config: dict[str, object]) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "bootstrap_servers": config["bootstrap_servers"],
        "client_id": config["client_id"],
        "group_id": config["consumer_group_id"],
        "enable_auto_commit": True,
        "auto_offset_reset": "earliest",
    }
    kwargs.update(_security_kwargs(config))
    return kwargs


def create_producer(config: dict[str, object] | None = None) -> KafkaProducer:
    """Create a Kafka producer using shared runtime configuration."""

    runtime_config = config or get_kafka_runtime_config()
    return KafkaProducer(
        **_producer_kwargs(runtime_config),
        value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
    )


def create_consumer(
    config: dict[str, object] | None = None,
    topics: Iterable[str] | None = None,
) -> KafkaConsumer:
    """Create a Kafka consumer and optionally subscribe it to topics."""

    runtime_config = config or get_kafka_runtime_config()
    consumer = KafkaConsumer(
        **_consumer_kwargs(runtime_config),
        value_deserializer=lambda payload: json.loads(payload.decode("utf-8")),
    )
    if topics:
        consumer.subscribe(list(topics))
    return consumer


def create_kafka_connectors_from_env() -> tuple[
    KafkaProducer, KafkaConsumer, dict[str, object]
]:
    """Initialize producer and consumer directly from environment variables."""

    # TODO: Add connector health checks and bounded retry strategy for startup.
    runtime_config = get_kafka_runtime_config()
    producer = create_producer(runtime_config)
    consumer = create_consumer(runtime_config)
    return producer, consumer, runtime_config


def publish_rag_complete(producer: KafkaProducer, event: RAGCompletionEvent) -> None:
    """Publish a completion event to Kafka."""

    producer.send(RAGTopics.RAG_COMPLETE.value, event.model_dump())
    producer.flush()


def check_required_topics(
    consumer: KafkaConsumer,
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
