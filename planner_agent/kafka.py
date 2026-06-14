"""Minimal Kafka producer/consumer factories for the planner agent."""

from __future__ import annotations

import json

from planner_agent.config import get_bootstrap_servers

from kafka import KafkaConsumer, KafkaProducer


def make_producer() -> KafkaProducer:
    """Create a Kafka producer with JSON value serialization and string keys.

    The key serializer encodes the message key (the workflow ``request_id``) as
    UTF-8 so dispatched events are partitioned/correlated by request. ``None``
    keys are passed through unchanged.
    """

    return KafkaProducer(
        bootstrap_servers=get_bootstrap_servers(),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda key: key.encode("utf-8") if key is not None else None,
    )


def make_consumer(*topics: str) -> KafkaConsumer:
    """Create a Kafka consumer subscribed to one or more topics."""

    return KafkaConsumer(
        *topics,
        bootstrap_servers=get_bootstrap_servers(),
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        auto_offset_reset="earliest",
        client_id="planner-service-consumer",
        group_id="planner-service-consumer",
    )
