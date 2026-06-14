"""Minimal Kafka producer/consumer factories for the planner agent."""

from __future__ import annotations

import json

from planner_agent.config import get_bootstrap_servers


def make_producer():
    """Create a Kafka producer with JSON value serialization."""

    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=get_bootstrap_servers(),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def make_consumer(topic: str):
    """Create a Kafka consumer subscribed to a single topic."""

    from kafka import KafkaConsumer

    return KafkaConsumer(
        topic,
        bootstrap_servers=get_bootstrap_servers(),
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        auto_offset_reset="earliest",
        client_id="planner-agent-consumer",
        group_id="planner-agent-group",
    )
