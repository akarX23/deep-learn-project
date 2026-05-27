"""RAG agent package exports."""

from __future__ import annotations

__all__ = ["RAGAgent"]


def __getattr__(name: str):
	if name == "RAGAgent":
		from rag_agent.agent import RAGAgent

		return RAGAgent
	raise AttributeError(name)
