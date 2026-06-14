"""Tests for the planner worker runtime loop."""

from __future__ import annotations

import planner_agent.worker as worker_module


class FakeMessage:
    def __init__(self, value: dict) -> None:
        self.value = value


def test_worker_processes_each_message(monkeypatch) -> None:
    messages = [
        FakeMessage(
            {
                "user_prompt": "teach me",
                "user_level": ["beginner"],
                "sid": "s1",
                "file_paths": [],
            }
        )
    ]
    monkeypatch.setattr(worker_module, "make_consumer", lambda topic: messages)

    processed: list[dict] = []

    class FakeAgent:
        def run(self, event: dict) -> dict:
            processed.append(event)
            return {}

    monkeypatch.setattr(worker_module, "PlannerAgent", lambda: FakeAgent())

    worker_module.run_worker()

    assert processed == [messages[0].value]


def test_worker_survives_processing_error(monkeypatch) -> None:
    messages = [FakeMessage({"bad": "event"}), FakeMessage({"also": "bad"})]
    monkeypatch.setattr(worker_module, "make_consumer", lambda topic: messages)

    calls: list[dict] = []

    class FakeAgent:
        def run(self, event: dict) -> dict:
            calls.append(event)
            raise ValueError("boom")

    monkeypatch.setattr(worker_module, "PlannerAgent", lambda: FakeAgent())

    worker_module.run_worker()

    assert len(calls) == 2
