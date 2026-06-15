"""Streamlit AI Tutor — ChatGPT-style conversational frontend."""

from __future__ import annotations

import queue
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import requests
import streamlit as st

from project.schemas import AgentEvent, ConnectionLifecycleState, EventType, FrontendSession
from ui_frontend.config import UIConfig
from ui_frontend.router import route_event
from ui_frontend.socketio_client import start_socketio_client
from ui_frontend.state import (
    create_initial_session,
    mark_connected,
    mark_connecting,
    mark_disconnected,
    mark_failed,
    mark_reconnecting,
)

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _ensure_frontend_session() -> FrontendSession:
    if "frontend_session" not in st.session_state:
        st.session_state.frontend_session = create_initial_session(
            session_id=str(uuid4())
        )
    return st.session_state.frontend_session


def _store_session(session: FrontendSession) -> None:
    st.session_state.frontend_session = session


def _ensure_chat_history() -> list[dict[str, Any]]:
    """Return chat history list, initialising it on first access."""
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    return st.session_state.chat_messages  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Event / state-change callbacks  (called from Streamlit script thread only)
# ---------------------------------------------------------------------------

def _on_event(event: AgentEvent) -> None:
    session = _ensure_frontend_session()
    updated = route_event(session, event)
    _store_session(updated)

    history = _ensure_chat_history()
    event_type = event.event_type

    if event_type == EventType.TEACHING_TOKEN:
        # Locate in-progress slot by stream_id to prevent duplicate bubbles.
        stream_id = updated.chat_state.stream_id
        in_progress_idx = next(
            (i for i, m in enumerate(history)
             if m["role"] == "assistant"
             and not m.get("complete")
             and m.get("stream_id") == stream_id),
            None,
        )
        if in_progress_idx is not None:
            history[in_progress_idx]["content"] = updated.chat_state.rendered_text
            if updated.chat_state.is_complete:
                history[in_progress_idx]["complete"] = True
        elif history and history[-1]["role"] == "assistant" and not history[-1].get("complete"):
            # Fallback: no stream_id match yet — update last in-progress slot.
            history[-1]["content"] = updated.chat_state.rendered_text
            history[-1]["stream_id"] = stream_id
            if updated.chat_state.is_complete:
                history[-1]["complete"] = True
        else:
            history.append({
                "role": "assistant",
                "content": updated.chat_state.rendered_text,
                "stream_id": stream_id,
                "complete": updated.chat_state.is_complete,
            })

    elif event_type == EventType.TEACHING_COMPLETE:
        # Finalise the last assistant message.
        if history and history[-1]["role"] == "assistant":
            history[-1]["content"] = updated.chat_state.rendered_text
            history[-1]["complete"] = True

    elif event_type == EventType.PLANNER_STATUS:
        # Clarification / status messages arrive as assistant info bubbles.
        msg = updated.planner_status.message
        if msg:
            # Avoid duplicate planner messages for the same text.
            if not (history and history[-1]["role"] == "assistant"
                    and history[-1].get("info") and history[-1]["content"] == msg):
                history.append({"role": "assistant", "content": msg, "info": True, "complete": True})


def _on_connection_state_change(
    state: ConnectionLifecycleState,
    error: str | None = None,
) -> None:
    session = _ensure_frontend_session()
    if state == ConnectionLifecycleState.CONNECTING:
        _store_session(mark_connecting(session))
    elif state == ConnectionLifecycleState.CONNECTED:
        _store_session(mark_connected(session))
    elif state == ConnectionLifecycleState.RECONNECTING:
        _store_session(mark_reconnecting(session, last_error=error))
    elif state == ConnectionLifecycleState.DISCONNECTED:
        _store_session(mark_disconnected(session))
    elif state == ConnectionLifecycleState.FAILED:
        _store_session(mark_failed(session, error or "connection failed"))


# ---------------------------------------------------------------------------
# Queue drain  (called from Streamlit script thread only)
# ---------------------------------------------------------------------------

def _drain_event_queue() -> bool:
    """Drain all pending items from the event queue into session state.

    Must only be called from the Streamlit script thread.
    Returns True if at least one item was processed.
    """
    eq: queue.Queue | None = st.session_state.get("event_queue")
    if eq is None:
        return False
    processed = False
    while True:
        try:
            item = eq.get_nowait()
        except queue.Empty:
            break
        kind = item[0]
        if kind == "connected":
            _, sid = item
            st.session_state.socketio_sid = sid
            _on_connection_state_change(ConnectionLifecycleState.CONNECTED)
        elif kind == "state":
            _, state, error = item
            _on_connection_state_change(state, error)
        elif kind == "event":
            _, event = item
            _on_event(event)
        processed = True
    return processed


