"""Centralized Kafka topic registry."""

from __future__ import annotations

from enum import Enum


class PlannerTopics(str, Enum):
    """Topics published by the planner or consumed by downstream agents."""

    RAG = "rag"
    INIT_PLANNER = "init-planner"


class RAGTopics(str, Enum):
    """Topics owned by the RAG service."""

    RAG_COMPLETE = "rag-complete"


class PlannerAgentTopics(str, Enum):
    """Topics produced by the planner agent to trigger downstream agents."""

    TEACHING_REQUEST = "teaching-request"
    QUIZ_REQUEST = "quiz-request"
    CLARIFY_USER_LEVEL = "clarify-user-level"
    WORKFLOW_COMPLETE = "workflow-complete"


class AgentCompletionTopics(str, Enum):
    """Completion topics consumed by the planner to resume workflows (future phase)."""

    TEACHING_COMPLETE = "teaching-complete"
    QUIZ_COMPLETE = "quiz-complete"


def get_rag_topic_names() -> list[str]:
    """Return the full set of topics required by the RAG Kafka service."""

    return [PlannerTopics.RAG.value, RAGTopics.RAG_COMPLETE.value]


def get_all_topic_names() -> list[str]:
    """Return the union of all topics registered across all topic enums.

    This aggregator function is the single source of truth for all Kafka topics
    required by the system. It is consumed by the backend service at startup to
    bootstrap the Kafka cluster with all required topics.

    Returns:
        list[str]: All topic names from every topic enum
    """
    return (
        [topic.value for topic in PlannerTopics]
        + [topic.value for topic in RAGTopics]
        + [topic.value for topic in PlannerAgentTopics]
        + [topic.value for topic in AgentCompletionTopics]
    )
