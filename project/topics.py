"""Centralized Kafka topic registry."""

from __future__ import annotations

from enum import Enum


class PlannerTopics(str, Enum):
    """Topics published by the planner or consumed by downstream agents."""

    RAG = "rag"
    TEACHING = "teaching"


class RAGTopics(str, Enum):
    """Topics owned by the RAG service."""

    RAG_COMPLETE = "rag-complete"


class TeachingTopics(str, Enum):
    """Topics owned by the Teaching Agent."""

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
        list[str]: All topic names from PlannerTopics and RAGTopics enums
    """
    return [topic.value for topic in PlannerTopics] + [
        topic.value for topic in RAGTopics
    ] + [topic.value for topic in TeachingTopics]
