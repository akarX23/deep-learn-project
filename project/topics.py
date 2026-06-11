"""Centralized Kafka topic registry."""

from __future__ import annotations

from enum import Enum


class PlannerTopics(str, Enum):
    """Topics published by the planner or consumed by downstream agents."""

    RAG = "rag"


class RAGTopics(str, Enum):
    """Topics owned by the RAG service."""

    RAG_COMPLETE = "rag-complete"


def get_rag_topic_names() -> list[str]:
    """Return the full set of topics required by the RAG Kafka service."""

    return [PlannerTopics.RAG.value, RAGTopics.RAG_COMPLETE.value]