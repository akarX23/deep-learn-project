"""Structured lifecycle logging for Kafka-driven RAG processing."""

from __future__ import annotations

import json
import logging
from typing import Any

from project.schemas import RequestLifecycleLogEntry


class StructuredLogger:
    """Emit request lifecycle logs as structured JSON."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("rag_agent.lifecycle")

    def emit_log_entry(self, entry: RequestLifecycleLogEntry) -> RequestLifecycleLogEntry:
        """Write a validated lifecycle entry to the underlying logger."""

        level = getattr(logging, entry.level.upper(), logging.INFO)
        self._logger.log(level, json.dumps(entry.model_dump(), sort_keys=True))
        return entry

    def emit(
        self,
        *,
        request_id: str,
        stage: str,
        message: str,
        level: str = "INFO",
        metadata: dict[str, Any] | None = None,
    ) -> RequestLifecycleLogEntry:
        """Convenience wrapper for emitting a lifecycle entry."""

        entry = RequestLifecycleLogEntry(
            request_id=request_id,
            stage=stage,
            level=level,
            message=message,
            metadata=metadata or {},
        )
        return self.emit_log_entry(entry)

    def emit_startup_topic_check(
        self,
        *,
        missing_topics: list[str],
        level: str = "INFO",
    ) -> RequestLifecycleLogEntry:
        """Emit startup-stage topic presence result."""

        if missing_topics:
            message = (
                "Kafka startup topic check found missing topics: "
                + ", ".join(missing_topics)
            )
        else:
            message = "Kafka startup topic check passed"

        return self.emit(
            request_id="worker",
            stage="startup_topic_check",
            level=level,
            message=message,
            metadata={"missing_topics": missing_topics},
        )