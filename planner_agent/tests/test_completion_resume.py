"""Tests for completion-event consumption and LangGraph Command resumption."""

from __future__ import annotations

import planner_agent.worker as worker_module
from langgraph.types import Command
from planner_agent.agent import PlannerAgent
from planner_agent.worker import parse_completion_event, run_completion_worker
from project.topics import AgentCompletionTopics, RAGTopics


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    def send(self, topic: str, value: dict) -> None:
        self.sent.append((topic, value))


class FakeMessage:
    def __init__(self, topic: str, value: dict) -> None:
        self.topic = topic
        self.value = value


def _rag_payload(request_id: str = "r1") -> dict:
    return {
        "request_id": request_id,
        "session_ctx": {"sid": "s1"},
        "user_prompt": "teach me",
        "compiled_material": "compiled markdown",
        "status": "complete",
        "errors": [],
        "total_pages_processed": 3,
        "total_pages_included": 2,
        "started_at": "2024-01-01T00:00:00Z",
        "completed_at": "2024-01-01T00:00:05Z",
        "duration_ms": 5000,
    }


# -- T048a: completion event consumption / parsing ------------------------
def test_parse_rag_completion() -> None:
    request_id, outputs = parse_completion_event(
        RAGTopics.RAG_COMPLETE.value, _rag_payload()
    )
    assert request_id == "r1"
    assert outputs == {"rag_compiled": "compiled markdown"}


def test_parse_teaching_completion() -> None:
    payload = {
        "request_id": "r2",
        "sid": "s1",
        "user_level": "beginner",
        "content": "a friendly lesson",
    }
    request_id, outputs = parse_completion_event(
        AgentCompletionTopics.TEACHING_COMPLETE.value, payload
    )
    assert request_id == "r2"
    assert outputs == {"teaching_materials": {"beginner": "a friendly lesson"}}


def test_parse_quiz_completion() -> None:
    payload = {"request_id": "r3", "sid": "s1", "quiz_content": "Q1?"}
    request_id, outputs = parse_completion_event(
        AgentCompletionTopics.QUIZ_COMPLETE.value, payload
    )
    assert request_id == "r3"
    assert outputs == {"quiz_content": "Q1?"}


def test_parse_unknown_topic_raises() -> None:
    try:
        parse_completion_event("nope", {})
    except ValueError as exc:
        assert "Unknown completion topic" in str(exc)
    else:  # pragma: no cover - must raise
        raise AssertionError("expected ValueError")


def test_completion_worker_resumes_matching_workflow(monkeypatch) -> None:
    messages = [FakeMessage(RAGTopics.RAG_COMPLETE.value, _rag_payload("rid"))]
    monkeypatch.setattr(worker_module, "make_consumer", lambda *topics: messages)

    resumed: list[tuple[str, dict]] = []

    class FakeAgent:
        def resume(self, request_id: str, outputs: dict) -> dict:
            resumed.append((request_id, outputs))
            return {"workflow_status": "complete"}

    run_completion_worker(agent=FakeAgent())

    assert resumed == [("rid", {"rag_compiled": "compiled markdown"})]


def test_completion_worker_survives_bad_event(monkeypatch) -> None:
    messages = [
        FakeMessage(RAGTopics.RAG_COMPLETE.value, {"bad": "payload"}),
        FakeMessage(
            AgentCompletionTopics.QUIZ_COMPLETE.value,
            {"request_id": "ok", "sid": "s", "quiz_content": "Q"},
        ),
    ]
    monkeypatch.setattr(worker_module, "make_consumer", lambda *topics: messages)

    resumed: list[str] = []

    class FakeAgent:
        def resume(self, request_id: str, outputs: dict) -> dict:
            resumed.append(request_id)
            return {"workflow_status": "complete"}

    run_completion_worker(agent=FakeAgent())

    # The first (invalid) event is logged and skipped; the second still resumes.
    assert resumed == ["ok"]


# -- T048b: Command issued with correct state -----------------------------
def test_resume_issues_command_with_outputs() -> None:
    agent = PlannerAgent(producer=FakeProducer())
    agent._active_requests.add("r1")

    captured: dict[str, object] = {}

    class FakeState:
        values = {"teaching_materials": {}}

    class FakeGraph:
        def get_state(self, config):
            return FakeState()

        def invoke(self, command, config):
            captured["command"] = command
            captured["config"] = config

    agent._graph = FakeGraph()  # type: ignore[assignment]
    agent.resume("r1", {"rag_compiled": "material"})

    command = captured["command"]
    assert isinstance(command, Command)
    assert command.update == {"rag_compiled": "material"}
    assert captured["config"]["configurable"]["thread_id"] == "r1"


# -- T048c: intermediate outputs merged into workflow state ---------------
def test_resume_merges_teaching_materials() -> None:
    agent = PlannerAgent(producer=FakeProducer())

    class FakeState:
        values = {"teaching_materials": {"beginner": "b-lesson"}}

    class FakeGraph:
        def get_state(self, config):
            return FakeState()

    agent._graph = FakeGraph()  # type: ignore[assignment]
    merged = agent._merge_outputs(
        "r1", {"configurable": {}}, {"teaching_materials": {"advanced": "a-lesson"}}
    )
    assert merged["teaching_materials"] == {
        "beginner": "b-lesson",
        "advanced": "a-lesson",
    }


# -- T048d: resumption correctness on a real graph ------------------------
def test_resume_real_graph_to_completion(monkeypatch) -> None:
    producer = FakeProducer()
    agent = PlannerAgent(producer=producer)

    # Provided level skips LLM; no file paths => fan out to teach_node, then pause.
    state = agent.run(
        {
            "user_prompt": "teach me",
            "user_level": ["beginner"],
            "sid": "s1",
            "file_paths": [],
        }
    )
    request_id = state["request_id"]
    assert state.get("workflow_status") != "complete"
    assert request_id in agent._active_requests

    final = agent.resume(request_id, {"teaching_materials": {"beginner": "lesson"}})

    assert final["workflow_status"] == "complete"
    assert final["teaching_materials"]["beginner"] == "lesson"
    assert request_id not in agent._active_requests


def test_resume_unknown_request_logs_warning(caplog) -> None:
    agent = PlannerAgent(producer=FakeProducer())

    class FakeState:
        values: dict = {}

    class FakeGraph:
        def get_state(self, config):
            return FakeState()

        def invoke(self, command, config):
            return None

    agent._graph = FakeGraph()  # type: ignore[assignment]
    import logging

    with caplog.at_level(logging.WARNING):
        agent.resume("ghost", {"quiz_content": "Q"})
    assert any("unknown/inactive" in r.message for r in caplog.records)
