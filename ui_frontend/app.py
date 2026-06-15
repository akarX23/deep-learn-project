"""Streamlit application shell for the tutoring frontend."""

from __future__ import annotations

from logging import config
from uuid import uuid4

import streamlit as st
from datetime import datetime, timezone

from project.schemas import AgentEvent, ConnectionLifecycleState, FrontendSession
from ui_frontend.config import UIConfig
from ui_frontend.router import route_event
from ui_frontend.state import (
    create_initial_session,
    mark_connected,
    mark_connecting,
    mark_disconnected,
    mark_failed,
    mark_reconnecting,
)
from project.schemas import (
    AgentEvent,
    ConnectionLifecycleState,
    FrontendSession,
    EventType,
)

def _ensure_frontend_session() -> FrontendSession:
    if "frontend_session" not in st.session_state:
        st.session_state.frontend_session = create_initial_session(
            session_id=str(uuid4())
        )
    return st.session_state.frontend_session


def _store_session(session: FrontendSession) -> None:
    st.session_state.frontend_session = session


def _on_event(event: AgentEvent) -> None:
    session = _ensure_frontend_session()
    _store_session(route_event(session, event))


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


def _render_status_panel(config: UIConfig, session: FrontendSession) -> None:
    st.sidebar.subheader("Status")
    st.sidebar.write(f"Connection: {session.connection_state.state.value}")
    st.sidebar.write(f"Reconnect attempts: {session.connection_state.retry_count}")
    if session.connection_state.last_error:
        st.sidebar.warning(session.connection_state.last_error)
    st.sidebar.write(f"WebSocket URL: {config.websocket_url}")
    st.sidebar.write(
        f"Simulator enabled by env: {'yes' if config.simulator_enabled else 'no'}"
    )

    if session.planner_status.message:
        st.sidebar.divider()
        st.sidebar.caption("Planner")
        st.sidebar.write(f"Stage: {session.planner_status.stage or '-'}")
        st.sidebar.write(session.planner_status.message)
        if session.planner_status.progress_percent is not None:
            st.sidebar.progress(session.planner_status.progress_percent / 100.0)


def main() -> None:
    st.set_page_config(page_title="AI Tutor", page_icon="Tutor", layout="wide")
    st.title("Tutor A_Z")

    try:
        config = UIConfig.from_env()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    session = _ensure_frontend_session()
    # Demo button for local testing
    if st.button("Load Demo Response"):
        from uuid import uuid4

        demo_event = AgentEvent(
            event_id=str(uuid4()),
            session_id=session.session_id,
            source_agent="teaching-agent",
            event_type=EventType.TEACHING_TOKEN,
            timestamp=datetime.now(timezone.utc),
            payload={
                "stream_id": "demo-1",
                "token": "Machine Learning is a subset of AI.",
                "sequence": 1,
            },
    )
        _on_event(demo_event)
        st.rerun()
    _render_status_panel(config, session)

    chat_tab, quiz_tab, evaluation_tab = st.tabs(["Chat", "Quiz", "Evaluation"])

    with chat_tab:
        st.subheader("Chat")
        if session.chat_state.rendered_text:
            with st.chat_message("assistant"):
                st.write(session.chat_state.rendered_text)
            if session.chat_state.is_complete:
                st.caption("Response complete")
        else:
            st.info("Teaching stream will appear here.")

        st.caption("US1 callbacks are wired for websocket event + state updates.")

    with quiz_tab:
        st.subheader("Quiz")
        st.info("Quiz events will appear here.")

    with evaluation_tab:
        st.subheader("Evaluation")
        st.info("Evaluation results will appear here.")


if __name__ == "__main__":
    main()
