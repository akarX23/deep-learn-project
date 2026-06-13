"""Socket.IO server, lightweight listeners, and the emit entry point.

This module owns the Socket.IO ``AsyncServer`` and the shared
:class:`ConnectionManager`. Listeners are intentionally lightweight; their full
behavior (and the ``stream-tokens`` emission flow) is implemented later.

Routing is keyed solely by ``session_id`` (which IS the Socket.IO ``sid``).
"""

from __future__ import annotations

from typing import Any

import socketio

from backend_service.app.connection_manager import ConnectionManager
from project.events import StreamTokensEventBody, WebSocketEvents

# Socket.IO server mounted onto the FastAPI app in main.py.
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_asgi_app = socketio.ASGIApp(sio, socketio_path="")

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
    await emit_event(WebSocketEvents.STREAM_TOKENS, body.model_dump(), session_id)
