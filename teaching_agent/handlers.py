"""Inbound Kafka request handlers for the Teaching Agent."""

from __future__ import annotations

import logging
from collections.abc import Callable
import os

from project.schemas import (
    ProgressUpdatePage,
    StreamProgressUpdateEventBody,
    StreamTokensEventBody,
    TeachingCompletionEvent,
    TeachingRequestEvent,
)
from teaching_agent.agent import TeachingAgent
from teaching_agent.config import get_max_history_messages, get_session_ttl_seconds
from teaching_agent.kafka import (
    KafkaProducerProtocol,
    publish_stream_progress_update,
    publish_stream_token,
    publish_teaching_complete,
)
from teaching_agent.session_memory import ConversationStore

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
        progress_publisher: Callable[
            [KafkaProducerProtocol, StreamProgressUpdateEventBody], None
        ] = publish_stream_progress_update,
        store: ConversationStore | None = None,
    ) -> None:
        self._agent_factory = agent_factory
        self._publisher = publisher
        self._stream_publisher = stream_publisher
        self._progress_publisher = progress_publisher
        # One store per handler. The worker builds a single handler and reuses it
        # for every request, so this is the per-process session memory; tests get
        # isolation for free by constructing their own handler/store.
        self._store = store if store is not None else ConversationStore(
            max_messages=get_max_history_messages(),
            ttl_seconds=get_session_ttl_seconds(),
        )

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
            # Handle progress events emitted by StreamingFieldExtractor
            if field == "_progress":
                if producer is None:
                    return
                try:
                    self._progress_publisher(
                        producer,
                        StreamProgressUpdateEventBody(
                            sid=event.sid,
                            for_page=ProgressUpdatePage.CHAT,
                            update=token,  # token here is the progress message
                        ),
                    )
                except Exception as cb_exc:
                    logger.warning(
                        "progress_publish_failed request_id=%s error=%s",
                        event.request_id,
                        cb_exc,
                    )
                return

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

        # Multi-turn: an explicitly supplied chat_history (e.g. from a producer or
        # test) wins; otherwise use the history this agent maintains for the sid.
        # Bounds (size/TTL) are enforced inside the store. A non-empty history also
        # makes the agent skip its greeting/off-topic guardrail (it's a follow-up).
        history = (
            list(event.chat_history)
            if event.chat_history
            else self._store.get_history(event.sid)
        )
        if history:
            logger.info(
                "conversation_history_loaded request_id=%s sid=%s messages=%d",
                event.request_id, event.sid, len(history),
            )

        try:
            result, raw_markdown = agent.run(
                {
                    "topic": event.user_prompt,
                    "output_mode": event.user_level,
                    "context": event.rag_compiled,
                    "chat_history": history,
                },
                token_callback,
            )
            completion_event = self.build_completion_event(event, raw_markdown)
            # Persist this turn so the next request in the session sees it. Only
            # real teaching answers are stored (content is not None) — error and
            # guardrail/canned replies (content None) never become history, so a
            # first genuine question is still guardrail-checked.
            if result is not None and result.content is not None and raw_markdown:
                self._store.append_turn(event.sid, event.user_prompt, raw_markdown)
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
                    data={"done": True, "tokens_used": tokens_used, "model": os.getenv("TEACHING_MODEL")},
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
