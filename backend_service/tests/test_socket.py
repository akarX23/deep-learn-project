from __future__ import annotations

import asyncio

from backend_service.app import socket as socket_module
from backend_service.app.connection_manager import ConnectionManager
from project.events import (
    StreamProgressUpdateEventBody,
    StreamTokensEventBody,
    WebSocketEvents,
)


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


def test_stream_progress_update_constant_value():
    assert WebSocketEvents.STREAM_PROGRESS_UPDATE.value == "stream-progress-update"


def test_route_message_maps_progress_update_topic():
    event, sid = socket_module._route_message(
        WebSocketEvents.STREAM_PROGRESS_UPDATE.value,
        {"sid": "sid-9", "for_page": "quiz", "update": "Generating questions"},
    )

    assert event == WebSocketEvents.STREAM_PROGRESS_UPDATE_SKT
    assert sid == "sid-9"


def test_stream_tokens_event_body_required_fields():
    body = StreamTokensEventBody(
        from_service="rag-agent", sid="sid-1", data={"k": "v"}
    )
    assert body.from_service == "rag-agent"
    assert body.sid == "sid-1"
    assert body.data == {"k": "v"}


def test_stream_tokens_event_body_data_defaults_to_empty_dict():
    body = StreamTokensEventBody(from_service="teaching-agent", sid="sid-2")
    assert body.data == {}


def test_stream_progress_update_event_body_required_fields():
    body = StreamProgressUpdateEventBody(
        sid="sid-3", for_page="chat", update="Preparing response"
    )

    assert body.sid == "sid-3"
    assert body.for_page == "chat"
    assert body.update == "Preparing response"
