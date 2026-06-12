"""Shared schemas for agent communication contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class PageExtractionStatus(str, Enum):
    """Per-page extraction result status."""

    SUCCESS = "SUCCESS"
    SKIPPED_IRRELEVANT = "SKIPPED_IRRELEVANT"
    FAILED_EXTRACTION = "FAILED_EXTRACTION"


class RAGAgentInput(BaseModel):
    """Input payload for the RAG retrieval agent."""

    request_id: str
    user_prompt: str
    file_paths: List[str] = Field(min_length=1)
    include_tables: bool = True
    include_images: bool = True
    relevance_threshold: float = 0.6
    schema_version: str = "1.0"

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id cannot be empty")
        return value

    @field_validator("user_prompt", "schema_version")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value

    @field_validator("relevance_threshold")
    @classmethod
    def validate_threshold(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("relevance_threshold must be within [0.0, 1.0]")
        return value


class ExtractedPage(BaseModel):
    """Audit entry for a processed PDF page."""

    file_name: str
    page_number: int = Field(ge=1)
    relevance_score: float = Field(ge=0.0, le=1.0)
    status: PageExtractionStatus
    ocr_used: bool = False
    errors: List[str] = Field(default_factory=list)


class RAGAgentOutput(BaseModel):
    """Output payload returned to the planner agent."""

    request_id: str
    user_prompt: str
    schema_version: str
    compiled_material: str
    extracted_pages: List[ExtractedPage] = Field(default_factory=list)
    total_pages_processed: int = 0
    total_pages_included: int = 0
    errors: List[str] = Field(default_factory=list)
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"complete", "partial", "failed"}:
            raise ValueError("status must be one of: complete, partial, failed")
        return value

    @field_validator("compiled_material")
    @classmethod
    def validate_compiled_material(cls, value: str) -> str:
        if value is None:
            raise ValueError("compiled_material cannot be null")
        return value

    @field_validator("total_pages_included")
    @classmethod
    def validate_counts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("total_pages_included cannot be negative")
        return value


class RAGRequestEvent(BaseModel):
    """Kafka request payload for the RAG service."""

    request_id: str
    session_ctx: dict[str, Any]
    user_request: str
    file_paths: List[str] = Field(min_length=1)
    created_at: str | None = None
    source: str | None = None

    @field_validator("request_id", "user_request")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value

    @field_validator("session_ctx")
    @classmethod
    def validate_session_ctx(cls, value: dict[str, Any]) -> dict[str, Any]:
        if value is None:
            raise ValueError("session_ctx cannot be null")
        return value


class RAGCompletionEvent(BaseModel):
    """Kafka completion payload emitted by the RAG service."""

    request_id: str
    session_ctx: dict[str, Any]
    user_prompt: str
    compiled_material: str = ""
    status: str
    errors: List[str] = Field(default_factory=list)
    total_pages_processed: int = Field(default=0, ge=0)
    total_pages_included: int = Field(default=0, ge=0)
    started_at: str
    completed_at: str
    duration_ms: int = Field(ge=0)
    source: str = "rag-service"

    @field_validator(
        "request_id", "user_prompt", "status", "started_at", "completed_at"
    )
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value

    @field_validator("status")
    @classmethod
    def validate_completion_status(cls, value: str) -> str:
        if value not in {"complete", "partial", "failed"}:
            raise ValueError("status must be one of: complete, partial, failed")
        return value

    @field_validator("compiled_material")
    @classmethod
    def validate_material(cls, value: str) -> str:
        if value is None:
            raise ValueError("compiled_material cannot be null")
        return value


class RequestLifecycleLogEntry(BaseModel):
    """Structured lifecycle log record for request processing."""

    request_id: str
    stage: str
    level: str = "INFO"
    message: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("request_id", "stage", "level", "message")
    @classmethod
    def validate_log_fields(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class TopicPresenceCheckResult(BaseModel):
    """Result of checking Kafka metadata for required topics."""

    required_topics: List[str]
    existing_topics: List[str]
    missing_topics: List[str]
    warning_message: str | None = None


class WorkerRuntimeState(BaseModel):
    """Runtime state for the standalone RAG worker process."""

    running: bool
    stop_event_set: bool
    poll_thread_alive: bool
    startup_topic_check_complete: bool
    startup_topic_check_warnings: List[str] = Field(default_factory=list)

# ---------------------------------------------------------------------------
# Backend Service schemas
# ---------------------------------------------------------------------------


class StartupTopicBootstrapResult(BaseModel):
    """Outcome of Kafka topic bootstrap during service startup."""

    created: List[str] = Field(
        default_factory=list,
        description="Topic names successfully created during this startup pass",
    )
    already_existed: List[str] = Field(
        default_factory=list,
        description="Topic names that already existed (idempotent — not errors)",
    )
    errors: List[tuple[str, str]] = Field(
        default_factory=list,
        description="List of (topic_name, error_message) tuples for non-fatal errors",
    )


# ---------------------------------------------------------------------------
# Teaching Agent schemas
# ---------------------------------------------------------------------------


class OutputMode(str, Enum):
    """Learner level that governs explanation structure, vocabulary, and token ceiling."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TeachingAgentInput(BaseModel):
    """Input payload received from the Planner Agent."""

    topic: str
    output_mode: OutputMode
    context: str = ""

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("topic cannot be empty")
        return value


class TeachingContent(BaseModel):
    """Structured explanation payload returned in a successful Teaching Agent response."""

    explanation: str
    diagram: Optional[str] = None
    notes: str
    example: Optional[str] = None

    @field_validator("explanation", "notes")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class TeachingMetadata(BaseModel):
    """Audit record for the Teaching Agent response."""

    topic: str
    tokens_used: int = Field(ge=0)
    model: str

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("model cannot be empty")
        return value


class TeachingAgentOutput(BaseModel):
    """Output payload returned by the Teaching Agent to the Planner Agent."""

    status: str
    output_mode: OutputMode
    content: Optional[TeachingContent] = None
    metadata: TeachingMetadata

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"ok", "error"}:
            raise ValueError("status must be 'ok' or 'error'")
        return value
