"""Centralized Kafka topic registry."""

from __future__ import annotations

from enum import Enum


class PlannerTopics(str, Enum):
    """Topics the planner publishes to and downstream agents consume from."""

    RAG = "rag"
    TEACHING = "teaching"


class PlannerAgentTopics(str, Enum):
    """Planner-agent-specific outbound topics for control-plane events."""

    CLARIFY_USER_LEVEL = "clarify-user-level"
    QUIZ_REQUEST = "quiz"
    WORKFLOW_COMPLETE = "planner-response"


class RAGTopics(str, Enum):
    """Topics owned by the RAG service."""

    RAG_COMPLETE = "rag-complete"


class PlannerInboundTopics(str, Enum):
    """Topics the Planner Agent consumes."""

    INIT_PLANNER = "init-planner"
    USER_CLARIFICATION_RESPONSE = "user-clarification-response"
    RAG_COMPLETE = "rag-complete"
    MATERIAL_COMPILED = "material-compiled"
    QUIZ_COMPLETE = "quiz-complete"


class PlannerOutboundTopics(str, Enum):
    """Topics the Planner Agent produces to."""

    CLARIFY_USER_LEVEL = "clarify-user-level"
    RAG = "rag"
    TEACHING = "teaching"
    QUIZ = "quiz"
    PLANNER_RESPONSE = "planner-response"


def get_rag_topic_names() -> list[str]:
    """Return the full set of topics required by the RAG Kafka service."""

    return [PlannerTopics.RAG.value, RAGTopics.RAG_COMPLETE.value]


def get_planner_topic_names() -> list[str]:
    """Return all topics required by the Planner Agent."""

    return (
        [t.value for t in PlannerInboundTopics]
        + [t.value for t in PlannerOutboundTopics]
    )


def get_all_topic_names() -> list[str]:
    """Return the union of all topics registered across all topic enums.

    This aggregator function is the single source of truth for all Kafka topics
    required by the system. It is consumed by the backend service at startup to
    bootstrap the Kafka cluster with all required topics.

    Returns:
        list[str]: Deduplicated topic names from all registered topic enums.
    """
    seen: set[str] = set()
    result: list[str] = []
    for name in (
        [t.value for t in PlannerTopics]
        + [t.value for t in RAGTopics]
        + [t.value for t in PlannerInboundTopics]
        + [t.value for t in PlannerOutboundTopics]
    ):
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result
