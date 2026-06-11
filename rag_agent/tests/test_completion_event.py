from __future__ import annotations

import pytest

from project.schemas import RAGCompletionEvent


def test_rag_completion_event_accepts_failed_payload_with_empty_material() -> None:
    event = RAGCompletionEvent.model_validate(
        {
            "request_id": "req-1",
            "session_ctx": {"session_id": "s-1"},
            "user_prompt": "Summarize the uploaded chapter",
            "compiled_material": "",
            "status": "failed",
            "errors": ["PDF missing"],
            "total_pages_processed": 0,
            "total_pages_included": 0,
            "started_at": "2026-06-11T16:00:00Z",
            "completed_at": "2026-06-11T16:00:01Z",
            "duration_ms": 1000,
        }
    )

    assert event.status == "failed"
    assert event.compiled_material == ""


def test_rag_completion_event_rejects_unknown_status() -> None:
    with pytest.raises(ValueError):
        RAGCompletionEvent.model_validate(
            {
                "request_id": "req-2",
                "session_ctx": {"session_id": "s-2"},
                "user_prompt": "Summarize the uploaded chapter",
                "compiled_material": "# Output",
                "status": "done",
                "errors": [],
                "total_pages_processed": 1,
                "total_pages_included": 1,
                "started_at": "2026-06-11T16:00:00Z",
                "completed_at": "2026-06-11T16:00:01Z",
                "duration_ms": 1000,
            }
        )