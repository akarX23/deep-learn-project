"""Planner agent: LangGraph orchestrator for multi-agent learning workflows.

Builds a StateGraph that infers the user's knowledge level, then dispatches work
to the RAG, Teaching, and Quiz agents via Kafka. Each producer node publishes a
request event keyed by ``request_id``; a dedicated *await* node that follows it
calls LangGraph's :func:`interrupt` to pause the workflow with state checkpointed
by ``request_id``. When an agent completion event arrives, :meth:`PlannerAgent.resume`
resumes the workflow with ``Command(resume=...)``, delivering the completion
outputs to the pending ``interrupt()`` call.

Separating *produce* and *await* into distinct nodes ensures that resuming the
graph re-executes only the await node (so request events are never re-published).

All inbound/outbound Kafka payloads cross schema boundaries defined in
``project/schemas.py`` (FR-016), every function is explicitly typed (FR-017),
and each workflow stage emits a log line (FR-014).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from kafka import KafkaProducer

from planner_agent.config import get_confidence_threshold, get_llm_config
from planner_agent.kafka import make_producer
from planner_agent.llm_client import call_llm
from planner_agent.prompts import LEVEL_QUIZ_INFERENCE_PROMPT
from project.schemas import (
    ClarifyUserLevelEventBody,
    LevelInferenceResult,
    PlannerRequestEvent,
    QuizRequestEvent,
    RAGRequestEvent,
    TeachingRequestEvent,
    WorkflowCompleteEventBody,
)
from project.topics import PlannerAgentTopics, PlannerTopics

logger = logging.getLogger(__name__)


class PlannerState(TypedDict, total=False):
    """Internal LangGraph state (not shared with other agents)."""

    request_id: str
    user_prompt: str
    sid: str
    user_levels: list[str]
    file_paths: list[str]
    quiz_requested: bool
    rag_compiled: str
    teaching_materials: dict[str, str]
    quiz_content: str
    workflow_status: str


class PlannerAgent:
    """Consumes a planner request and orchestrates downstream agents."""

    def __init__(self, producer: KafkaProducer | None = None) -> None:
        self._producer: KafkaProducer | None = producer
        self._graph: CompiledStateGraph = self._build_graph()
        # Resumption registry: request_ids of in-flight (paused) workflows that
        # the completion consumer may resume. Populated by run(), cleared once a
        # workflow reaches its terminal state.
        self._active_requests: set[str] = set()

    # -- producer ---------------------------------------------------------
    @property
    def producer(self) -> KafkaProducer:
        if self._producer is None:
            self._producer = make_producer()
        return self._producer

    def _publish(self, topic: str, payload: dict[str, object], request_id: str) -> None:
        # request_id is the Kafka message key so downstream agents (and their
        # completion events) stay correlated to this workflow.
        logger.info("[%s] Publishing event to topic '%s'", request_id, topic)
        self.producer.send(topic, value=payload, key=request_id)

    # -- graph construction ----------------------------------------------
    def _build_graph(self) -> CompiledStateGraph:
        graph: StateGraph = StateGraph(PlannerState)
        graph.add_node("infer_level", self._infer_level)
        graph.add_node("clarify_and_end", self._clarify_and_end)
        graph.add_node("run_rag", self._run_rag)
        graph.add_node("await_rag", self._await_rag)
        graph.add_node("dispatch_teaching", self._dispatch_teaching)
        graph.add_node("await_teaching", self._await_teaching)
        graph.add_node("run_quiz", self._run_quiz)
        graph.add_node("await_quiz", self._await_quiz)
        graph.add_node("finish", self._finish)

        graph.add_edge(START, "infer_level")
        graph.add_conditional_edges("infer_level", self._route_after_infer)
        graph.add_edge("clarify_and_end", END)
        # RAG: publish -> pause (interrupt) -> teaching dispatch.
        graph.add_edge("run_rag", "await_rag")
        graph.add_edge("await_rag", "dispatch_teaching")
        # Teaching: publish one request per level -> pause until all complete.
        graph.add_edge("dispatch_teaching", "await_teaching")
        graph.add_conditional_edges("await_teaching", self._route_quiz)
        # Quiz: publish -> pause (interrupt) -> finish.
        graph.add_edge("run_quiz", "await_quiz")
        graph.add_edge("await_quiz", "finish")
        graph.add_edge("finish", END)

        # Pausing is performed dynamically inside the await_* nodes via
        # interrupt(); no static interrupt_after is configured.
        return graph.compile(checkpointer=MemorySaver())

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
        event = ClarifyUserLevelEventBody(
            request_id=state["request_id"],
            user_prompt=state["user_prompt"],
            sid=state["sid"],
            reason=state.get("workflow_status", "clarifying"),
        )
        self._publish(
            PlannerAgentTopics.CLARIFY_USER_LEVEL.value,
            event.model_dump(mode="json"),
            state["request_id"],
        )
        return {"workflow_status": "clarifying"}

    def _run_rag(self, state: PlannerState) -> dict[str, object]:
        # Publishes to the RAG agent's inbound topic ("rag"). The subsequent
        # await_rag node pauses the graph until a rag-complete event is consumed.
        logger.info("[%s] Dispatching RAG request", state["request_id"])
        event = RAGRequestEvent(
            request_id=state["request_id"],
            session_ctx={"sid": state["sid"]},
            user_request=state["user_prompt"],
            file_paths=list(state["file_paths"]),
            source="planner-agent",
        )
        self._publish(
            PlannerTopics.RAG.value, event.model_dump(mode="json"), state["request_id"]
        )
        return {}

    def _await_rag(self, state: PlannerState) -> dict[str, object]:
        # Pauses here until resume() delivers the rag-complete outputs. On
        # resume, only this node re-executes, so run_rag never re-publishes.
        outputs = interrupt(
            {"await": "rag-complete", "request_id": state["request_id"]}
        )
        logger.info("[%s] Resumed with RAG completion outputs", state["request_id"])
        return {"rag_compiled": str(outputs.get("rag_compiled", ""))}

    def _dispatch_teaching(self, state: PlannerState) -> dict[str, object]:
        # Fan-out: publish one teaching request per user level. The graph waits
        # for all of them in await_teaching.
        levels = list(state.get("user_levels", []))
        logger.info(
            "[%s] Dispatching teaching requests for levels=%s",
            state["request_id"],
            levels,
        )
        for level in levels:
            event = TeachingRequestEvent(
                request_id=state["request_id"],
                user_prompt=state["user_prompt"],
                user_level=level,
                rag_compiled=state.get("rag_compiled", ""),
                sid=state["sid"],
            )
            self._publish(
                PlannerTopics.TEACHING.value,
                event.model_dump(mode="json"),
                state["request_id"],
            )
        return {}

    def _await_teaching(self, state: PlannerState) -> dict[str, object]:
        # Gather node: interrupt once per dispatched level. Each resume delivers
        # one teaching-complete payload (self-describing via user_level), so
        # completion order does not matter. Re-executes wholly on each resume.
        levels = list(state.get("user_levels", []))
        materials: dict[str, str] = dict(state.get("teaching_materials", {}))
        for _ in levels:
            outputs = interrupt(
                {"await": "teaching-complete", "request_id": state["request_id"]}
            )
            level = str(outputs.get("user_level", ""))
            materials[level] = str(outputs.get("content", ""))
            logger.info(
                "[%s] Resumed with teaching completion for level=%s",
                state["request_id"],
                level,
            )
        return {"teaching_materials": materials}

    def _run_quiz(self, state: PlannerState) -> dict[str, object]:
        # Publishes the quiz request; await_quiz pauses until quiz-complete.
        logger.info("[%s] Dispatching quiz request", state["request_id"])
        event = QuizRequestEvent(
            request_id=state["request_id"],
            user_prompt=state["user_prompt"],
            user_levels=state.get("user_levels", []),
            teaching_materials=state.get("teaching_materials", {}),
            sid=state["sid"],
        )
        self._publish(
            PlannerAgentTopics.QUIZ_REQUEST.value,
            event.model_dump(mode="json"),
            state["request_id"],
        )
        return {}

    def _await_quiz(self, state: PlannerState) -> dict[str, object]:
        outputs = interrupt(
            {"await": "quiz-complete", "request_id": state["request_id"]}
        )
        logger.info("[%s] Resumed with quiz completion outputs", state["request_id"])
        return {"quiz_content": str(outputs.get("quiz_content", ""))}

    def _finish(self, state: PlannerState) -> dict[str, object]:
        logger.info("[%s] Workflow complete", state["request_id"])
        event = WorkflowCompleteEventBody(
            request_id=state["request_id"],
            sid=state["sid"],
            rag_compiled=state.get("rag_compiled", ""),
            teaching_materials=state.get("teaching_materials", {}),
            quiz_content=state.get("quiz_content", ""),
        )
        self._publish(
            PlannerAgentTopics.WORKFLOW_COMPLETE.value,
            event.model_dump(mode="json"),
            state["request_id"],
        )
        return {"workflow_status": "complete"}

    # -- routers ----------------------------------------------------------
    def _route_after_infer(self, state: PlannerState) -> str:
        if state.get("workflow_status") == "clarifying":
            return "clarify_and_end"
        if state.get("file_paths"):
            return "run_rag"
        return "dispatch_teaching"

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
        self._active_requests.add(request_id)
        self._graph.invoke(initial_state, config)

    # -- resumption -------------------------------------------------------
    def resume(self, request_id: str, outputs: dict[str, object]) -> dict[str, object]:
        """Resume a paused workflow with outputs from an agent completion event.

        Delivers ``outputs`` to the pending ``interrupt()`` call in the await node
        (keyed by ``request_id``) via ``Command(resume=...)`` and continues graph
        execution. Teaching completions are self-describing (each carries its own
        ``user_level``), so the gather node accumulates ``teaching_materials``
        internally and out-of-order completions are handled safely.
        """

        if request_id not in self._active_requests:
            logger.warning(
                "[%s] Resume requested for unknown/inactive workflow", request_id
            )
        config: dict[str, object] = {"configurable": {"thread_id": request_id}}
        logger.info(
            "[%s] Resuming workflow with outputs: %s", request_id, list(outputs)
        )
        self._graph.invoke(Command(resume=outputs), config)