@st.fragment(run_every="1s")
def _event_poller() -> None:
    """Heartbeat: drain queue every second, trigger full rerun on new data."""
    if _drain_event_queue():
        st.rerun()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _render_status_panel(cfg: UIConfig, session: FrontendSession) -> None:
    conn = session.connection_state
    state_val = conn.state.value

    state_icons = {
        "connected": "🟢",
        "connecting": "🟡",
        "reconnecting": "🟡",
        "disconnected": "🔴",
        "failed": "🔴",
    }
    icon = state_icons.get(state_val, "⚪")

    st.sidebar.subheader("Connection")
    st.sidebar.write(f"{icon} {state_val.capitalize()}")
    if conn.retry_count:
        st.sidebar.caption(f"Retry attempts: {conn.retry_count}")
    if conn.last_error:
        st.sidebar.warning(conn.last_error)

    st.sidebar.divider()
    st.sidebar.caption(f"Server: `{cfg.websocket_url}`")

    if session.planner_status.message:
        st.sidebar.divider()
        st.sidebar.subheader("Planner")
        st.sidebar.write(f"**Stage:** {session.planner_status.stage or '—'}")
        st.sidebar.write(session.planner_status.message)
        if session.planner_status.progress_percent is not None:
            st.sidebar.progress(session.planner_status.progress_percent / 100.0)

    if session.diagnostics:
        with st.sidebar.expander(f"Diagnostics ({len(session.diagnostics)})"):
            for d in session.diagnostics[-10:]:
                st.write(f"[{d.severity.value.upper()}] {d.reason}")


# ---------------------------------------------------------------------------
# Chat tab rendering
# ---------------------------------------------------------------------------

def _render_chat_tab(cfg: UIConfig, session: FrontendSession) -> None:
    history = _ensure_chat_history()
    sid: str | None = st.session_state.get("socketio_sid")
    conn_state = session.connection_state.state

    # ── Render history ────────────────────────────────────────────────────
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        with st.chat_message(role):
            if msg.get("info"):
                st.info(content)
            elif role == "assistant" and not msg.get("complete"):
                # In-progress stream: render with a blinking cursor feel.
                st.write(content + " ▌")
            else:
                st.write(content)

    # ── Status hints below the history ───────────────────────────────────
    if conn_state in (ConnectionLifecycleState.RECONNECTING,):
        st.warning("Reconnecting to server…")
    elif conn_state == ConnectionLifecycleState.FAILED:
        st.error("Connection failed. Refresh the page to retry.")

    # ── Input bar ────────────────────────────────────────────────────────
    connected = conn_state == ConnectionLifecycleState.CONNECTED and sid is not None
    placeholder = "Ask your tutor…" if connected else "Connecting to server…"

    if prompt := st.chat_input(placeholder, disabled=not connected):
        # 1. Add user message to history immediately.
        history.append({"role": "user", "content": prompt, "complete": True})
        # 2. Reserve an in-progress assistant slot (stream_id filled on first token).
        history.append({"role": "assistant", "content": "", "complete": False, "stream_id": None})
        # 3. POST to backend.
        try:
            resp = requests.post(
                f"{cfg.backend_url}/api/chat/request",
                data={"user_prompt": prompt, "sid": sid, "user_level": []},
                timeout=10,
            )
            if resp.status_code != 200:
                history[-1]["content"] = f"⚠️ Request failed ({resp.status_code}): {resp.text}"
                history[-1]["complete"] = True
        except requests.RequestException as exc:
            history[-1]["content"] = f"⚠️ Could not reach the server: {exc}"
            history[-1]["complete"] = True
        st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="AI Tutor", layout="wide", page_icon="🎓")
    st.title("🎓 AI Tutor")

    try:
        cfg = UIConfig.from_env()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    session = _ensure_frontend_session()

    # ── One-time Socket.IO startup per Streamlit session ─────────────────
    if "event_queue" not in st.session_state:
        st.session_state.event_queue = queue.Queue()
    if "socketio_client" not in st.session_state:
        st.session_state.socketio_client = start_socketio_client(
            cfg.websocket_url,
            st.session_state.event_queue,
        )

    # ── Sidebar ───────────────────────────────────────────────────────────
    _render_status_panel(cfg, session)

    # ── Tabs ──────────────────────────────────────────────────────────────
    chat_tab, quiz_tab, evaluation_tab = st.tabs(["💬 Chat", "📝 Quiz", "📊 Evaluation"])

    with chat_tab:
        _render_chat_tab(cfg, session)

    with quiz_tab:
        st.info("Quiz events will appear here.")

    with evaluation_tab:
        st.info("Evaluation results will appear here.")

    # ── Background event poller (must be last: st.rerun() aborts the script) ──
    _event_poller()


if __name__ == "__main__":
    main()
