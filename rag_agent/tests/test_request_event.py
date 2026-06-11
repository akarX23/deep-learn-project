from __future__ import annotations

import pytest

from project.schemas import RAGRequestEvent


def test_rag_request_event_requires_non_empty_fields() -> None:
    with pytest.raises(ValueError):
        RAGRequestEvent.model_validate(
            {
                "request_id": "req-1",
                "session_ctx": {},
                "user_request": "   ",
                "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
            }
        )


def test_rag_request_event_accepts_valid_payload() -> None:
    event = RAGRequestEvent.model_validate(
        {
            "request_id": "req-1",
            "session_ctx": {"session_id": "s-1"},
            "user_request": "Summarize the chapter",
            "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
        }
    )

    assert event.request_id == "req-1"
    assert event.file_paths == ["rag_agent/tests/inputs/sample.pdf"]