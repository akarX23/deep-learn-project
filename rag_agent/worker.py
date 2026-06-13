"""Standalone Kafka worker runtime for RAG event processing."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone

import logging

from project.schemas import (
    RAGAgentInput,
    RAGCompletionEvent,
    RAGRequestEvent,
    RAGAgentOutput,
    WorkerRuntimeState,
)
from project.topics import get_rag_topic_names
from rag_agent.agent import RAGAgent
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
    publish_rag_complete,
)
from rag_agent.utils.helpers import get_kafka_runtime_config

logger = logging.getLogger(__name__)

RequestProcessor = Callable[
    [dict[str, object], KafkaProducerProtocol], RAGCompletionEvent | None
]


def _extract_request_id(payload: dict[str, object]) -> str:
    raw_request_id = payload.get("request_id")
    if isinstance(raw_request_id, str) and raw_request_id.strip():
        return raw_request_id
    return "unknown"


def _isoformat_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_completion_event(
    event: RAGRequestEvent,
    result: RAGAgentOutput,
    started_at: datetime,
    completed_at: datetime,
) -> RAGCompletionEvent:
    duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))
    return RAGCompletionEvent(
        request_id=event.request_id,
        session_ctx=event.session_ctx,
        user_prompt=result.user_prompt,
        compiled_material=result.compiled_material,
        status=result.status,
        errors=result.errors,
        total_pages_processed=result.total_pages_processed,
        total_pages_included=result.total_pages_included,
        started_at=_isoformat_utc(started_at),
        completed_at=_isoformat_utc(completed_at),
        duration_ms=duration_ms,
    )


def process_request_event(
    payload: dict[str, object],
    producer: KafkaProducerProtocol,
    agent_factory: Callable[[], RAGAgent] = RAGAgent,
    publisher: Callable[
        [KafkaProducerProtocol, RAGCompletionEvent], None
    ] = publish_rag_complete,
    clock: Callable[[], datetime] | None = None,
) -> RAGCompletionEvent | None:
    """Process one request event with direct worker -> agent -> publish flow."""

    now = clock or (lambda: datetime.now(timezone.utc))
    raw_request_id = _extract_request_id(payload)
    try:
        event = RAGRequestEvent.model_validate(payload)
    except Exception as exc:
        logger.error(
            "rejected invalid RAG request event request_id=%s error=%s",
            raw_request_id,
            exc,
        )
        # TODO: Add richer validation error classification and response behavior.
        return None

    started_at = now()
    request = RAGAgentInput(
        request_id=event.request_id,
        user_prompt=event.user_request,
        file_paths=event.file_paths,
    )

    logger.info(
        "processing_started request_id=%s file_count=%d",
        event.request_id,
        len(event.file_paths),
    )
    try:
        result = agent_factory().run(request)
    except Exception as exc:
        completed_at = now()
        logger.error("processing_failed request_id=%s error=%s", event.request_id, exc)
        # TODO: Add retry/backoff policy and failure taxonomy for processing exceptions.
        completion_event = RAGCompletionEvent(
            request_id=event.request_id,
            session_ctx=event.session_ctx,
            user_prompt=event.user_request,
            compiled_material="",
            status="failed",
            errors=[str(exc)],
            total_pages_processed=0,
            total_pages_included=0,
            started_at=_isoformat_utc(started_at),
            completed_at=_isoformat_utc(completed_at),
            duration_ms=max(0, int((completed_at - started_at).total_seconds() * 1000)),
        )
    else:
        completed_at = now()
        completion_event = _build_completion_event(
            event, result, started_at, completed_at
        )
        logger.info(
            "processing_completed request_id=%s status=%s",
            event.request_id,
            completion_event.status,
        )

    try:
        publisher(producer, completion_event)
    except Exception as exc:
        logger.error("publish_failed request_id=%s error=%s", event.request_id, exc)
        # TODO: Add dead-letter and idempotent publish handling.
    else:
        logger.info(
            "publish_completed request_id=%s status=%s",
            event.request_id,
            completion_event.status,
        )
    return completion_event


def process_consumer_batch(
    consumer: KafkaConsumerProtocol,
    producer: KafkaProducerProtocol,
    processor: RequestProcessor,
    poll_timeout_ms: int,
) -> int:
    """Poll once and dispatch all returned Kafka records."""

    batches = poll_records(consumer, timeout_ms=poll_timeout_ms)
    processed = 0
    for records in batches.values():
        for record in records:
            payload = record.value
            request_id = _extract_request_id(payload)
            logger.info(
                "consumed request_id=%s topic=%s",
                request_id,
                getattr(record, "topic", "rag"),
            )
            try:
                processor(payload, producer)
            except Exception as exc:
                logger.error("dispatch error request_id=%s error=%s", request_id, exc)
            processed += 1
    return processed


class RAGWorker:
    """Owns worker lifecycle for Kafka consume-dispatch-publish processing."""

    def __init__(
        self,
        config: dict[str, object] | None = None,
        producer_factory: Callable[
            [dict[str, object]], KafkaProducerProtocol
        ] = create_producer,
        consumer_factory: Callable[
            [dict[str, object]], KafkaConsumerProtocol
        ] = create_consumer,
        request_processor: RequestProcessor = process_request_event,
    ) -> None:
        self._config = config
        self._producer_factory = producer_factory
        self._consumer_factory = consumer_factory
        self._request_processor = request_processor
        self._producer: KafkaProducerProtocol | None = None
        self._consumer: KafkaConsumerProtocol | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._startup_warnings: list[str] = []
        self._startup_check_complete = False

    @property
    def config(self) -> dict[str, object]:
        if self._config is None:
            self._config = get_kafka_runtime_config()
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
            logger.warning("startup_topic_check missing=%s", topic_check.missing_topics)
        else:
            logger.info("startup_topic_check all required topics present")

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            args=(self._request_processor,),
            daemon=True,
            name="rag-kafka-worker-loop",
        )
        self._thread.start()

    def _poll_loop(self, processor: RequestProcessor) -> None:
        if self._consumer is None or self._producer is None:
            return
        while not self._stop_event.is_set():
            try:
                process_consumer_batch(
                    self._consumer,
                    self._producer,
                    processor,
                    int(self.config.get("poll_timeout_ms", 1000)),
                )
            except Exception as exc:
                logger.error("poll_loop failure error=%s", exc)

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

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
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
