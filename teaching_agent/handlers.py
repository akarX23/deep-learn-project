"""Inbound Kafka request handlers for the Teaching Agent."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from project.schemas import (
    TeachingAgentOutput,
    TeachingCompletionEvent,
    TeachingRequestEvent,
)
from teaching_agent.agent import TeachingAgent
from teaching_agent.kafka import KafkaProducerProtocol, publish_teaching_complete

logger = logging.getLogger(__name__)


class TeachingRequestEventHandler:
    """Ingest Kafka request events and dispatch them to the Teaching Agent pipeline."""

    def __init__(
        self,
        agent_factory: Callable[[], TeachingAgent] = TeachingAgent,
        publisher: Callable[
            [KafkaProducerProtocol, TeachingCompletionEvent], None
        ] = publish_teaching_complete,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._agent_factory = agent_factory
        self._publisher = publisher
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def parse_event(self, payload: dict[str, object]) -> TeachingRequestEvent:
        """Parse inbound payload into request event schema."""
        return TeachingRequestEvent.model_validate(payload)

    def build_completion_event(
        self,
        event: TeachingRequestEvent,
        result: TeachingAgentOutput,
        started_at: datetime,
        completed_at: datetime,
    ) -> TeachingCompletionEvent:
        """Map agent output into the outbound Kafka completion contract."""
        duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))
        return TeachingCompletionEvent(
            request_id=event.request_id,
            session_ctx=event.session_ctx,
            topic=event.topic,
            output_mode=event.output_mode,
            status=result.status,
            content=result.content,
            tokens_used=result.metadata.tokens_used,
            model=result.metadata.model,
            started_at=_isoformat_utc(started_at),
            completed_at=_isoformat_utc(completed_at),
            duration_ms=duration_ms,
        )

    def process_request(
        self,
        payload: dict[str, object],
        producer: KafkaProducerProtocol | None = None,
    ) -> TeachingCompletionEvent | None:
        """Convert a Kafka request payload into a TeachingAgent execution."""
        raw_request_id = _extract_request_id(payload)
        try:
            event = self.parse_event(payload)
        except Exception as exc:
            logger.error(
                "rejected invalid teaching request event request_id=%s error=%s",
                raw_request_id, exc,
            )
            return None  # malformed payload — no completion event published

        started_at = self._clock()
        agent = self._agent_factory()
        logger.info(
            "processing_started request_id=%s topic=%s mode=%s",
            event.request_id, event.topic, event.output_mode,
        )

        try:
            result = agent.run({
                "topic": event.topic,
                "output_mode": event.output_mode,
                "context": event.context,
            })
            completed_at = self._clock()
            completion_event = self.build_completion_event(event, result, started_at, completed_at)
            logger.info(
                "processing_completed request_id=%s status=%s",
                event.request_id, completion_event.status,
            )
        except Exception as exc:
            completed_at = self._clock()
            logger.error("processing_failed request_id=%s error=%s", event.request_id, exc)
            duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))
            completion_event = TeachingCompletionEvent(
                request_id=event.request_id,
                session_ctx=event.session_ctx,
                topic=event.topic,
                output_mode=event.output_mode,
                status="error",
                content=None,
                tokens_used=0,
                model="unknown",
                started_at=_isoformat_utc(started_at),
                completed_at=_isoformat_utc(completed_at),
                duration_ms=duration_ms,
                errors=[str(exc)],
            )

        if producer is not None:
            try:
                self._publisher(producer, completion_event)
            except Exception as exc:
                logger.error("publish_failed request_id=%s error=%s", event.request_id, exc)
            else:
                logger.info(
                    "publish_completed request_id=%s status=%s",
                    event.request_id, completion_event.status,
                )
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
