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
    QuizState,
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
