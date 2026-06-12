from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

from project.schemas import RAGRequestEvent
from rag_agent.handlers import RAGRequestEventHandler


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


def test_request_handler_process_request_has_typed_signature() -> None:
    hints = get_type_hints(RAGRequestEventHandler.process_request)

    assert "payload" in hints
    assert "producer" in hints
    assert "return" in hints


def test_request_handler_contains_todo_markers_for_deferred_scope() -> None:
    parse_source = inspect.getsource(RAGRequestEventHandler.parse_event)
    process_source = inspect.getsource(RAGRequestEventHandler.process_request)

    assert "TODO" in parse_source
    assert "TODO" in process_source