from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

from project.schemas import RAGRequestEvent
from rag_agent.worker import process_request_event


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


def test_request_processor_has_typed_signature() -> None:
    hints = get_type_hints(process_request_event)

    assert "payload" in hints
    assert "producer" in hints
    assert "return" in hints


def test_request_processor_contains_todo_markers_for_deferred_scope() -> None:
    process_source = inspect.getsource(process_request_event)

    assert "TODO" in process_source
