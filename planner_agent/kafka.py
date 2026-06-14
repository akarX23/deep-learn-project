"""Minimal Kafka producer/consumer factories for the planner agent."""

from __future__ import annotations

import json

from planner_agent.config import get_bootstrap_servers

from kafka import KafkaConsumer, KafkaProducer


def make_producer() -> KafkaProducer:
    """Create a Kafka producer with JSON value serialization."""

    return KafkaProducer(
        bootstrap_servers=get_bootstrap_servers(),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def make_consumer(topic: str) -> KafkaConsumer:
    """Create a Kafka consumer subscribed to a single topic."""

    return KafkaConsumer(
        topic,
        bootstrap_servers=get_bootstrap_servers(),
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        auto_offset_reset="earliest",
        client_id="planner-agent-consumer",
        group_id="planner-agent-group",
    )
