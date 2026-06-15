from __future__ import annotations

from backend_service.app.utils import default_rag_test_event
from project.schemas import PlannerRequestEvent, RAGRequestEvent, UserRequest


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
        sid="abc-123",
    )
    assert req.user_prompt == "Explain gradient descent"
    assert req.user_level == ["beginner"]
    assert req.sid == "abc-123"


def test_planner_request_event_required_fields() -> None:
    event = PlannerRequestEvent(
        user_prompt="Explain backprop",
        user_level=["beginner"],
        sid="sid-1",
        file_paths=["/abs/path/doc1.pdf", "/abs/path/doc2.txt"],
    )
    assert event.user_prompt == "Explain backprop"
    assert event.user_level == ["beginner"]
    assert event.sid == "sid-1"
    assert event.file_paths == ["/abs/path/doc1.pdf", "/abs/path/doc2.txt"]


def test_planner_request_event_defaults_empty_lists() -> None:
    event = PlannerRequestEvent(user_prompt="q", sid="sid-2")
    assert event.user_level == []
    assert event.file_paths == []
