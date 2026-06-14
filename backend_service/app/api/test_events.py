from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from project.schemas import RAGRequestEvent
from backend_service.app.utils import default_rag_test_event

router = APIRouter(prefix="/api/v1/test-events", tags=["test-events"])


def _serialize_metadata(record_metadata: Any) -> dict[str, int | None] | None:
    """Serialize Kafka record metadata to a plain dict."""
    if record_metadata is None:
        return None

    metadata = {
        "partition": getattr(record_metadata, "partition", None),
        "offset": getattr(record_metadata, "offset", None),
        "timestamp": getattr(record_metadata, "timestamp", None),
    }
    return metadata


@router.post("/rag")
def publish_rag_test_event(
    request: Request, payload: RAGRequestEvent = default_rag_test_event()
) -> dict[str, Any]:
    """Publish a test event to the 'rag' topic.

    Accepts a full RAGRequestEvent as the request body.
    Uses the shared Kafka producer from the admin layer.
    """
    # Get the shared producer from the admin service stored in app state
    admin_service = getattr(request.app.state, "kafka_admin", None)
    if admin_service is None:
        raise HTTPException(status_code=500, detail="Kafka admin service not available")

    try:
        producer = admin_service.producer
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to get producer: {str(exc)}"
        ) from exc

    # Publish the event to Kafka
    try:
        future = producer.send("rag", value=payload.model_dump(mode="json"))
        record_metadata = future.get(timeout=5)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "request_id": payload.request_id,
        "topic": "rag",
        "publish_status": "published",
        "metadata": _serialize_metadata(record_metadata),
    }
