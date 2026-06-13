"""Inbound Kafka request handlers for the RAG service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

import logging

from project.schemas import RAGAgentInput, RAGCompletionEvent, RAGRequestEvent, RAGAgentOutput
from rag_agent.agent import RAGAgent
from rag_agent.kafka import KafkaProducerProtocol, publish_rag_complete

logger = logging.getLogger(__name__)


class RAGRequestEventHandler:
    """Ingest Kafka request events and dispatch them to the RAG pipeline."""

    def __init__(
        self,
        agent_factory: Callable[[], RAGAgent] = RAGAgent,
        publisher: Callable[[KafkaProducerProtocol, RAGCompletionEvent], None] = publish_rag_complete,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._agent_factory = agent_factory
        self._publisher = publisher
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def parse_event(self, payload: dict[str, object]) -> RAGRequestEvent:
        """Parse inbound payload into request event schema."""

        # TODO: Add richer schema and semantic validation in a follow-up task.
        return RAGRequestEvent.model_validate(payload)

    def build_completion_event(
        self,
        event: RAGRequestEvent,
        result: RAGAgentOutput,
        started_at: datetime,
        completed_at: datetime,
    ) -> RAGCompletionEvent:
        """Map agent output into the outbound Kafka completion contract."""

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

    def process_request(
        self,
        payload: dict[str, object],
        producer: KafkaProducerProtocol | None = None,
    ) -> RAGCompletionEvent | None:
        """Convert a parsed request event into a RAGAgent execution."""

        raw_request_id = _extract_request_id(payload)
        try:
            event = self.parse_event(payload)
        except Exception as exc:
            logger.error("rejected invalid RAG request event request_id=%s error=%s", raw_request_id, exc)
            # TODO: Add specific exception handling for validation errors
            return None

        started_at = self._clock()
        request = RAGAgentInput(
            request_id=event.request_id,
            user_prompt=event.user_request,
            file_paths=event.file_paths,
        )
        agent = self._agent_factory()
        logger.info("processing_started request_id=%s file_count=%d", event.request_id, len(event.file_paths))
        # TODO: Add timing and throughput metrics counters in a follow-up task.
        try:
            result = agent.run(request)
        except Exception as exc:
            completed_at = self._clock()
            logger.error("processing_failed request_id=%s error=%s", event.request_id, exc)
            # TODO: Add specific exception handling for pipeline failures
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
            completed_at = self._clock()
            completion_event = self.build_completion_event(event, result, started_at, completed_at)
            logger.info("processing_completed request_id=%s status=%s", event.request_id, completion_event.status)

        if producer is not None:
            try:
                self._publisher(producer, completion_event)
            except Exception as exc:
                logger.error("publish_failed request_id=%s error=%s", event.request_id, exc)
                # TODO: Add specific exception handling for publish failures
            else:
                logger.info("publish_completed request_id=%s status=%s", event.request_id, completion_event.status)
        return completion_event


def _isoformat_utc(value: datetime) -> str:
    """Serialize datetimes consistently in UTC."""

    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_request_id(payload: dict[str, object]) -> str:
    """Extract request_id from raw inbound payload."""

    raw_request_id = payload.get("request_id")
    if isinstance(raw_request_id, str) and raw_request_id.strip():
        return raw_request_id
    return "unknown"