"""FastAPI runtime for Kafka-driven RAG processing."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from typing import Any, Callable

import uvicorn
from fastapi import FastAPI

from project.topics import get_rag_topic_names
from rag_agent.config import KafkaRuntimeConfig
from rag_agent.handlers import RAGRequestEventHandler
from rag_agent.kafka import (
    bootstrap_topics,
    close_consumer,
    close_producer,
    consumer_subscribe_rag,
    create_consumer,
    create_producer,
    poll_records,
)
from rag_agent.logging import StructuredLogger

logger = logging.getLogger(__name__)


def process_consumer_batch(
    consumer: Any,
    producer: Any,
    handler: Callable[[dict[str, Any], Any], None],
    poll_timeout_ms: int,
    lifecycle_logger: StructuredLogger | None = None,
) -> int:
    """Poll once and dispatch all returned Kafka records."""

    batches = poll_records(consumer, timeout_ms=poll_timeout_ms)
    processed = 0
    for records in batches.values():
        for record in records:
            payload = record.value
            request_id = _extract_request_id(payload)
            if lifecycle_logger is not None:
                lifecycle_logger.emit(
                    request_id=request_id,
                    stage="consumed",
                    message="Consumed RAG request event",
                    metadata={"topic": getattr(record, "topic", "rag")},
                )
            try:
                handler(payload, producer)
            except Exception as exc:
                if lifecycle_logger is not None:
                    lifecycle_logger.emit(
                        request_id=request_id,
                        stage="error",
                        level="ERROR",
                        message="Unhandled exception while processing consumed event",
                        metadata={"failure_stage": "dispatch", "error": str(exc)},
                    )
            processed += 1
    return processed


def _poll_loop(app: FastAPI, stop_event: threading.Event) -> None:
    consumer = app.state.kafka_consumer
    producer = app.state.kafka_producer
    handler: Callable[[dict[str, Any], Any], None] = app.state.message_handler
    config: KafkaRuntimeConfig = app.state.kafka_config
    lifecycle_logger: StructuredLogger = app.state.lifecycle_logger

    while not stop_event.is_set():
        try:
            process_consumer_batch(
                consumer,
                producer,
                handler,
                config.poll_timeout_ms,
                lifecycle_logger=lifecycle_logger,
            )
        except Exception:
            logger.exception("Kafka poll loop failed")


def create_app(
    settings: KafkaRuntimeConfig | None = None,
    message_handler: Callable[[dict[str, Any], Any], None] | None = None,
    producer_factory: Callable[[KafkaRuntimeConfig], Any] = create_producer,
    consumer_factory: Callable[[KafkaRuntimeConfig], Any] = create_consumer,
    bootstrapper: Callable[[KafkaRuntimeConfig, list[str]], None] = bootstrap_topics,
    lifecycle_logger: StructuredLogger | None = None,
) -> FastAPI:
    """Create the FastAPI application that owns Kafka lifecycle."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings or KafkaRuntimeConfig.from_env()
        bootstrapper(config, get_rag_topic_names())

        producer = producer_factory(config)
        consumer = consumer_factory(config)
        consumer_subscribe_rag(consumer)

        stop_event = threading.Event()
        resolved_logger = lifecycle_logger or StructuredLogger(logger)
        default_handler = RAGRequestEventHandler(lifecycle_logger=resolved_logger)
        poll_thread = threading.Thread(
            target=_poll_loop,
            args=(app, stop_event),
            daemon=True,
            name="rag-kafka-poll-loop",
        )

        app.state.kafka_config = config
        app.state.kafka_producer = producer
        app.state.kafka_consumer = consumer
        app.state.kafka_stop_event = stop_event
        app.state.kafka_poll_thread = poll_thread
        app.state.lifecycle_logger = resolved_logger
        app.state.message_handler = message_handler or default_handler.process_request

        poll_thread.start()
        try:
            yield
        finally:
            stop_event.set()
            poll_thread.join(timeout=2)
            close_consumer(consumer)
            close_producer(producer)

    app = FastAPI(title="RAG Kafka Service", lifespan=lifespan)
    return app


app = create_app()


def main() -> None:
    """Run the FastAPI service locally."""

    uvicorn.run(app, host="0.0.0.0", port=8002)


def _extract_request_id(payload: dict[str, Any]) -> str:
    raw_request_id = payload.get("request_id")
    if isinstance(raw_request_id, str) and raw_request_id.strip():
        return raw_request_id
    return "unknown"


if __name__ == "__main__":
    main()