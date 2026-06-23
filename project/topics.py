"""Centralized Kafka topic registry."""

from __future__ import annotations

from enum import Enum


class PlannerTopics(str, Enum):
    """Topics published by the planner or consumed by downstream agents."""

    RAG = "rag"
    INIT_PLANNER = "init-planner"
    TEACHING = "teaching"


class RAGTopics(str, Enum):
    """Topics owned by the RAG service."""

    RAG_COMPLETE = "rag-complete"


class PlannerAgentTopics(str, Enum):
    """Topics produced by the planner agent to trigger downstream agents."""

    QUIZ_REQUEST = "quiz-request"
    CLARIFY_USER_LEVEL = "clarify-user-level"
    WORKFLOW_COMPLETE = "workflow-complete"


class BackendStreamTopics(str, Enum):
    """Topics the backend consumes to forward events to Socket.IO sessions."""

    STREAM_TOKENS = "stream-tokens"
    STREAM_PROGRESS_UPDATE = "stream-progress-update"


class AgentCompletionTopics(str, Enum):
    """Completion topics consumed by the planner to resume paused workflows."""

    TEACHING_COMPLETE = "teaching-complete"
    QUIZ_COMPLETE = "quiz-complete"


class TeachingTopics(str, Enum):
    """Topics owned by the Teaching Agent."""

    TEACHING_COMPLETE = "teaching-complete"


class QuizAgentTopics(str, Enum):
    """Topics consumed by the Quiz Agent."""

    QUIZ_EVALUATE = "quiz-evaluate"
class PlannerInboundTopics(str, Enum):
    """All topics consumed by the orchestrator_agent worker (single consumer)."""

    INIT_PLANNER = "init-planner"
    RAG_COMPLETE = "rag-complete"
    MATERIAL_COMPILED = "material-compiled"
    QUIZ_COMPLETE = "quiz-complete"
    TEACHING_COMPLETE = "teaching-complete"


def get_rag_topic_names() -> list[str]:
    """Return the full set of topics required by the RAG Kafka service."""

    return [PlannerTopics.RAG.value, RAGTopics.RAG_COMPLETE.value]


def get_teaching_topic_names() -> list[str]:
    """Return the full set of topics required by the Teaching Agent Kafka service."""

    return [PlannerTopics.TEACHING.value, TeachingTopics.TEACHING_COMPLETE.value]


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
        + [topic.value for topic in TeachingTopics]
        + [topic.value for topic in BackendStreamTopics]
    )


def get_backend_consumer_topic_names() -> list[str]:
    """Return topics the backend consumer subscribes to for Socket.IO forwarding."""

    return [
        PlannerAgentTopics.CLARIFY_USER_LEVEL.value,
        BackendStreamTopics.STREAM_TOKENS.value,
        BackendStreamTopics.STREAM_PROGRESS_UPDATE.value,
        PlannerAgentTopics.WORKFLOW_COMPLETE.value,
    ]
