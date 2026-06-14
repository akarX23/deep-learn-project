"""Tests for the planner level/quiz inference node."""

from __future__ import annotations

import json

import planner_agent.agent as agent_module
from planner_agent.agent import PlannerAgent
from project.topics import PlannerAgentTopics


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    def send(self, topic: str, value: dict) -> None:
        self.sent.append((topic, value))


def _patch_llm(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr(
        agent_module, "call_llm", lambda messages, config: json.dumps(payload)
    )


def test_provided_levels_skip_llm(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):  # pragma: no cover - must not be called
        raise AssertionError("LLM should not be called when levels are provided")

    monkeypatch.setattr(agent_module, "call_llm", _boom)
    agent = PlannerAgent(producer=FakeProducer())
    result = agent._infer_level(
        {"user_prompt": "p", "user_levels": ["beginner"], "file_paths": []}
    )
    assert result["user_levels"] == ["beginner"]


def test_high_confidence_sets_level(monkeypatch) -> None:
    _patch_llm(
        monkeypatch,
        {"level": "advanced", "confidence": 0.92, "quiz_requested": True},
    )
    agent = PlannerAgent(producer=FakeProducer())
    result = agent._infer_level(
        {"user_prompt": "deep dive please", "user_levels": [], "file_paths": []}
    )
    assert result["user_levels"] == ["advanced"]
    assert result["quiz_requested"] is True


def test_low_confidence_triggers_clarify(monkeypatch) -> None:
    _patch_llm(
        monkeypatch,
        {"level": "beginner", "confidence": 0.2, "quiz_requested": False},
    )
    agent = PlannerAgent(producer=FakeProducer())
    result = agent._infer_level(
        {"user_prompt": "hmm", "user_levels": [], "file_paths": []}
    )
    assert result["workflow_status"] == "clarifying"


def test_llm_failure_triggers_clarify(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise RuntimeError("llm down")

    monkeypatch.setattr(agent_module, "call_llm", _boom)
    agent = PlannerAgent(producer=FakeProducer())
    result = agent._infer_level(
        {"user_prompt": "hmm", "user_levels": [], "file_paths": []}
    )
    assert result["workflow_status"] == "clarifying"


def test_clarify_node_publishes_event() -> None:
    producer = FakeProducer()
    agent = PlannerAgent(producer=producer)
    agent._clarify_and_end(
        {
            "request_id": "r1",
            "user_prompt": "hmm",
            "sid": "s1",
            "workflow_status": "clarifying",
        }
    )
    assert producer.sent[0][0] == PlannerAgentTopics.CLARIFY_USER_LEVEL.value
