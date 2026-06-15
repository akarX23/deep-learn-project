"""Inbound Kafka request handlers for the Teaching Agent."""

from __future__ import annotations

import logging
from collections.abc import Callable
# from datetime import datetime, timezone  # no longer needed: new TeachingCompletionEvent has no timing fields

from project.schemas import (
    # TeachingAgentOutput,  # no longer needed: result is passed through but not type-annotated in build_completion_event
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
        # clock: Callable[[], datetime] | None = None,  # removed: new schema has no timing fields
    ) -> None:
        self._agent_factory = agent_factory
        self._publisher = publisher
        # self._clock = clock or (lambda: datetime.now(timezone.utc))  # removed: no timing in new schema

    def parse_event(self, payload: dict[str, object]) -> TeachingRequestEvent:
        """Parse inbound payload into request event schema."""
        return TeachingRequestEvent.model_validate(payload)

    def build_completion_event(
        self,
        event: TeachingRequestEvent,
        result,
        # started_at: datetime,   # removed: new TeachingCompletionEvent has no timing fields
        # completed_at: datetime, # removed: new TeachingCompletionEvent has no timing fields
    ) -> TeachingCompletionEvent:
        """Map agent output into the outbound Kafka completion contract."""
        # Old mapping (pre-master-merge schema):
        # duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))
        # return TeachingCompletionEvent(
        #     request_id=event.request_id,
        #     session_ctx=event.session_ctx,
        #     topic=event.topic,
        #     output_mode=event.output_mode,
        #     status=result.status,
        #     content=result.content,
        #     tokens_used=result.metadata.tokens_used,
        #     model=result.metadata.model,
        #     started_at=_isoformat_utc(started_at),
        #     completed_at=_isoformat_utc(completed_at),
        #     duration_ms=duration_ms,
        # )
        content_str = result.content.model_dump_json() if result.content else ""
        return TeachingCompletionEvent(
            request_id=event.request_id,
            sid=event.sid,
            user_level=event.user_level,
            content=content_str,
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

        # started_at = self._clock()  # removed: no timing in new schema
        agent = self._agent_factory()
        logger.info(
            "processing_started request_id=%s user_prompt=%s user_level=%s",
            # Old fields: event.topic, event.output_mode
            event.request_id, event.user_prompt, event.user_level,
        )

        try:
            result = agent.run({
                # Old mapping (pre-master-merge schema):
                # "topic": event.topic,
                # "output_mode": event.output_mode,
                # "context": event.context,
                "topic": event.user_prompt,      # user_prompt → topic (core pipeline field)
                "output_mode": event.user_level,  # user_level  → output_mode (core pipeline field)
                "context": event.rag_compiled,    # rag_compiled → context (core pipeline field)
            })
            # completed_at = self._clock()  # removed: no timing in new schema
            completion_event = self.build_completion_event(event, result)
            # Old log included completion_event.status (field removed from new schema):
            # logger.info("processing_completed request_id=%s status=%s", event.request_id, completion_event.status)
            logger.info("processing_completed request_id=%s", event.request_id)
        except Exception as exc:
            # completed_at = self._clock()  # removed: no timing in new schema
            logger.error("processing_failed request_id=%s error=%s", event.request_id, exc)
            # duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))
            # Old error completion event (pre-master-merge schema):
            # completion_event = TeachingCompletionEvent(
            #     request_id=event.request_id,
            #     session_ctx=event.session_ctx,
            #     topic=event.topic,
            #     output_mode=event.output_mode,
            #     status="error",
            #     content=None,
            #     tokens_used=0,
            #     model="unknown",
            #     started_at=_isoformat_utc(started_at),
            #     completed_at=_isoformat_utc(completed_at),
            #     duration_ms=duration_ms,
            #     errors=[str(exc)],
            # )
            completion_event = TeachingCompletionEvent(
                request_id=event.request_id,
                sid=event.sid,
                user_level=event.user_level,
                content="",
            )

        if producer is not None:
            try:
                self._publisher(producer, completion_event)
            except Exception as exc:
                logger.error("publish_failed request_id=%s error=%s", event.request_id, exc)
            else:
                # Old log included completion_event.status (field removed from new schema):
                # logger.info("publish_completed request_id=%s status=%s", event.request_id, completion_event.status)
                logger.info("publish_completed request_id=%s", event.request_id)
        return completion_event


# def _isoformat_utc(value: datetime) -> str:
#     """Serialize datetimes consistently in UTC."""
#     return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
# Removed: new TeachingCompletionEvent has no timing fields (started_at, completed_at, duration_ms)


def _extract_request_id(payload: dict[str, object]) -> str:
    """Extract request_id from raw inbound payload."""
    raw_request_id = payload.get("request_id")
    if isinstance(raw_request_id, str) and raw_request_id.strip():
        return raw_request_id
    return "unknown"
