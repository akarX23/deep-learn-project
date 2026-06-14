"""Planner agent: LangGraph orchestrator for multi-agent learning workflows.

Builds a StateGraph that infers the user's knowledge level, then dispatches work
to the RAG, Teaching, and Quiz agents via Kafka. Dispatch nodes publish an event
and the graph pauses (static ``interrupt_after``) with state checkpointed by
``request_id``. Resumption from agent completion events is a future phase (see
TODO markers).

All inbound/outbound Kafka payloads cross schema boundaries defined in
``project/schemas.py`` (FR-016), every function is explicitly typed (FR-017),
and each workflow stage emits a log line (FR-014).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Protocol, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from kafka import KafkaProducer

from planner_agent.config import get_confidence_threshold, get_llm_config
from planner_agent.kafka import make_producer
from planner_agent.llm_client import call_llm
from planner_agent.prompts import LEVEL_QUIZ_INFERENCE_PROMPT
from project.schemas import (
    ClarifyUserLevelEvent,
    LevelInferenceResult,
    PlannerRequestEvent,
    QuizRequestEvent,
    RAGRequestEvent,
    TeachingRequestEvent,
    WorkflowCompleteEvent,
)
from project.topics import PlannerAgentTopics, PlannerTopics

logger = logging.getLogger(__name__)

# Nodes after which the graph pauses; state is checkpointed by request_id and
# resumed via Command(resume=...) when an agent completion event arrives (future).
DISPATCH_INTERRUPT_NODES = ["run_rag", "teach_node", "run_quiz"]


class PlannerState(TypedDict, total=False):
    """Internal LangGraph state (not shared with other agents)."""

    request_id: str
    user_prompt: str
    sid: str
    user_levels: list[str]
    file_paths: list[str]
    quiz_requested: bool
    current_level: str
    rag_compiled: str
    teaching_materials: dict[str, str]
    quiz_content: str
    workflow_status: str


class PlannerAgent:
    """Consumes a planner request and orchestrates downstream agents."""

    def __init__(self, producer: KafkaProducer | None = None) -> None:
        self._producer: KafkaProducer | None = producer
        self._graph: CompiledStateGraph = self._build_graph()

    # -- producer ---------------------------------------------------------
    @property
    def producer(self) -> KafkaProducer:
        if self._producer is None:
            self._producer = make_producer()
        return self._producer

    def _publish(self, topic: str, payload: dict[str, object]) -> None:
        logger.info("Publishing event to topic '%s'", topic)
        self.producer.send(topic, payload)

    # -- graph construction ----------------------------------------------
    def _build_graph(self) -> CompiledStateGraph:
        graph: StateGraph = StateGraph(PlannerState)
        graph.add_node("infer_level", self._infer_level)
        graph.add_node("clarify_and_end", self._clarify_and_end)
        graph.add_node("run_rag", self._run_rag)
        graph.add_node("teach_node", self._teach_node)
        graph.add_node("run_quiz", self._run_quiz)
        graph.add_node("finish", self._finish)

        graph.add_edge(START, "infer_level")
        graph.add_conditional_edges("infer_level", self._route_after_infer)
        graph.add_edge("clarify_and_end", END)
        graph.add_conditional_edges("run_rag", self._fan_out_teach)
        graph.add_conditional_edges("teach_node", self._route_quiz)
        graph.add_edge("run_quiz", "finish")
        graph.add_edge("finish", END)

        return graph.compile(
            checkpointer=MemorySaver(),
            interrupt_after=DISPATCH_INTERRUPT_NODES,
        )

    # -- nodes ------------------------------------------------------------
    def _infer_level(self, state: PlannerState) -> dict[str, object]:
        request_id = state.get("request_id", "")
        # Levels explicitly provided in the request: skip inference entirely.
        if state.get("user_levels"):
            logger.info(
                "[%s] Using provided user levels, skipping inference", request_id
            )
            # TODO: detect quiz intent via LLM when levels are pre-provided.
            return {"user_levels": state["user_levels"], "quiz_requested": False}

        logger.info("[%s] Inferring user level via planner LLM", request_id)
        try:
            prompt = LEVEL_QUIZ_INFERENCE_PROMPT.format(
                user_prompt=state["user_prompt"]
            )
            raw = call_llm([{"role": "user", "content": prompt}], get_llm_config())
            result = LevelInferenceResult(**json.loads(raw))
        except Exception as exc:  # noqa: BLE001 - minimal handling for this iteration
            logger.warning("[%s] Level inference failed: %s", request_id, exc)
            return self._clarify(state, "level inference failed")

        if result.confidence < get_confidence_threshold():
            return self._clarify(
                state, f"confidence below threshold ({result.confidence})"
            )

        logger.info(
            "[%s] Inferred level=%s quiz_requested=%s",
            request_id,
            result.level.value,
            result.quiz_requested,
        )
        return {
            "user_levels": [result.level.value],
            "quiz_requested": result.quiz_requested,
        }

    def _clarify(self, state: PlannerState, reason: str) -> dict[str, object]:
        logger.info(
            "[%s] Clarification required: %s", state.get("request_id", ""), reason
        )
        return {"workflow_status": "clarifying"}

    def _clarify_and_end(self, state: PlannerState) -> dict[str, object]:
        event = ClarifyUserLevelEvent(
            request_id=state["request_id"],
            user_prompt=state["user_prompt"],
            sid=state["sid"],
            reason=state.get("workflow_status", "clarifying"),
        )
        self._publish(
            PlannerAgentTopics.CLARIFY_USER_LEVEL.value, event.model_dump(mode="json")
        )
        return {"workflow_status": "clarifying"}

    def _run_rag(self, state: PlannerState) -> dict[str, object]:
        # NOTE: published to the RAG agent's inbound topic ("rag").
        # TODO: resume the graph via Command(resume=...) when rag-complete arrives.
        logger.info("[%s] Dispatching RAG request", state["request_id"])
        event = RAGRequestEvent(
            request_id=state["request_id"],
            session_ctx={"sid": state["sid"]},
            user_request=state["user_prompt"],
            file_paths=list(state["file_paths"]),
            source="planner-agent",
        )
        self._publish(PlannerTopics.RAG.value, event.model_dump(mode="json"))
        return {}

    def _teach_node(self, state: PlannerState) -> dict[str, object]:
        # TODO: resume via Command(resume=...) to fill teaching_materials[level].
        logger.info(
            "[%s] Dispatching teaching request for level=%s",
            state["request_id"],
            state["current_level"],
        )
        event = TeachingRequestEvent(
            request_id=state["request_id"],
            user_prompt=state["user_prompt"],
            user_level=state["current_level"],
            rag_compiled=state.get("rag_compiled", ""),
            sid=state["sid"],
        )
        self._publish(
            PlannerAgentTopics.TEACHING_REQUEST.value, event.model_dump(mode="json")
        )
        return {}

    def _run_quiz(self, state: PlannerState) -> dict[str, object]:
        # TODO: resume via Command(resume=...) to fill quiz_content.
        logger.info("[%s] Dispatching quiz request", state["request_id"])
        event = QuizRequestEvent(
            request_id=state["request_id"],
            user_prompt=state["user_prompt"],
            user_levels=state.get("user_levels", []),
            teaching_materials=state.get("teaching_materials", {}),
            sid=state["sid"],
        )
        self._publish(
            PlannerAgentTopics.QUIZ_REQUEST.value, event.model_dump(mode="json")
        )
        return {}

    def _finish(self, state: PlannerState) -> dict[str, object]:
        logger.info("[%s] Workflow complete", state["request_id"])
        event = WorkflowCompleteEvent(
            request_id=state["request_id"],
            sid=state["sid"],
            rag_compiled=state.get("rag_compiled", ""),
            teaching_materials=state.get("teaching_materials", {}),
            quiz_content=state.get("quiz_content", ""),
        )
        self._publish(
            PlannerAgentTopics.WORKFLOW_COMPLETE.value, event.model_dump(mode="json")
        )
        return {"workflow_status": "complete"}

    # -- routers ----------------------------------------------------------
    def _route_after_infer(self, state: PlannerState) -> str | list[Send]:
        if state.get("workflow_status") == "clarifying":
            return "clarify_and_end"
        if state.get("file_paths"):
            return "run_rag"
        return self._fan_out_teach(state)

    def _fan_out_teach(self, state: PlannerState) -> list[Send]:
        return [
            Send("teach_node", {**state, "current_level": level})
            for level in state.get("user_levels", [])
        ]

    def _route_quiz(self, state: PlannerState) -> str:
        return "run_quiz" if state.get("quiz_requested") else "finish"

    # -- entry point ------------------------------------------------------
    def run(self, event: dict[str, object]) -> dict[str, object]:
        """Run the workflow for a single init-planner event payload."""

        request = PlannerRequestEvent(**event)
        request_id = uuid.uuid4().hex
        logger.info("Assigned request_id=%s for sid=%s", request_id, request.sid)
        initial_state: PlannerState = {
            "request_id": request_id,
            "user_prompt": request.user_prompt,
            "sid": request.sid,
            "user_levels": list(request.user_level),
            "file_paths": list(request.file_paths),
            "quiz_requested": False,
            "rag_compiled": "",
            "teaching_materials": {},
            "quiz_content": "",
            "workflow_status": "active",
        }
        config: dict[str, object] = {"configurable": {"thread_id": request_id}}
        self._graph.invoke(initial_state, config)
        return dict(self._graph.get_state(config).values)
