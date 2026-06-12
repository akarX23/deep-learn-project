from __future__ import annotations

import json

from rag_agent.logging import StructuredLogger


class _FakeLogger:
    def __init__(self) -> None:
        self.entries = []

    def log(self, level: int, message: str) -> None:
        self.entries.append((level, message))


def test_structured_logger_emits_request_lifecycle_entry() -> None:
    fake_logger = _FakeLogger()
    logger = StructuredLogger(fake_logger)

    entry = logger.emit(
        request_id="req-1",
        stage="processing_started",
        message="Starting pipeline",
        metadata={"file_count": 1},
    )

    assert entry.request_id == "req-1"
    payload = json.loads(fake_logger.entries[0][1])
    assert payload["stage"] == "processing_started"
    assert payload["metadata"]["file_count"] == 1