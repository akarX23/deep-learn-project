"""Tests for the planner agent graph orchestration."""

from __future__ import annotations

from planner_agent.agent import PlannerAgent
from project.topics import PlannerAgentTopics, PlannerTopics


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    def send(self, topic: str, value: dict) -> None:
        self.sent.append((topic, value))


def _topics(producer: FakeProducer) -> list[str]:
    return [topic for topic, _ in producer.sent]


def test_run_assigns_request_id() -> None:
    producer = FakeProducer()
    agent = PlannerAgent(producer=producer)
    state = agent.run(
        {
            "user_prompt": "teach me photosynthesis",
            "user_level": ["beginner"],
            "sid": "s1",
            "file_paths": [],
        }
    )
    assert state["request_id"]
    assert state["sid"] == "s1"


def test_runs_get_distinct_request_ids() -> None:
    agent = PlannerAgent(producer=FakeProducer())
    event = {
        "user_prompt": "teach me",
        "user_level": ["beginner"],
        "sid": "s1",
        "file_paths": [],
    }
    first = agent.run(event)["request_id"]
    second = agent.run(event)["request_id"]
    assert first != second


def test_memorysaver_checkpoint_accessible_by_request_id() -> None:
    agent = PlannerAgent(producer=FakeProducer())
    state = agent.run(
        {
            "user_prompt": "teach me",
            "user_level": ["beginner"],
            "sid": "s1",
            "file_paths": [],
        }
    )
    config = {"configurable": {"thread_id": state["request_id"]}}
    snapshot = agent._graph.get_state(config)
    assert snapshot.values["request_id"] == state["request_id"]


def test_files_present_dispatches_rag() -> None:
    producer = FakeProducer()
    agent = PlannerAgent(producer=producer)
    agent.run(
        {
            "user_prompt": "explain these notes",
            "user_level": ["beginner"],
            "sid": "s1",
            "file_paths": ["/tmp/notes.pdf"],
        }
    )
    assert PlannerTopics.RAG.value in _topics(producer)


def test_no_files_fans_out_teaching_per_level() -> None:
    producer = FakeProducer()
    agent = PlannerAgent(producer=producer)
    agent.run(
        {
            "user_prompt": "teach me photosynthesis",
            "user_level": ["beginner", "intermediate"],
            "sid": "s1",
            "file_paths": [],
        }
    )
    teaching = [
        value
        for topic, value in producer.sent
        if topic == PlannerAgentTopics.TEACHING_REQUEST.value
    ]
    assert len(teaching) == 2
    assert {event["user_level"] for event in teaching} == {"beginner", "intermediate"}


def test_quiz_node_publishes_quiz_request() -> None:
    producer = FakeProducer()
    agent = PlannerAgent(producer=producer)
    agent._run_quiz(
        {
            "request_id": "r1",
            "user_prompt": "quiz me",
            "user_levels": ["beginner"],
            "teaching_materials": {"beginner": "..."},
            "sid": "s1",
        }
    )
    assert PlannerAgentTopics.QUIZ_REQUEST.value in _topics(producer)


def test_finish_node_publishes_workflow_complete() -> None:
    producer = FakeProducer()
    agent = PlannerAgent(producer=producer)
    agent._finish(
        {
            "request_id": "r1",
            "sid": "s1",
            "rag_compiled": "",
            "teaching_materials": {},
            "quiz_content": "",
        }
    )
    assert PlannerAgentTopics.WORKFLOW_COMPLETE.value in _topics(producer)


def test_route_quiz_branches_on_flag() -> None:
    agent = PlannerAgent(producer=FakeProducer())
    assert agent._route_quiz({"quiz_requested": True}) == "run_quiz"
    assert agent._route_quiz({"quiz_requested": False}) == "finish"
