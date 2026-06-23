"""Socket.IO server, lightweight listeners, and the emit entry point.

This module owns the Socket.IO ``AsyncServer`` and the shared
:class:`ConnectionManager`. It also runs the backend Kafka consumer, which
forwards ``clarify-user-level`` and ``stream-tokens`` events to the originating
Socket.IO session.

Routing is keyed solely by ``session_id`` (which IS the Socket.IO ``sid``).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import socketio
from kafka import KafkaConsumer

from backend_service.app.config import KafkaSettings
from backend_service.app.connection_manager import ConnectionManager
from project.events import (
    ClarifyUserLevelEventBody,
    StreamProgressUpdateEventBody,
    StreamTokensEventBody,
    WebSocketEvents,
)
from project.schemas import WorkflowCompleteEventBody
from project.topics import (
    BackendStreamTopics,
    PlannerAgentTopics,
    get_backend_consumer_topic_names,
)

logger = logging.getLogger(__name__)

CONSUMER_GROUP_ID = "backend-service-consumer"

# Socket.IO server mounted onto the FastAPI app in main.py.
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=[])
socket_asgi_app = socketio.ASGIApp(sio)

# Shared connection manager keyed by session_id (== sid).
connection_manager = ConnectionManager()


@sio.event
async def connect(sid: str, environ: dict, auth: Any = None) -> None:
    """Register a new session keyed by its sid.

    TODO: Authenticate/authorize the connection before registering.
    """
    connection_manager.set(sid, sid)


@sio.event
async def disconnect(sid: str) -> None:
    """Handle a session disconnect.

    Remove the session from the connection manager and release resources.
    """
    connection_manager.remove(sid)


async def emit_event(
    event: WebSocketEvents | str, payload: Any, session_id: str
) -> None:
    """Emit ``event`` with ``payload`` to the connection for ``session_id``.

    TODO: Handle a missing/unknown session_id explicitly.
    TODO: Handle concurrent-emit ordering / back-pressure.
    """
    event_name = event.value if isinstance(event, WebSocketEvents) else event
    await sio.emit(event_name, payload, to=session_id)


async def stream_tokens(body: StreamTokensEventBody, session_id: str) -> None:
    """Emit a ``stream-tokens`` event to a session using the typed schema.

    TODO: Implement the token streaming flow.
    """
    await emit_event(WebSocketEvents.STREAM_TOKENS_SKT, body.model_dump(), session_id)


def _route_message(topic: str, payload: dict[str, Any]) -> tuple[WebSocketEvents, str]:
    """Validate a consumed payload and return the socket event + target sid."""

    if topic == PlannerAgentTopics.CLARIFY_USER_LEVEL.value:
        event = ClarifyUserLevelEventBody.model_validate(payload)
        return WebSocketEvents.CLARIFY_USER_LEVEL_SKT, event.sid

    if topic == BackendStreamTopics.STREAM_PROGRESS_UPDATE.value:
        event = StreamProgressUpdateEventBody.model_validate(payload)
        return WebSocketEvents.STREAM_PROGRESS_UPDATE_SKT, event.sid
    
    if topic == PlannerAgentTopics.WORKFLOW_COMPLETE.value:
        event = WorkflowCompleteEventBody.model_validate(payload)
        return WebSocketEvents.WORKFLOW_COMPLETE_SKT, event.sid

    body = StreamTokensEventBody.model_validate(payload)
    return WebSocketEvents.STREAM_TOKENS_SKT, body.sid


async def run_consumer(settings: KafkaSettings) -> None:
    """Poll backend topics and forward each payload to its Socket.IO session.

    Runs as a background asyncio task started during FastAPI lifespan startup.
    Errors are logged and the loop continues so a single bad message cannot
    stop event forwarding.

    TODO: Add graceful shutdown / consumer.close() on cancellation.
    """
    topics = get_backend_consumer_topic_names()
    consumer = KafkaConsumer(
        *topics,
        **settings.consumer_kwargs(CONSUMER_GROUP_ID),
        value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
    )
    logger.info("Backend consumer subscribed to topics: %s", topics)

    loop = asyncio.get_running_loop()
    while True:
        # poll() is blocking; run it off the event loop.
        records = await loop.run_in_executor(
            None, lambda: consumer.poll(timeout_ms=1000)
        )
        for messages in records.values():
            for message in messages:
                try:
                    event, sid = _route_message(message.topic, message.value)
                    await emit_event(event, message.value, sid)
                    logger.debug("Forwarded %s to session %s", event.value, sid)
                except Exception:  # noqa: BLE001 - keep consumer alive
                    logger.exception(
                        "Failed to forward message from topic %s", message.topic
                    )
