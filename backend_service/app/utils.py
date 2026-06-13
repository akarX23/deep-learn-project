from __future__ import annotations

from uuid import uuid4

from project.schemas import RAGRequestEvent


def default_rag_test_event() -> RAGRequestEvent:
    return RAGRequestEvent(
        request_id=f"test-{uuid4().hex}",
        session_ctx={"source": "backend-service", "mode": "integration-test"},
        user_request="Summarize gradient descent for local integration testing.",
        file_paths=["rag_agent/tests/inputs/sample.pdf"],
        created_at=None,
        source="backend-service",
    )
