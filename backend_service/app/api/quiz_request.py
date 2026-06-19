"""Quiz-request API: accept quiz generation input and route to quiz agent.

Accepts a JSON body containing ``sid``, ``user_prompt``, and ``teaching_material``.
Builds a ``QuizRequestEvent`` with a randomly selected user level and publishes it
onto the ``quiz-request`` Kafka topic.
"""

from __future__ import annotations

import random
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend_service.app.kafka_admin import KafkaAdminService
from project.schemas import (
    Quiz,
    QuizContentRequest,
    QuizEvaluateRequestEvent,
    QuizRequestEvent,
    SubmittedAnswer,
    UserLevelEnum,
)
from project.topics import PlannerAgentTopics, QuizAgentTopics

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


class QuizEvaluateApiRequest(BaseModel):
    sid: str
    quiz: Quiz
    answers: list[SubmittedAnswer]


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/request")
async def create_quiz_request(
    request: Request,
    payload: QuizContentRequest,
) -> JSONResponse:
    selected_level = random.choice([level.value for level in UserLevelEnum])

    event = QuizRequestEvent(
        request_id=f"quiz-{uuid.uuid4().hex}",
        user_prompt=payload.user_prompt,
        user_levels=[selected_level],
        teaching_materials={selected_level: payload.teaching_material},
        sid=payload.sid,
    )

    admin_service: KafkaAdminService = getattr(request.app.state, "kafka_admin", None)
    if admin_service is None:
        return _error(500, "Kafka admin service not available")

    try:
        producer = admin_service.producer
        future = producer.send(
            PlannerAgentTopics.QUIZ_REQUEST.value, value=event.model_dump(mode="json")
        )
        future.get(timeout=5)
    except Exception as exc:  # noqa: BLE001 - intentionally minimal handling
        return _error(500, f"Failed to publish quiz request event: {exc}")

    return JSONResponse(
        status_code=200,
        content={"message": "Quiz request accepted and queued"},
    )


@router.post("/evaluate")
async def create_quiz_evaluate_request(
    request: Request,
    payload: QuizEvaluateApiRequest,
) -> JSONResponse:
    admin_service: KafkaAdminService = getattr(request.app.state, "kafka_admin", None)
    if admin_service is None:
        return _error(500, "Kafka admin service not available")

    event = QuizEvaluateRequestEvent(
        request_id=f"quiz-eval-{uuid.uuid4().hex}",
        sid=payload.sid,
        quiz=payload.quiz,
        answers=payload.answers,
    )

    try:
        producer = admin_service.producer
        future = producer.send(
            QuizAgentTopics.QUIZ_EVALUATE.value,
            value=event.model_dump(mode="json"),
        )
        future.get(timeout=5)
    except Exception as exc:  # noqa: BLE001 - intentionally minimal handling
        return _error(500, f"Failed to publish quiz evaluate event: {exc}")

    return JSONResponse(
        status_code=200,
        content={"message": "Quiz evaluate request accepted and queued"},
    )
