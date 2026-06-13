"""User-request ingestion API: accept a prompt + file uploads, route to planner.

Accepts ``multipart/form-data`` with parsed ``UserRequest`` form fields
(``user_prompt``, ``user_level``, ``sid``) and up to three uploaded files. Saves
the files to the configured uploads directory and publishes a
``PlannerRequestEvent`` to the ``init-planner`` Kafka topic.

Implementation is intentionally minimal; advanced validation, cleanup policies,
and richer error handling are deferred (see TODO markers).
"""

from __future__ import annotations

import logging
import os
import uuid

from typing import Annotated
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend_service.app.config import get_upload_dir
from backend_service.app.kafka_admin import KafkaAdminService
from project.schemas import PlannerRequestEvent, UserRequest
from project.topics import PlannerTopics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Maximum number of files accepted per request. Excess files trigger a warning
# log but do NOT reject the request (simple count check only).
MAX_FILES = 3


def _error(status_code: int, message: str) -> JSONResponse:
    """Return a simple error response: ``{"error": <message>}``."""
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/request")
async def ingest_user_request(
    request: Request,
    user_prompt: Annotated[str, Form(...)],
    sid: Annotated[str, Form(...)],
    user_level: Annotated[list[str], Form()] = [],
    files: Annotated[list[UploadFile], File()] = [],
) -> JSONResponse:
    """Accept a user request with optional file uploads and route to the planner.

    The ``UserRequest`` is supplied as parsed form fields (``user_prompt``,
    ``user_level``, ``sid``) so Swagger exposes them as separate inputs.
    """
    # Build and validate the UserRequest from parsed form fields.
    try:
        user_req = UserRequest(
            user_prompt=user_prompt,
            user_level=user_level,
            sid=sid,
        )
    except ValidationError as exc:
        return _error(400, f"Invalid UserRequest payload: {exc}")

    # Simple count check: warn on overflow but do not reject (FR-034).
    if len(files) > MAX_FILES:
        logger.warning(
            "Received %d files for sid=%s, exceeding the max of %d",
            len(files),
            user_req.sid,
            MAX_FILES,
        )

    # Save uploaded files and collect absolute paths.
    upload_dir = get_upload_dir()
    try:
        os.makedirs(upload_dir, exist_ok=True)
        file_paths: list[str] = []
        for upload in files:
            # TODO: validate file type/size before saving.
            unique_name = f"{uuid.uuid4().hex}_{upload.filename}"
            dest_path = os.path.join(upload_dir, unique_name)
            content = await upload.read()
            with open(dest_path, "wb") as handle:
                handle.write(content)
            file_paths.append(os.path.abspath(dest_path))
    except OSError as exc:
        return _error(500, f"Failed to save uploaded files: {exc}")

    # Build and publish the planner event.
    event = PlannerRequestEvent(
        user_prompt=user_req.user_prompt,
        user_level=user_req.user_level,
        sid=user_req.sid,
        file_paths=file_paths,
    )

    admin_service: KafkaAdminService = getattr(request.app.state, "kafka_admin", None)
    if admin_service is None:
        # TODO: distinguish transient vs. permanent producer unavailability.
        return _error(500, "Kafka admin service not available")

    try:
        producer = admin_service.producer
        future = producer.send(
            PlannerTopics.INIT_PLANNER.value, value=event.model_dump(mode="json")
        )
        future.get(timeout=5)
    except Exception as exc:  # noqa: BLE001 - minimal handling for this iteration
        # TODO: add retry/backoff and structured error reporting.
        # Files remain on disk (retained indefinitely) for later reprocessing.
        return _error(500, f"Failed to publish planner event: {exc}")

    return JSONResponse(
        status_code=200,
        content={"message": "Request accepted and queued for planner processing"},
    )
