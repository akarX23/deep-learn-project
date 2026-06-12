"""Compatibility module for legacy service entrypoint."""

from __future__ import annotations

from rag_agent.worker import RAGWorker, main, process_consumer_batch

__all__ = ["RAGWorker", "process_consumer_batch", "main"]