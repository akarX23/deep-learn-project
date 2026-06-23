"""Tests covering the planner's clarified requirements (Session 2026-06-14).

Verifies:
- FR-015: the planner uses its own LiteLLM client/config, not rag_agent's.
- FR-014: each workflow stage emits a log line.
- FR-016: outbound Kafka payloads conform to project/schemas.py.
"""

from __future__ import annotations

import json
import logging

import planner_agent.agent as agent_module
import planner_agent.config as planner_config
import planner_agent.llm_client as planner_llm_client
from planner_agent.agent import PlannerAgent
from project.schemas import RAGRequestEvent, TeachingRequestEvent, WorkflowCompleteEventBody


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    def send(self, topic: str, value: dict) -> None:
        self.sent.append((topic, value))


def test_planner_uses_local_llm_client() -> None:
    # The call_llm bound in the agent module is the planner-local one (FR-015).
    assert agent_module.call_llm is planner_llm_client.call_llm


def test_planner_config_reads_planner_env(monkeypatch) -> None:
    monkeypatch.setenv("PLANNER_TEXT_MODEL", "planner-model")
    config = planner_config.get_llm_config()
    assert config["model"] == "planner-model"
    assert "planner-model" in str(config["routed_model"])


def test_infer_level_emits_log(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        agent_module,
        "call_llm",
        lambda messages, config: json.dumps(
            {"level": "advanced", "confidence": 0.95, "quiz_requested": False}
        ),
    )
    agent = PlannerAgent(producer=FakeProducer())
    with caplog.at_level(logging.INFO):
        agent._infer_level(
            {
                "request_id": "r1",
                "user_prompt": "p",
                "user_levels": [],
                "file_paths": [],
            }
        )
    assert any("Inferred level" in rec.message for rec in caplog.records)


def test_dispatch_emits_log(caplog) -> None:
    agent = PlannerAgent(producer=FakeProducer())
    with caplog.at_level(logging.INFO):
        agent._finish(
            {
                "request_id": "r1",
                "sid": "s1",
                "rag_compiled": "",
                "teaching_materials": {},
                "quiz_content": "",
            }
        )
    assert any("Workflow complete" in rec.message for rec in caplog.records)


def test_rag_dispatch_payload_conforms_to_schema() -> None:
    producer = FakeProducer()
    agent = PlannerAgent(producer=producer)
    agent._run_rag(
        {
            "request_id": "r1",
            "user_prompt": "explain these notes",
            "file_paths": ["/tmp/notes.pdf"],
            "sid": "s1",
        }
    )
    _, payload = producer.sent[0]
    # Re-parsing through the schema proves the payload is conformant (FR-016).
    RAGRequestEvent(**payload)


def test_teaching_and_workflow_payloads_conform_to_schema() -> None:
    producer = FakeProducer()
    agent = PlannerAgent(producer=producer)
    agent._teach_node(
        {
            "request_id": "r1",
            "user_prompt": "teach me",
            "current_level": "beginner",
            "sid": "s1",
        }
    )
    agent._finish(
        {
            "request_id": "r1",
            "sid": "s1",
            "rag_compiled": "",
            "teaching_materials": {"beginner": "..."},
            "quiz_content": "",
        }
    )
    teaching_payload = producer.sent[0][1]
    workflow_payload = producer.sent[1][1]
    TeachingRequestEvent(**teaching_payload)
    WorkflowCompleteEventBody(**workflow_payload)
