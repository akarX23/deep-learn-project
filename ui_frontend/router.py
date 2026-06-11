"""Event router for websocket messages to state containers."""

from __future__ import annotations

import logging
from typing import Optional

from project.schemas import (
    AgentEvent,
    ChatStreamState,
    DiagnosticEvent,
    DiagnosticSeverity,
    EvaluationResultPayload,
    EvaluationState,
    FrontendSession,
    PlannerStatusPayload,
    PlannerStatusState,
    QuizEventPayload,
    QuizPhase,
    QuizState,
    SystemErrorPayload,
    TeachingCompletePayload,
    TeachingTokenPayload,
)

logger = logging.getLogger(__name__)

# Supported event types and their routing
TEACHING_EVENTS = {"teaching.token", "teaching.complete"}
PLANNER_EVENTS = {"planner.status"}
QUIZ_EVENTS = {"quiz.started", "quiz.question", "quiz.feedback", "quiz.completed"}
EVALUATION_EVENTS = {"evaluation.result"}
SYSTEM_EVENTS = {"system.error"}


def _add_diagnostic(
    session: FrontendSession,
    severity: DiagnosticSeverity,
    event_type: str,
    message: str,
) -> FrontendSession:
    """Add a diagnostic entry to the session."""
    diag = DiagnosticEvent(
        event_type=event_type,
        severity=severity,
        message=message,
    )
    updated_diagnostics = list(session.diagnostics) + [diag]
    return session.model_copy(update={"diagnostics": updated_diagnostics})


def _handle_teaching_token(
    session: FrontendSession,
    event: AgentEvent,
) -> FrontendSession:
    """Route teaching.token event to chat state."""
    try:
        payload = TeachingTokenPayload(**event.payload)
    except Exception as exc:
        logger.error(f"Invalid teaching.token payload: {exc}")
        return _add_diagnostic(
            session,
            DiagnosticSeverity.ERROR,
            "teaching.token",
            f"Invalid payload: {exc}",
        )

    chat_state = session.chat_state
    stream_id = payload.stream_id

    # Check for duplicate sequence
    if (
        chat_state.stream_id == stream_id
        and payload.sequence <= chat_state.last_sequence
    ):
        logger.debug(
            f"Ignoring duplicate/out-of-order token: seq={payload.sequence} "
            f"(last={chat_state.last_sequence})"
        )
        return session

    # Append token and update sequence
    updated_text = chat_state.rendered_text + payload.token
    updated_chat_state = chat_state.model_copy(
        update={
            "stream_id": stream_id,
            "rendered_text": updated_text,
            "last_sequence": payload.sequence,
        }
    )

    return session.model_copy(update={"chat_state": updated_chat_state})


def _handle_teaching_complete(
    session: FrontendSession,
    event: AgentEvent,
) -> FrontendSession:
    """Route teaching.complete event to chat state."""
    try:
        payload = TeachingCompletePayload(**event.payload)
    except Exception as exc:
        logger.error(f"Invalid teaching.complete payload: {exc}")
        return _add_diagnostic(
            session,
            DiagnosticSeverity.ERROR,
            "teaching.complete",
            f"Invalid payload: {exc}",
        )

    # Mark stream as complete
    updated_chat_state = session.chat_state.model_copy(
        update={"is_complete": True}
    )
    return session.model_copy(update={"chat_state": updated_chat_state})


def _handle_planner_status(
    session: FrontendSession,
    event: AgentEvent,
) -> FrontendSession:
    """Route planner.status event to status panel."""
    try:
        payload = PlannerStatusPayload(**event.payload)
    except Exception as exc:
        logger.error(f"Invalid planner.status payload: {exc}")
        return _add_diagnostic(
            session,
            DiagnosticSeverity.ERROR,
            "planner.status",
            f"Invalid payload: {exc}",
        )

    updated_status = session.planner_status.model_copy(
        update={
            "stage": payload.stage,
            "message": payload.message,
            "progress_percent": payload.progress_percent,
            "updated_at": event.timestamp,
        }
    )
    return session.model_copy(update={"planner_status": updated_status})


