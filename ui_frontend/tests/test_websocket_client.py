from __future__ import annotations

import asyncio

from project.schemas import ConnectionLifecycleState
from ui_frontend.websocket_client import WebSocketClient


class _StateRecorder:
    def __init__(self) -> None:
        self.states: list[tuple[ConnectionLifecycleState, str | None]] = []

    def __call__(
        self,
        state: ConnectionLifecycleState,
        error: str | None = None,
    ) -> None:
        self.states.append((state, error))


def test_reconnect_transitions_include_reconnecting_then_connected(
    monkeypatch,
) -> None:
    recorder = _StateRecorder()
    client = WebSocketClient(
        websocket_url="ws://example.local/ws/events",
        on_event=lambda _event: None,
        on_state_change=recorder,
    )

    attempts = {"count": 0}

    async def fake_connect() -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary outage")
        client.retry_count = 0
        recorder(ConnectionLifecycleState.CONNECTED, None)

    async def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(client, "connect", fake_connect)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    asyncio.run(client._handle_reconnect())

    assert attempts["count"] == 2
    assert recorder.states[0][0] == ConnectionLifecycleState.RECONNECTING
    assert recorder.states[-1][0] == ConnectionLifecycleState.CONNECTED
