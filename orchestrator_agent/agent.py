"""Planner Agent: LangGraph orchestrator for multi-agent learning workflows.

Builds a ``StateGraph`` that infers the user's knowledge level and then
dispatches work to the RAG, Teaching, and Quiz agents via Kafka.  Every
*produce* node publishes a request event keyed by ``request_id``; the
dedicated *await* node that follows it calls LangGraph's :func:`interrupt`
to pause the workflow with state checkpointed under ``request_id``.  When
an agent completion event arrives on any inbound topic the worker calls
:meth:`PlannerAgent.resume`, which delivers the payload to the pending
``interrupt()`` call via ``Command(resume=...)``.

Separating *produce* and *await* into distinct nodes ensures that resuming
the graph re-executes only the await node — request events are never
re-published on resume.

LLM is invoked in exactly two places (FR-024):

1. **infer_level** — when learner levels are *not* pre-provided, a single
   LLM call resolves both the level and whether a quiz was requested
   (``LEVEL_QUIZ_INFERENCE_PROMPT`` → ``LevelInferenceResult``).
2. **infer_level** — when the query is classified as COMPLEX a second LLM
   call rewrites it for downstream query quality (FR-022).

All other routing is rule-based.  Errors are caught at every stage and
appended to ``state["errors"]`` so the workflow never fails silently (FR-023).

All inbound / outbound Kafka payloads are validated against Pydantic v2
models defined in ``project/schemas.py`` (FR-016).  Every node emits at
least one structured log line (FR-014).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt

from orchestrator_agent import classifier, rewriter
from orchestrator_agent.config import get_confidence_threshold, get_llm_config
from orchestrator_agent.kafka import make_producer
from orchestrator_agent.llm_client import call_llm
from orchestrator_agent.prompts import LEVEL_QUIZ_INFERENCE_PROMPT
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


# ---------------------------------------------------------------------------
# LangGraph state — single dict shared across all 9 nodes
# ---------------------------------------------------------------------------


class PlannerState(TypedDict, total=False):
    """Internal LangGraph state (not shared with other agents).

    ``total=False`` means every key is optional so nodes can return partial
    dicts that update only the keys they own.
    """

    # ── initial fields set by run() ─────────────────────────────────────
    request_id: str
    user_prompt: str          # may be rewritten in infer_level for COMPLEX queries
    sid: str
    user_levels: list[str]    # finalised after infer_level
    file_paths: list[str]

    # ── infer_level outputs ─────────────────────────────────────────────
    quiz_requested: bool

    # ── await_rag output ────────────────────────────────────────────────
    rag_compiled: str

    # ── await_teaching output ───────────────────────────────────────────
    teaching_materials: dict[str, str]   # learner_level → teaching content

    # ── await_quiz output ───────────────────────────────────────────────
    quiz_content: str

    # ── control / diagnostics ───────────────────────────────────────────
    workflow_status: str      # "active" | "clarifying" | "blocked" | "complete" | "failed"
    errors: list[str]


# ---------------------------------------------------------------------------
# PlannerAgent
# ---------------------------------------------------------------------------


class PlannerAgent:
    """Consumes a planner request and orchestrates downstream learning agents.

    Lifecycle
    ---------
    1. :meth:`run` is called with a raw init-planner Kafka payload.  It
       validates it as :class:`~project.schemas.PlannerRequestEvent`, assigns
       a ``request_id``, builds the initial state, and invokes the graph.
       If the graph hits an :func:`interrupt` (awaiting an agent completion)
       it returns immediately with state checkpointed under ``request_id``.

    2. When a completion event arrives on any agent topic, the worker calls
       :meth:`resume` with ``request_id`` and the completion payload.
       LangGraph restores the checkpoint and continues from after the
       interrupted ``interrupt()`` call.

    3. The workflow terminates either in ``finish`` (success) or
       ``clarify_and_end`` (low-confidence level inference / injection
       detected), both of which produce a Kafka event and route to ``END``.

    Concurrency
    -----------
    ``_active_requests`` is a best-effort in-process guard used by
    :meth:`resume` to warn when a completion arrives for an unknown or
    already-finished workflow.  MemorySaver is not thread-safe by default;
    run each workflow on a dedicated thread or use an async checkpointer
    for concurrent workloads.
    """

    def __init__(self, producer: Any | None = None) -> None:
        """Initialise the planner agent.

        Args:
            producer: A kafka-python ``KafkaProducer`` (or any object
                implementing ``.send(topic, value, key)`` and ``.flush()``).
                When *None* a real producer is created lazily on first use
                via :func:`~planner_agent.kafka.make_producer`.
        """
        self._producer: Any | None = producer
        self._graph: CompiledStateGraph = self._build_graph()
        # Tracks request_ids of paused (in-flight) workflows.  Populated by
        # run(), cleared when a workflow reaches a terminal node.
        self._active_requests: set[str] = set()

    # ── producer ──────────────────────────────────────────────────────────

    @property
    def producer(self) -> Any:
        """Lazily initialise and return the Kafka producer."""
        if self._producer is None:
            self._producer = make_producer()
        return self._producer

    def _publish(
        self, topic: str, payload: dict[str, Any], request_id: str
    ) -> None:
        """Serialise *payload* and send it to *topic* keyed by *request_id*.

        The message key co-locates all events for one request on the same
        Kafka partition, preserving ordering guarantees (FR-007).

        Errors are logged rather than re-raised so a single publish failure
        does not crash the entire workflow (FR-023).
        """
        try:
            logger.info(
                "[%s] publish topic=%s payload_keys=%s",
                request_id,
                topic,
                list(payload.keys()),
            )
            self.producer.send(topic, value=payload, key=request_id)
            self.producer.flush()
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "[%s] publish_failed topic=%s error=%s", request_id, topic, exc
            )

    # ── graph construction ────────────────────────────────────────────────

    def _build_graph(self) -> CompiledStateGraph:
        """Compile and return the 9-node LangGraph StateGraph.

        Graph topology::

            START
              └─ infer_level ──(route)──► clarify_and_end ──► END
                                      ├─► run_rag ──► await_rag ──► dispatch_teaching
                                      └─► dispatch_teaching
                                              └─ await_teaching ──(route)──► run_quiz
                                                                          └─► finish
                                                      run_quiz ──► await_quiz ──► finish
                                                                                    └─► END
        """
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

        # RAG path: publish → pause (interrupt) → teaching dispatch.
        graph.add_edge("run_rag", "await_rag")
        graph.add_edge("await_rag", "dispatch_teaching")

        # Teaching: publish one request per level → pause until all complete.
        graph.add_edge("dispatch_teaching", "await_teaching")
        graph.add_conditional_edges("await_teaching", self._route_quiz)

        # Quiz path: publish → pause (interrupt) → finish.
        graph.add_edge("run_quiz", "await_quiz")
        graph.add_edge("await_quiz", "finish")
        graph.add_edge("finish", END)

        # MemorySaver checkpoints state before each interrupt() call so that
        # resume() can restore the exact point where execution paused (FR-020).
        return graph.compile(checkpointer=MemorySaver())

    # ── nodes ─────────────────────────────────────────────────────────────

    def _infer_level(self, state: PlannerState) -> dict[str, Any]:
        """[Node 1] Gate: detect injection, infer level, optionally rewrite query.

        Decision tree:

        * Injection pattern detected → ``workflow_status = "blocked"``.
        * ``user_levels`` pre-provided → skip LLM; use keyword quiz detection
          (FR-005).
        * Levels absent → one LLM call resolves level + quiz intent via
          ``LEVEL_QUIZ_INFERENCE_PROMPT`` (FR-024 Case 1).
          Low confidence → ``workflow_status = "clarifying"``.
        * Query is COMPLEX (FR-022) → one more LLM call rewrites
          ``user_prompt`` (FR-024 Case 2).

        Returns:
            Partial state dict updating ``user_levels``, ``quiz_requested``,
            ``user_prompt`` (if rewritten), and optionally ``workflow_status``
            and ``errors``.
        """
        request_id = state.get("request_id", "?")
        user_prompt: str = state.get("user_prompt", "")
        updates: dict[str, Any] = {}

        # ── injection check (always first, rule-based) ────────────────────
        if classifier.contains_injection_pattern(user_prompt):
            logger.warning("[%s] infer_level: injection pattern blocked", request_id)
            updates["errors"] = list(state.get("errors", [])) + [
                "Query blocked: prompt injection pattern detected."
            ]
            updates["workflow_status"] = "blocked"
            return updates

        # ── level determination ───────────────────────────────────────────
        if state.get("user_levels"):
            # Pre-provided — skip LLM, use keyword quiz detection (FR-005).
            updates["user_levels"] = [lvl.lower() for lvl in state["user_levels"]]
            updates["quiz_requested"] = classifier.detect_quiz_intent(user_prompt)
            logger.info(
                "[%s] infer_level: levels pre-provided=%s quiz=%s",
                request_id,
                updates["user_levels"],
                updates["quiz_requested"],
            )
        else:
            # LLM inference — Case 1 (FR-024): level + quiz in one call.
            logger.info("[%s] infer_level: calling LLM for level+quiz inference", request_id)
            try:
                raw = call_llm(
                    [
                        {
                            "role": "user",
                            "content": LEVEL_QUIZ_INFERENCE_PROMPT.format(
                                user_prompt=user_prompt
                            ),
                        }
                    ],
                    get_llm_config(),
                )
                print(raw)
                result = LevelInferenceResult(**json.loads(raw))
                logger.info(
                    "[%s] infer_level: level=%s confidence=%.2f quiz=%s reasoning=%r",
                    request_id,
                    result.level.value,
                    result.confidence,
                    result.quiz_requested,
                    result.reasoning,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "[%s] infer_level: LLM inference failed error=%s; routing to clarify",
                    request_id,
                    exc,
                )
                updates["errors"] = list(state.get("errors", [])) + [
                    f"Level inference failed: {exc}."
                ]
                updates["workflow_status"] = "clarifying"
                return updates

            if result.confidence < get_confidence_threshold():
                logger.info(
                    "[%s] infer_level: confidence=%.2f < threshold=%.2f → clarify",
                    request_id,
                    result.confidence,
                    get_confidence_threshold(),
                )
                updates["workflow_status"] = "clarifying"
                return updates

            updates["user_levels"] = [result.level.value]
            updates["quiz_requested"] = result.quiz_requested

        # ── query rewrite — Case 2: COMPLEX queries only (FR-022) ─────────
        complexity = classifier.detect_complexity(user_prompt)
        if complexity == "COMPLEX":
            primary_level = (
                updates.get("user_levels")
                or state.get("user_levels")
                or ["intermediate"]
            )[0]
            logger.info(
                "[%s] infer_level: query=COMPLEX calling rewrite LLM level=%s",
                request_id,
                primary_level,
            )
            try:
                rewritten = rewriter.rewrite_query(
                    user_prompt, primary_level, get_llm_config()
                )
                if rewritten and rewritten != user_prompt:
                    logger.info(
                        "[%s] infer_level: rewritten original_words=%d rewritten_words=%d",
                        request_id,
                        len(user_prompt.split()),
                        len(rewritten.split()),
                    )
                    updates["user_prompt"] = rewritten
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[%s] infer_level: rewrite failed error=%s using_original=true",
                    request_id,
                    exc,
                )
                updates["errors"] = list(state.get("errors", [])) + [
                    f"Query rewrite failed: {exc}; using original query."
                ]

        return updates

    def _clarify_and_end(self, state: PlannerState) -> dict[str, Any]:
        """[Node 2] Terminal: publish clarification or blocked event, then end.

        Two scenarios reach this node:

        * ``workflow_status == "blocked"`` — injection detected; emit a
          failed :class:`~project.schemas.WorkflowCompleteEvent`.
        * ``workflow_status == "clarifying"`` — level unclear; emit a
          :class:`~project.schemas.ClarifyUserLevelEvent` so the frontend
          can ask the learner to self-identify.

        Returns:
            Partial state dict (``workflow_status`` preserved).
        """
        request_id = state.get("request_id", "?")
        status = state.get("workflow_status", "clarifying")
        self._active_requests.discard(request_id)

        if status == "blocked":
            logger.warning("[%s] clarify_and_end: emitting failed workflow-complete", request_id)
            self._publish(
                PlannerAgentTopics.WORKFLOW_COMPLETE.value,
                WorkflowCompleteEvent(
                    request_id=request_id,
                    sid=state.get("sid", ""),
                    status="failed",
                ).model_dump(mode="json"),
                request_id,
            )
        else:
            logger.info("[%s] clarify_and_end: emitting clarify-user-level", request_id)
            self._publish(
                PlannerAgentTopics.CLARIFY_USER_LEVEL.value,
                ClarifyUserLevelEvent(
                    request_id=request_id,
                    user_prompt=state.get("user_prompt", ""),
                    sid=state.get("sid", ""),
                    reason=status,
                ).model_dump(mode="json"),
                request_id,
            )

        return {"workflow_status": status}

    def _run_rag(self, state: PlannerState) -> dict[str, Any]:
        """[Node 3] Publish a RAG request; await_rag will pause until it completes.

        Only reached when ``file_paths`` is non-empty (FR-006a).

        Returns:
            Empty dict — no state changes; await_rag owns the RAG output.
        """
        request_id = state.get("request_id", "?")
        logger.info(
            "[%s] run_rag: dispatching RAG request file_paths=%s",
            request_id,
            state.get("file_paths", []),
        )
        self._publish(
            PlannerTopics.RAG.value,
            RAGRequestEvent(
                request_id=request_id,
                session_ctx={"sid": state.get("sid", "")},
                user_request=state.get("user_prompt", ""),
                file_paths=list(state.get("file_paths", [])),
                source="planner-agent",
            ).model_dump(mode="json"),
            request_id,
        )
        return {}

    def _await_rag(self, state: PlannerState) -> dict[str, Any]:
        """[Node 4] Pause execution until a rag-complete event arrives.

        ``interrupt()`` suspends the graph here; LangGraph checkpoints state
        under ``request_id``.  When the worker calls ``resume()`` with the
        rag-complete payload, execution continues from after this call.

        Returns:
            Partial state dict with ``rag_compiled`` extracted from the
            completion payload.
        """
        request_id = state.get("request_id", "?")
        logger.info("[%s] await_rag: paused — waiting for rag-complete", request_id)

        outputs: dict[str, Any] = interrupt(
            {"await": "rag-complete", "request_id": request_id}
        )

        rag_compiled = str(
            outputs.get("compiled_material", outputs.get("rag_compiled", ""))
        )
        logger.info(
            "[%s] await_rag: resumed rag_chars=%d status=%s",
            request_id,
            len(rag_compiled),
            outputs.get("status", "?"),
        )
        if outputs.get("status") == "failed":
            logger.error(
                "[%s] await_rag: RAG agent reported failure errors=%s",
                request_id,
                outputs.get("errors"),
            )
        return {"rag_compiled": rag_compiled}

    def _dispatch_teaching(self, state: PlannerState) -> dict[str, Any]:
        """[Node 5] Fan-out: publish one teaching request per finalised learner level.

        RAG-compiled material (when available) is embedded so the Teaching
        agent can ground explanations in the uploaded content (FR-006b).

        Returns:
            Empty dict — no state changes; await_teaching owns all outputs.
        """
        request_id = state.get("request_id", "?")
        levels: list[str] = list(state.get("user_levels", ["intermediate"]))
        rag_compiled: str = state.get("rag_compiled", "")

        logger.info(
            "[%s] dispatch_teaching: levels=%s rag_available=%s",
            request_id,
            levels,
            bool(rag_compiled),
        )

        for level in levels:
            self._publish(
                PlannerTopics.TEACHING.value,
                TeachingRequestEvent(
                    request_id=request_id,
                    user_prompt=state.get("user_prompt", ""),
                    user_level=level,
                    rag_compiled=rag_compiled,
                    sid=state.get("sid", ""),
                ).model_dump(mode="json"),
                request_id,
            )
            logger.info(
                "[%s] dispatch_teaching: published level=%s", request_id, level
            )

        return {}

    def _await_teaching(self, state: PlannerState) -> dict[str, Any]:
        """[Node 6] Gather: collect one teaching completion per dispatched level.

        ``interrupt()`` is called once per level inside a for-loop.  LangGraph
        resumes execution from after each ``interrupt()`` call (not from the
        top of the function), so ``materials`` accumulates naturally across
        resumes.  Completion payloads carry ``user_level`` (or
        ``learner_level``) so out-of-order arrivals are stored correctly.

        Returns:
            Partial state dict with ``teaching_materials`` fully populated.
        """
        request_id = state.get("request_id", "?")
        levels: list[str] = list(state.get("user_levels", ["intermediate"]))
        # Seed from state so partial accumulation survives the first resume.
        materials: dict[str, str] = dict(state.get("teaching_materials", {}))

        logger.info(
            "[%s] await_teaching: paused — expecting completions for levels=%s",
            request_id,
            levels,
        )

        for _ in levels:
            outputs: dict[str, Any] = interrupt(
                {"await": "teaching-complete", "request_id": request_id}
            )
            level = str(
                outputs.get("user_level", outputs.get("learner_level", "unknown"))
            )
            content = str(
                outputs.get("content", outputs.get("teaching_content", ""))
            )
            materials[level] = content
            logger.info(
                "[%s] await_teaching: level=%s content_chars=%d status=%s",
                request_id,
                level,
                len(content),
                outputs.get("status", "?"),
            )
            if outputs.get("status") == "failed":
                logger.error(
                    "[%s] await_teaching: agent failure level=%s errors=%s",
                    request_id,
                    level,
                    outputs.get("errors"),
                )

        return {"teaching_materials": materials}

    def _run_quiz(self, state: PlannerState) -> dict[str, Any]:
        """[Node 7] Publish a quiz request; await_quiz will pause until it completes.

        Only reached when ``quiz_requested`` is True (FR-006c).  Teaching
        materials are forwarded so the Quiz agent generates contextualised
        questions.

        Returns:
            Empty dict — no state changes; await_quiz owns the quiz output.
        """
        request_id = state.get("request_id", "?")
        logger.info("[%s] run_quiz: dispatching quiz request", request_id)
        self._publish(
            PlannerAgentTopics.QUIZ_REQUEST.value,
            QuizRequestEvent(
                request_id=request_id,
                user_prompt=state.get("user_prompt", ""),
                user_levels=list(state.get("user_levels", ["intermediate"])),
                teaching_materials=dict(state.get("teaching_materials", {})),
                sid=state.get("sid", ""),
            ).model_dump(mode="json"),
            request_id,
        )
        return {}

    def _await_quiz(self, state: PlannerState) -> dict[str, Any]:
        """[Node 8] Pause execution until a quiz-complete event arrives.

        Returns:
            Partial state dict with ``quiz_content`` from the completion
            payload.
        """
        request_id = state.get("request_id", "?")
        logger.info("[%s] await_quiz: paused — waiting for quiz-complete", request_id)

        outputs: dict[str, Any] = interrupt(
            {"await": "quiz-complete", "request_id": request_id}
        )

        quiz_content = str(
            outputs.get(
                "quiz_content",
                json.dumps(outputs.get("questions", [])),
            )
        )
        logger.info(
            "[%s] await_quiz: resumed quiz_chars=%d status=%s",
            request_id,
            len(quiz_content),
            outputs.get("status", "?"),
        )
        if outputs.get("status") == "failed":
            logger.error(
                "[%s] await_quiz: quiz agent reported failure errors=%s",
                request_id,
                outputs.get("errors"),
            )
        return {"quiz_content": quiz_content}

    def _finish(self, state: PlannerState) -> dict[str, Any]:
        """[Node 9] Assemble outputs and publish the final WorkflowCompleteEvent.

        Derives overall status from what was collected:
        * ``"complete"`` — teaching (and optionally RAG / quiz) succeeded,
          no errors.
        * ``"partial"`` — some content collected but errors were logged.
        * ``"failed"`` — no usable content produced.

        Returns:
            Partial state dict with ``workflow_status = "complete"``.
        """
        request_id = state.get("request_id", "?")
        self._active_requests.discard(request_id)

        teaching_materials: dict[str, str] = dict(state.get("teaching_materials", {}))
        rag_compiled: str = state.get("rag_compiled", "")
        quiz_content: str = state.get("quiz_content", "")
        errors: list[str] = list(state.get("errors", []))

        has_teaching = any(v for v in teaching_materials.values())
        has_rag = bool(rag_compiled)
        has_quiz = bool(quiz_content)

        if not (has_teaching or has_rag or has_quiz):
            status = "failed"
        elif errors:
            status = "partial"
        else:
            status = "complete"

        logger.info(
            "[%s] finish: status=%s has_teaching=%s has_rag=%s has_quiz=%s errors=%d",
            request_id,
            status,
            has_teaching,
            has_rag,
            has_quiz,
            len(errors),
        )

        self._publish(
            PlannerAgentTopics.WORKFLOW_COMPLETE.value,
            WorkflowCompleteEvent(
                request_id=request_id,
                sid=state.get("sid", ""),
                rag_compiled=rag_compiled,
                teaching_materials=teaching_materials,
                quiz_content=quiz_content,
                status=status,
            ).model_dump(mode="json"),
            request_id,
        )

        return {"workflow_status": "complete"}

    # ── routers (all rule-based — no LLM, FR-024) ─────────────────────────

    def _route_after_infer(self, state: PlannerState) -> str:
        """Route from ``infer_level`` based on workflow status and file availability.

        Returns:
            ``"clarify_and_end"`` — level unclear or injection detected.
            ``"run_rag"`` — files present; RAG must run before teaching.
            ``"dispatch_teaching"`` — no files; go straight to teaching.
        """
        status = state.get("workflow_status", "active")
        if status in {"clarifying", "blocked"}:
            return "clarify_and_end"
        if state.get("file_paths"):
            return "run_rag"
        return "dispatch_teaching"

    def _route_quiz(self, state: PlannerState) -> str:
        """Route from ``await_teaching`` based on quiz intent.

        Returns:
            ``"run_quiz"`` — quiz keywords detected in the query (FR-006c).
            ``"finish"`` — no quiz intent; assemble final response immediately.
        """
        return "run_quiz" if state.get("quiz_requested") else "finish"

    # ── public entry points ────────────────────────────────────────────────

    def run(self, event: dict[str, Any]) -> None:
        """Start a new learning workflow from an init-planner Kafka payload.

        Validates *event* as a :class:`~project.schemas.PlannerRequestEvent`,
        assigns a fresh UUID ``request_id``, builds the initial
        :class:`PlannerState`, and invokes the compiled graph.

        Execution pauses at the first ``await_*`` node and returns to the
        caller; the worker then waits for agent completion events and calls
        :meth:`resume` for each one.

        Args:
            event: Raw Kafka payload dict from the init-planner topic.

        Raises:
            pydantic.ValidationError: if *event* does not conform to
                :class:`~project.schemas.PlannerRequestEvent`.
        """
        request = PlannerRequestEvent(**event)
        request_id = uuid.uuid4().hex
        logger.info(
            "run: new_workflow request_id=%s sid=%s has_files=%s user_levels=%s",
            request_id,
            request.sid,
            bool(request.file_paths),
            request.user_level,
        )

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
            "errors": [],
        }

        config: dict[str, Any] = {"configurable": {"thread_id": request_id}}
        self._active_requests.add(request_id)

        try:
            self._graph.invoke(initial_state, config)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "run: pipeline_error request_id=%s error=%s", request_id, exc
            )
            self._active_requests.discard(request_id)

    def resume(self, request_id: str, outputs: dict[str, Any]) -> None:
        """Resume a paused workflow with outputs from an agent completion event.

        Delivers *outputs* to the pending ``interrupt()`` call in the matching
        await node via ``Command(resume=outputs)`` and continues graph
        execution.  Teaching completions are self-describing (each carries its
        own ``user_level``), so the gather loop in :meth:`_await_teaching`
        accumulates materials in the correct slot regardless of arrival order.

        Args:
            request_id: Identifies the paused workflow thread in MemorySaver.
            outputs:    Agent completion payload (rag-complete, material-compiled,
                        or quiz-complete Kafka message as a plain dict).
        """
        if request_id not in self._active_requests:
            logger.warning(
                "resume: unknown_workflow request_id=%s (completed or never started)",
                request_id,
            )

        config: dict[str, Any] = {"configurable": {"thread_id": request_id}}
        logger.info(
            "resume: resuming request_id=%s output_keys=%s",
            request_id,
            list(outputs.keys()),
        )

        try:
            self._graph.invoke(Command(resume=outputs), config)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "resume: pipeline_error request_id=%s error=%s", request_id, exc
            )
            self._active_requests.discard(request_id)
