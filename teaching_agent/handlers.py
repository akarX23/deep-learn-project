"""Inbound Kafka request handlers for the Teaching Agent."""

from __future__ import annotations

import logging
from collections.abc import Callable

from project.schemas import (
    StreamTokensEventBody,
    TeachingCompletionEvent,
    TeachingRequestEvent,
)
from teaching_agent.agent import TeachingAgent
from teaching_agent.kafka import KafkaProducerProtocol, publish_stream_token, publish_teaching_complete

logger = logging.getLogger(__name__)


class TeachingRequestEventHandler:
    """Ingest Kafka request events and dispatch them to the Teaching Agent pipeline."""

    def __init__(
        self,
        agent_factory: Callable[[], TeachingAgent] = TeachingAgent,
        publisher: Callable[
            [KafkaProducerProtocol, TeachingCompletionEvent], None
        ] = publish_teaching_complete,
        stream_publisher: Callable[
            [KafkaProducerProtocol, StreamTokensEventBody], None
        ] = publish_stream_token,
    ) -> None:
        self._agent_factory = agent_factory
        self._publisher = publisher
        self._stream_publisher = stream_publisher

    def parse_event(self, payload: dict[str, object]) -> TeachingRequestEvent:
        """Parse inbound payload into request event schema."""
        return TeachingRequestEvent.model_validate(payload)

    def build_completion_event(
        self,
        event: TeachingRequestEvent,
        raw_markdown: str,
    ) -> TeachingCompletionEvent:
        """Map raw markdown response into the outbound Kafka completion contract."""
        return TeachingCompletionEvent(
            request_id=event.request_id,
            sid=event.sid,
            user_level=event.user_level,
            content=raw_markdown,
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

        agent = self._agent_factory()
        logger.info(
            "processing_started request_id=%s user_prompt=%s user_level=%s",
            event.request_id, event.user_prompt, event.user_level,
        )

        def token_callback(field: str, token: str) -> None:
            if producer is None:
                return
            try:
                self._stream_publisher(producer, StreamTokensEventBody(
                    from_service="teaching-agent",
                    sid=event.sid,
                    data={"field": field, "token": token},
                ))
            except Exception as cb_exc:
                logger.warning(
                    "stream_publish_failed request_id=%s error=%s", event.request_id, cb_exc,
                )

        try:
            result, raw_markdown = agent.run(
                {
                    "topic": event.user_prompt,
                    "output_mode": event.user_level,
                    "context": event.rag_compiled,
                },
                token_callback,
            )
            completion_event = self.build_completion_event(event, raw_markdown)
            logger.info("processing_completed request_id=%s", event.request_id)
        except Exception as exc:
            logger.error("processing_failed request_id=%s error=%s", event.request_id, exc)
            result = None
            completion_event = TeachingCompletionEvent(
                request_id=event.request_id,
                sid=event.sid,
                user_level=event.user_level,
                content="",
            )

        # Publish stream-complete sentinel then flush (always, before completion event)
        if producer is not None:
            tokens_used = result.metadata.tokens_used if result is not None else 0
            try:
                self._stream_publisher(producer, StreamTokensEventBody(
                    from_service="teaching-agent",
                    sid=event.sid,
                    data={"done": True, "tokens_used": tokens_used},
                ))
                producer.flush()
            except Exception as exc:
                logger.error(
                    "stream_sentinel_failed request_id=%s error=%s", event.request_id, exc,
                )

        if producer is not None:
            try:
                self._publisher(producer, completion_event)
            except Exception as exc:
                logger.error("publish_failed request_id=%s error=%s", event.request_id, exc)
            else:
                logger.info("publish_completed request_id=%s", event.request_id)
        return completion_event


def _extract_request_id(payload: dict[str, object]) -> str:
    """Extract request_id from raw inbound payload."""
    raw_request_id = payload.get("request_id")
    if isinstance(raw_request_id, str) and raw_request_id.strip():
        return raw_request_id
    return "unknown"
