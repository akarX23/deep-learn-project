from __future__ import annotations

from backend_service.app.utils import default_rag_test_event
from project.schemas import RAGRequestEvent, UserRequest


def test_default_rag_test_event_returns_rag_request_event() -> None:
    result = default_rag_test_event()
    assert isinstance(result, RAGRequestEvent)


def test_default_rag_test_event_request_id_starts_with_test_prefix() -> None:
    result = default_rag_test_event()
    assert result.request_id.startswith("test-")


def test_default_rag_test_event_request_id_unique_across_calls() -> None:
    first = default_rag_test_event()
    second = default_rag_test_event()
    assert first.request_id != second.request_id


def test_default_rag_test_event_required_fields_are_truthy() -> None:
    result = default_rag_test_event()
    assert result.user_request
    assert result.file_paths
    assert result.session_ctx


def test_user_request_required_fields() -> None:
    req = UserRequest(
        user_prompt="Explain gradient descent",
        user_level=["beginner"],
        file_data=None,
        sid="abc-123",
    )
    assert req.user_prompt == "Explain gradient descent"
    assert req.user_level == ["beginner"]
    assert req.sid == "abc-123"


def test_user_request_file_data_accepts_any_type() -> None:
    req = UserRequest(
        user_prompt="q",
        user_level=["advanced"],
        file_data={"name": "notes.pdf", "size": 1024},
        sid="sid-x",
    )
    assert req.file_data == {"name": "notes.pdf", "size": 1024}
