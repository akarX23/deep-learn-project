"""Shared WebSocket event-name constants.

This module is the single source of truth for WebSocket event names exchanged
between the backend and the frontend. Payload shapes live in
``project/schemas.py`` and are re-exported here so both frontend and backend can
import names and bodies from one place. Keeping this module free of backend-only
dependencies lets the frontend import the same names.
"""

from __future__ import annotations

from enum import Enum

from project.schemas import (
    ClarifyUserLevelEvent,
    StreamProgressUpdateEventBody,
    StreamTokensEventBody,
)

__all__ = [
    "WebSocketEvents",
    "StreamTokensEventBody",
    "StreamProgressUpdateEventBody",
    "ClarifyUserLevelEvent",
]


class WebSocketEvents(str, Enum):
    """WebSocket event names shared by the frontend and backend."""

    # Kafka topic names consumed by the backend.
    STREAM_TOKENS = "stream-tokens"
    STREAM_PROGRESS_UPDATE = "stream-progress-update"

    # Socket.IO event names emitted to the frontend.
    CLARIFY_USER_LEVEL_SKT = "clarify-user-level-skt"
    STREAM_TOKENS_SKT = "stream-tokens-skt"
    STREAM_PROGRESS_UPDATE_SKT = "stream-progress-update-skt"
