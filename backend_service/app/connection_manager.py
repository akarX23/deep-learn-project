"""Minimal in-memory connection manager for WebSocket sessions.

Maps a ``session_id`` (which IS the Socket.IO-generated ``sid``) to its
connection handle so Kafka-driven results can be routed to the right session.
Sessions are independent even when a single user owns several of them.

Intentionally simple: only ``get`` and ``set``. Lifecycle concerns (disconnect
cleanup, thread/async safety, back-pressure) are deferred.
"""

from __future__ import annotations

from typing import Any


class ConnectionManager:
    """Track active WebSocket sessions keyed by ``session_id``."""

    def __init__(self) -> None:
        self._connections: dict[str, Any] = {}

    def set(self, session_id: str, connection: Any) -> None:
        """Register (or overwrite) the connection for a session."""
        self._connections[session_id] = connection

    def get(self, session_id: str) -> Any | None:
        """Return the connection for a session, or ``None`` if absent."""
        return self._connections.get(session_id)
    
    def remove(self, session_id: str) -> None:
        """Remove the connection for a session."""
        if session_id in self._connections:
            del self._connections[session_id]

# TODO: Add thread/async safety if accessed from multiple loops.
