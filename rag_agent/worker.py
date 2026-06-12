"""Standalone Kafka worker runtime for RAG event processing."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from project.schemas import RAGCompletionEvent, WorkerRuntimeState
from project.topics import get_rag_topic_names
from rag_agent.config import KafkaRuntimeConfig
from rag_agent.handlers import RAGRequestEventHandler
from rag_agent.kafka import (
    KafkaConsumerProtocol,
    KafkaProducerProtocol,
    check_required_topics,
    close_consumer,
    close_producer,
    consumer_subscribe_rag,
    create_consumer,
    create_producer,
    poll_records,
)
from rag_agent.logging import StructuredLogger

RequestHandler = Callable[[dict[str, object], KafkaProducerProtocol | None], RAGCompletionEvent | None]


def _extract_request_id(payload: dict[str, object]) -> str:
    raw_request_id = payload.get("request_id")
    if isinstance(raw_request_id, str) and raw_request_id.strip():
        return raw_request_id
    return "unknown"


def process_consumer_batch(
    consumer: KafkaConsumerProtocol,
    producer: KafkaProducerProtocol,
    handler: RequestHandler,
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


class RAGWorker:
    """Owns worker lifecycle for Kafka consume-dispatch-publish processing."""

    def __init__(
        self,
        config: KafkaRuntimeConfig | None = None,
        producer_factory: Callable[[KafkaRuntimeConfig], KafkaProducerProtocol] = create_producer,
        consumer_factory: Callable[[KafkaRuntimeConfig], KafkaConsumerProtocol] = create_consumer,
        handler_factory: Callable[[], RAGRequestEventHandler] = RAGRequestEventHandler,
        lifecycle_logger: StructuredLogger | None = None,
    ) -> None:
        self._config = config
        self._producer_factory = producer_factory
        self._consumer_factory = consumer_factory
        self._handler_factory = handler_factory
        self._logger = lifecycle_logger or StructuredLogger()
        self._producer: KafkaProducerProtocol | None = None
        self._consumer: KafkaConsumerProtocol | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._startup_warnings: list[str] = []
        self._startup_check_complete = False

    @property
    def config(self) -> KafkaRuntimeConfig:
        if self._config is None:
            self._config = KafkaRuntimeConfig.from_env()
        return self._config

    def start(self) -> None:
        """Initialize Kafka clients, run startup checks, and start poll loop thread."""

        self._producer = self._producer_factory(self.config)
        self._consumer = self._consumer_factory(self.config)
        consumer_subscribe_rag(self._consumer)

        topic_check = check_required_topics(self._consumer, get_rag_topic_names())
        self._startup_warnings = []
        self._startup_check_complete = True
        if topic_check.warning_message:
            self._startup_warnings.append(topic_check.warning_message)
            self._logger.emit_startup_topic_check(
                missing_topics=topic_check.missing_topics,
                level="WARNING",
            )
        else:
            self._logger.emit_startup_topic_check(missing_topics=[])

        handler = self._handler_factory().process_request
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            args=(handler,),
            daemon=True,
            name="rag-kafka-worker-loop",
        )
        self._thread.start()

    def _poll_loop(self, handler: RequestHandler) -> None:
        if self._consumer is None or self._producer is None:
            return
        while not self._stop_event.is_set():
            try:
                process_consumer_batch(
                    self._consumer,
                    self._producer,
                    handler,
                    self.config.poll_timeout_ms,
                    self._logger,
                )
            except Exception as exc:
                self._logger.emit(
                    request_id="worker",
                    stage="error",
                    level="ERROR",
                    message="Worker poll loop failure",
                    metadata={"failure_stage": "poll_loop", "error": str(exc)},
                )

    def stop(self) -> None:
        """Stop poll loop and close Kafka resources."""

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        close_consumer(self._consumer)
        close_producer(self._producer)

    def get_state(self) -> WorkerRuntimeState:
        """Return a typed snapshot of worker runtime state."""

        return WorkerRuntimeState(
            running=self._thread is not None and self._thread.is_alive(),
            stop_event_set=self._stop_event.is_set(),
            poll_thread_alive=self._thread is not None and self._thread.is_alive(),
            startup_topic_check_complete=self._startup_check_complete,
            startup_topic_check_warnings=self._startup_warnings,
        )


def main() -> None:
    """Run worker until interrupted."""

    worker = RAGWorker()
    worker.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        worker.stop()


if __name__ == "__main__":
    main()