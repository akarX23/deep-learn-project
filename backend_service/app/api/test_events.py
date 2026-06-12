from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from backend_service.app.config import KafkaSettings
from project.schemas import RAGRequestEvent

router = APIRouter(prefix="/api/v1/test-events", tags=["test-events"])


class RAGTestEventRequest(BaseModel):
    overrides: dict[str, Any] | None = None

    @field_validator("overrides")
    @classmethod
    def _validate_overrides(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is None:
            return value
        if not isinstance(value, dict):
            raise ValueError("overrides must be an object")
        return value


def _default_rag_test_event() -> dict[str, Any]:
    return {
        "request_id": f"test-{uuid4().hex}",
        "session_ctx": {
            "source": "backend-service",
            "mode": "development-test",
        },
        "user_request": "Summarize gradient descent for local integration testing.",
        "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
        "source": "backend-service",
    }


def _merge_rag_test_event(overrides: dict[str, Any] | None) -> RAGRequestEvent:
    merged = _default_rag_test_event()
    if overrides:
        merged.update(overrides)
    return RAGRequestEvent(**merged)


def _serialize_metadata(record_metadata: Any) -> dict[str, int | None] | None:
    if record_metadata is None:
        return None

    metadata = {
        "partition": getattr(record_metadata, "partition", None),
        "offset": getattr(record_metadata, "offset", None),
        "timestamp": getattr(record_metadata, "timestamp", None),
    }
    return metadata


def build_test_event_producer(settings: KafkaSettings) -> Any:
    from kafka import KafkaProducer

    return KafkaProducer(
        **settings.admin_kwargs(),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def _get_test_event_producer(request: Request) -> Any:
    producer = getattr(request.app.state, "test_event_producer", None)
    if producer is not None:
        return producer

    factory = getattr(request.app.state, "test_event_producer_factory", None)
    if factory is None:
        raise RuntimeError("Test-event producer is not configured")

    producer = factory(request.app.state.kafka_settings)
    request.app.state.test_event_producer = producer
    return producer


@router.post("/rag")
def publish_rag_test_event(request: Request, payload: RAGTestEventRequest) -> dict[str, Any]:
    try:
        event = _merge_rag_test_event(payload.overrides)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    producer = _get_test_event_producer(request)

    try:
        future = producer.send("rag", value=event.model_dump(mode="json"))
        record_metadata = future.get(timeout=5)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "request_id": event.request_id,
        "topic": "rag",
        "publish_status": "published",
        "metadata": _serialize_metadata(record_metadata),
    }
