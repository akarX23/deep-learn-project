from __future__ import annotations

from backend_service.app.connection_manager import ConnectionManager


def test_set_then_get_returns_connection():
    manager = ConnectionManager()
    manager.set("sid-1", "conn-1")
    assert manager.get("sid-1") == "conn-1"


def test_get_unknown_session_returns_none():
    manager = ConnectionManager()
    assert manager.get("missing") is None


def test_sessions_are_independent():
    manager = ConnectionManager()
    manager.set("sid-1", "conn-1")
    manager.set("sid-2", "conn-2")
    assert manager.get("sid-1") == "conn-1"
    assert manager.get("sid-2") == "conn-2"


def test_set_overwrites_existing_session():
    manager = ConnectionManager()
    manager.set("sid-1", "conn-1")
    manager.set("sid-1", "conn-2")
    assert manager.get("sid-1") == "conn-2"