def _handle_quiz_event(
    session: FrontendSession,
    event: AgentEvent,
) -> FrontendSession:
    """Route quiz.* events to quiz state."""
    try:
        payload = QuizEventPayload(**event.payload)
    except Exception as exc:
        logger.error(f"Invalid quiz event payload: {exc}")
        return _add_diagnostic(
            session,
            DiagnosticSeverity.ERROR,
            event.event_type,
            f"Invalid payload: {exc}",
        )

    # Map event_type to phase
    event_to_phase = {
        "quiz.started": QuizPhase.STARTED,
        "quiz.question": QuizPhase.QUESTION,
        "quiz.feedback": QuizPhase.FEEDBACK,
        "quiz.completed": QuizPhase.COMPLETED,
    }
    phase = event_to_phase.get(event.event_type, QuizPhase.IDLE)

    updated_quiz_state = session.quiz_state.model_copy(
        update={
            "quiz_id": payload.quiz_id,
            "phase": phase,
            "current_question": payload.question_text,
            "choices": payload.choices or [],
            "feedback": payload.feedback,
            "score": payload.score,
        }
    )
    return session.model_copy(update={"quiz_state": updated_quiz_state})


def _handle_evaluation_result(
    session: FrontendSession,
    event: AgentEvent,
) -> FrontendSession:
    """Route evaluation.result event to evaluation state."""
    try:
        payload = EvaluationResultPayload(**event.payload)
    except Exception as exc:
        logger.error(f"Invalid evaluation.result payload: {exc}")
        return _add_diagnostic(
            session,
            DiagnosticSeverity.ERROR,
            "evaluation.result",
            f"Invalid payload: {exc}",
        )

    updated_eval_state = session.evaluation_state.model_copy(
        update={
            "latest_summary": payload.summary,
            "strengths": payload.strengths or [],
            "gaps": payload.gaps or [],
            "recommendations": payload.recommendations or [],
            "history_count": session.evaluation_state.history_count + 1,
        }
    )
    return session.model_copy(update={"evaluation_state": updated_eval_state})


def _handle_system_error(
    session: FrontendSession,
    event: AgentEvent,
) -> FrontendSession:
    """Route system.error event to diagnostics."""
    try:
        payload = SystemErrorPayload(**event.payload)
    except Exception as exc:
        logger.error(f"Invalid system.error payload: {exc}")
        return _add_diagnostic(
            session,
            DiagnosticSeverity.ERROR,
            "system.error",
            f"Invalid payload: {exc}",
        )

    return _add_diagnostic(
        session,
        DiagnosticSeverity.WARNING,
        "system.error",
        f"[{payload.code}] {payload.message}",
    )


def route_event(session: FrontendSession, event: AgentEvent) -> FrontendSession:
    """
    Validate and route an incoming event to the appropriate state container.

    Args:
        session: Current frontend session state
        event: Incoming AgentEvent from websocket

    Returns:
        Updated session with event applied or diagnostic collected
    """
    event_type = event.event_type

    try:
        if event_type in TEACHING_EVENTS:
            if event_type == "teaching.token":
                return _handle_teaching_token(session, event)
            elif event_type == "teaching.complete":
                return _handle_teaching_complete(session, event)

        elif event_type in PLANNER_EVENTS:
            return _handle_planner_status(session, event)

        elif event_type in QUIZ_EVENTS:
            return _handle_quiz_event(session, event)

        elif event_type in EVALUATION_EVENTS:
            return _handle_evaluation_result(session, event)

        elif event_type in SYSTEM_EVENTS:
            return _handle_system_error(session, event)

        else:
            logger.warning(f"Unknown event type: {event_type}")
            return _add_diagnostic(
                session,
                DiagnosticSeverity.WARNING,
                event_type,
                f"Unknown event type",
            )

    except Exception as exc:
        logger.error(f"Unhandled exception routing {event_type}: {exc}")
        return _add_diagnostic(
            session,
            DiagnosticSeverity.ERROR,
            event_type,
            f"Routing failed: {exc}",
        )
