"""Kafka gateway for the RAG service."""

from __future__ import annotations

import json
from typing import Any, Iterable

import httpx

from project.schemas import RAGCompletionEvent
from project.topics import PlannerTopics
from rag_agent.config import KafkaRuntimeConfig


def create_producer(config: KafkaRuntimeConfig):
    """Create a Kafka producer using shared runtime configuration."""

    try:
        from kafka import KafkaProducer
    except Exception as exc:
        raise RuntimeError("kafka-python is required for producer initialization") from exc

    return KafkaProducer(
        **config.producer_kwargs(),
        value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
    )


def create_consumer(config: KafkaRuntimeConfig, topics: Iterable[str] | None = None):
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


def consumer_subscribe_rag(consumer) -> None:
    """Subscribe the consumer to the inbound RAG topic."""

    consumer.subscribe([PlannerTopics.RAG.value])


def poll_records(consumer, timeout_ms: int) -> dict[Any, list[Any]]:
    """Poll Kafka for a batch of records."""

    return consumer.poll(timeout_ms=timeout_ms)


def publish_rag_complete(producer, event: RAGCompletionEvent) -> None:
    """Publish a completion event to Kafka."""

    from project.topics import RAGTopics

    producer.send(RAGTopics.RAG_COMPLETE.value, event.model_dump())
    producer.flush()


def bootstrap_topics(config: KafkaRuntimeConfig, topic_names: Iterable[str]) -> None:
    """Call the backend topic API to ensure required topics exist."""

    with httpx.Client(timeout=10.0) as client:
        for topic_name in topic_names:
            response = client.post(
                config.topic_api_url,
                json={
                    "topic_name": topic_name,
                    "num_partitions": 1,
                    "replication_factor": 1,
                },
            )
            response.raise_for_status()


def close_consumer(consumer) -> None:
    """Close consumer if available."""

    if consumer is not None:
        consumer.close()


def close_producer(producer) -> None:
    """Flush and close producer if available."""

    if producer is not None:
        producer.flush()
        producer.close()