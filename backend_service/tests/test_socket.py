from __future__ import annotations

import asyncio

from backend_service.app import socket as socket_module
from backend_service.app.connection_manager import ConnectionManager
from project.events import WebSocketEvents


def test_connect_registers_session(monkeypatch):
    manager = ConnectionManager()
    monkeypatch.setattr(socket_module, "connection_manager", manager)

    asyncio.run(socket_module.connect("sid-1", {}, None))

    assert manager.get("sid-1") == "sid-1"


def test_emit_event_routes_to_session(monkeypatch):
    calls = []

    async def fake_emit(event, payload, to=None):
        calls.append((event, payload, to))

    monkeypatch.setattr(socket_module.sio, "emit", fake_emit)

    asyncio.run(
        socket_module.emit_event(
            WebSocketEvents.STREAM_TOKENS, {"token": "hi"}, "sid-1"
        )
    )

    assert calls == [("stream-tokens", {"token": "hi"}, "sid-1")]


def test_emit_event_accepts_plain_string_event(monkeypatch):
    calls = []

    async def fake_emit(event, payload, to=None):
        calls.append((event, payload, to))

    monkeypatch.setattr(socket_module.sio, "emit", fake_emit)

    asyncio.run(socket_module.emit_event("custom-event", {"x": 1}, "sid-2"))

    assert calls == [("custom-event", {"x": 1}, "sid-2")]


def test_stream_tokens_constant_value():
    assert WebSocketEvents.STREAM_TOKENS.value == "stream-tokens"
