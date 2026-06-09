from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/api/v1/topics", tags=["topics"])


class TopicCreateRequest(BaseModel):
    topic_name: str
    num_partitions: int = Field(default=1, ge=1)
    replication_factor: int = Field(default=1, ge=1)
    config: dict[str, str] | None = None

    @field_validator("topic_name")
    @classmethod
    def _validate_topic_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("topic_name cannot be empty")
        return value


class TopicCreateResponse(BaseModel):
    topic_name: str | None = None
    status: str
    message: str


@router.post("", response_model=TopicCreateResponse)
def create_topic(payload: TopicCreateRequest, request: Request) -> JSONResponse:
    admin = request.app.state.kafka_admin
    try:
        status = admin.create_topic(
            topic_name=payload.topic_name,
            num_partitions=payload.num_partitions,
            replication_factor=payload.replication_factor,
            config=payload.config,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if status == "created":
        code = 201
        msg = "Topic created successfully"
    else:
        code = 200
        msg = "Topic already exists"

    body = TopicCreateResponse(
        topic_name=payload.topic_name, status=status, message=msg
    )
    return JSONResponse(status_code=code, content=body.model_dump())
