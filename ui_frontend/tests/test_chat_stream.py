from __future__ import annotations

from project.schemas import TeachingCompletePayload, TeachingTokenPayload
from ui_frontend.state import (
    apply_teaching_complete,
    apply_teaching_token,
    create_initial_session,
)


def test_teaching_token_order_and_duplicate_handling() -> None:
    session = create_initial_session(session_id="sess-us1")

    s1 = apply_teaching_token(
        session,
        TeachingTokenPayload(
            stream_id="stream-1",
            sequence=0,
            token="Hello",
            is_final=False,
        ),
    )
    s2 = apply_teaching_token(
        s1,
        TeachingTokenPayload(
            stream_id="stream-1",
            sequence=1,
            token=" world",
            is_final=False,
        ),
    )

    # Duplicate sequence must be ignored.
    s3 = apply_teaching_token(
        s2,
        TeachingTokenPayload(
            stream_id="stream-1",
            sequence=1,
            token=" duplicate",
            is_final=False,
        ),
    )

    assert s2.chat_state.rendered_text == "Hello world"
    assert s2.chat_state.last_sequence == 1
    assert s3.chat_state.rendered_text == "Hello world"
    assert s3.chat_state.last_sequence == 1


def test_teaching_complete_marks_stream_done() -> None:
    session = create_initial_session(session_id="sess-us1")
    partial = apply_teaching_token(
        session,
        TeachingTokenPayload(
            stream_id="stream-2",
            sequence=0,
            token="Partial",
            is_final=False,
        ),
    )

    completed = apply_teaching_complete(
        partial,
        TeachingCompletePayload(
            stream_id="stream-2",
            final_text="Partial answer finalized",
            tokens_used=4,
        ),
    )

    assert completed.chat_state.is_complete is True
    assert completed.chat_state.stream_id == "stream-2"
    assert completed.chat_state.rendered_text == "Partial answer finalized"
