"""Shared WebSocket event-name constants.

This module is the single source of truth for WebSocket event names exchanged
between the backend and the frontend. It intentionally contains event *names*
only — payload shapes live in ``project/schemas.py``. Keeping this module free
of backend-only dependencies lets the frontend import the same names.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class WebSocketEvents(str, Enum):
    """WebSocket event names shared by the frontend and backend."""

    STREAM_TOKENS = "stream-tokens"


class StreamTokensEventBody(BaseModel):
    """Payload schema for the ``stream-tokens`` WebSocket event."""

    from_service: str
    content: str
    metadata: dict[str, Any] = {}
