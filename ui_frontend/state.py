"""State helpers for frontend session and connection lifecycle management."""

from __future__ import annotations

from datetime import datetime, timezone

from project.schemas import (
    ChatStreamState,
    ConnectionLifecycleState,
    ConnectionState,
    EvaluationState,
    FrontendSession,
    PlannerStatusState,
    PlannerStatusPayload,
    QuizState,
    TeachingCompletePayload,
    TeachingTokenPayload,
)

_ALLOWED_TABS = {"chat", "quiz", "evaluation"}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _connection_state(
    state: ConnectionLifecycleState,
    retry_count: int = 0,
    last_error: str | None = None,
) -> ConnectionState:
    return ConnectionState(
        state=state,
        retry_count=retry_count,
        last_error=last_error,
        last_change_ts=_now_utc(),
    )


def create_initial_session(session_id: str, active_tab: str = "chat") -> FrontendSession:
    """Create a new frontend session with default state containers."""
    if active_tab not in _ALLOWED_TABS:
        raise ValueError(f"active_tab must be one of {_ALLOWED_TABS}")

    return FrontendSession(
        session_id=session_id,
        active_tab=active_tab,
        connection_state=_connection_state(ConnectionLifecycleState.CONNECTING),
        chat_state=ChatStreamState(),
        quiz_state=QuizState(),
        evaluation_state=EvaluationState(),
        planner_status=PlannerStatusState(updated_at=_now_utc()),
    )


def set_active_tab(session: FrontendSession, active_tab: str) -> FrontendSession:
    """Switch active tab while keeping all current state data."""
    if active_tab not in _ALLOWED_TABS:
        raise ValueError(f"active_tab must be one of {_ALLOWED_TABS}")
    return session.model_copy(update={"active_tab": active_tab})


def mark_connecting(session: FrontendSession) -> FrontendSession:
    """Move lifecycle to connecting without changing retry count."""
    return session.model_copy(
        update={
            "connection_state": _connection_state(
                ConnectionLifecycleState.CONNECTING,
                retry_count=session.connection_state.retry_count,
                last_error=None,
            )
        }
    )


def mark_connected(session: FrontendSession) -> FrontendSession:
    """Move lifecycle to connected and reset retry metadata."""
    return session.model_copy(
        update={
            "connection_state": _connection_state(
                ConnectionLifecycleState.CONNECTED,
                retry_count=0,
                last_error=None,
            )
        }
    )


def mark_reconnecting(
    session: FrontendSession,
    last_error: str | None = None,
) -> FrontendSession:
    """Move lifecycle to reconnecting and increment retry count."""
    return session.model_copy(
        update={
            "connection_state": _connection_state(
                ConnectionLifecycleState.RECONNECTING,
                retry_count=session.connection_state.retry_count + 1,
                last_error=last_error,
            )
        }
    )


def mark_disconnected(session: FrontendSession) -> FrontendSession:
    """Move lifecycle to disconnected while retaining retry metadata."""
    return session.model_copy(
        update={
            "connection_state": _connection_state(
                ConnectionLifecycleState.DISCONNECTED,
                retry_count=session.connection_state.retry_count,
                last_error=session.connection_state.last_error,
            )
        }
    )


def mark_failed(session: FrontendSession, error: str) -> FrontendSession:
    """Move lifecycle to failed and store the latest error."""
    return session.model_copy(
        update={
            "connection_state": _connection_state(
                ConnectionLifecycleState.FAILED,
                retry_count=session.connection_state.retry_count,
                last_error=error,
            )
        }
    )


def apply_teaching_token(
    session: FrontendSession,
    payload: TeachingTokenPayload,
) -> FrontendSession:
    """Append in-order token chunks to chat state and ignore duplicates."""
    chat_state = session.chat_state

    if chat_state.stream_id == payload.stream_id and payload.sequence <= chat_state.last_sequence:
        return session

    if chat_state.stream_id != payload.stream_id:
        chat_state = ChatStreamState(stream_id=payload.stream_id)

    updated_chat_state = chat_state.model_copy(
        update={
            "stream_id": payload.stream_id,
            "rendered_text": chat_state.rendered_text + payload.token,
            "last_sequence": payload.sequence,
            "is_complete": payload.is_final,
        }
    )
    return session.model_copy(update={"chat_state": updated_chat_state})


def apply_teaching_complete(
    session: FrontendSession,
    payload: TeachingCompletePayload,
) -> FrontendSession:
    """Finalize chat stream and optionally apply server-provided final text."""
    final_text = payload.final_text or session.chat_state.rendered_text
    updated_chat_state = session.chat_state.model_copy(
        update={
            "stream_id": payload.stream_id,
            "rendered_text": final_text,
            "is_complete": True,
        }
    )
    return session.model_copy(update={"chat_state": updated_chat_state})


def apply_planner_status(
    session: FrontendSession,
    payload: PlannerStatusPayload,
    updated_at: datetime | None = None,
) -> FrontendSession:
    """Update planner status panel fields for the latest planner event."""
    updated_status = session.planner_status.model_copy(
        update={
            "stage": payload.stage,
            "message": payload.message,
            "progress_percent": payload.progress_percent,
            "updated_at": updated_at or _now_utc(),
        }
    )
    return session.model_copy(update={"planner_status": updated_status})
