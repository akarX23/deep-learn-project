"""Shared schemas for agent communication contracts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

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
        UUID(value)
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


# ---------------------------------------------------------------------------
# UI Frontend websocket schemas
# ---------------------------------------------------------------------------


class ConnectionLifecycleState(str, Enum):
    """WebSocket connection lifecycle states for the frontend."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


class DiagnosticSeverity(str, Enum):
    """Severity level for frontend diagnostic records."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class EventType(str, Enum):
    """Supported websocket event types for frontend routing."""

    TEACHING_TOKEN = "teaching.token"
    TEACHING_COMPLETE = "teaching.complete"
    PLANNER_STATUS = "planner.status"
    QUIZ_STARTED = "quiz.started"
    QUIZ_QUESTION = "quiz.question"
    QUIZ_FEEDBACK = "quiz.feedback"
    QUIZ_COMPLETED = "quiz.completed"
    EVALUATION_RESULT = "evaluation.result"
    SYSTEM_ERROR = "system.error"


class QuizPhase(str, Enum):
    """Frontend quiz lifecycle phases."""

    IDLE = "idle"
    STARTED = "started"
    QUESTION = "question"
    FEEDBACK = "feedback"
    COMPLETED = "completed"


class TeachingTokenPayload(BaseModel):
    """Payload for per-token teaching stream updates."""

    stream_id: str
    sequence: int = Field(ge=0)
    token: str
    is_final: bool = False

    @field_validator("stream_id")
    @classmethod
    def validate_stream_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("stream_id cannot be empty")
        return value

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        if value is None:
            raise ValueError("token cannot be null")
        return value


class TeachingCompletePayload(BaseModel):
    """Payload for the final teaching stream event."""

    stream_id: str
    final_text: str = ""
    tokens_used: int = Field(default=0, ge=0)

    @field_validator("stream_id")
    @classmethod
    def validate_stream_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("stream_id cannot be empty")
        return value


class PlannerStatusPayload(BaseModel):
    """Payload for planner progress updates."""

    stage: str
    message: str
    progress_percent: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("stage", "message")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class QuizEventPayload(BaseModel):
    """Payload for quiz lifecycle events."""

    quiz_id: str
    phase: QuizPhase
    question_text: Optional[str] = None
    choices: List[str] = Field(default_factory=list)
    feedback: Optional[str] = None
    score: Optional[float] = None

    @field_validator("quiz_id")
    @classmethod
    def validate_quiz_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("quiz_id cannot be empty")
        return value


class EvaluationResultPayload(BaseModel):
    """Payload for evaluation result events."""

    evaluation_id: str
    summary: str
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    @field_validator("evaluation_id", "summary")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class SystemErrorPayload(BaseModel):
    """Payload for system-level websocket error events."""

    code: str
    message: str
    retryable: bool = False

    @field_validator("code", "message")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class AgentEvent(BaseModel):
    """Normalized websocket event envelope consumed by the frontend."""

    schema_version: str = "1.0"
    event_id: str
    event_type: EventType
    source_agent: str
    session_id: str
    request_id: Optional[str] = None
    timestamp: datetime
    payload: dict = Field(default_factory=dict)
    status: Optional[str] = None
    error_message: Optional[str] = None

    @field_validator("event_id", "source_agent", "session_id", "schema_version")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class ConnectionState(BaseModel):
    """Frontend websocket connection state model."""

    state: ConnectionLifecycleState
    retry_count: int = Field(default=0, ge=0)
    last_error: Optional[str] = None
    last_change_ts: datetime


class ChatStreamState(BaseModel):
    """Aggregated state for teaching text stream rendering."""

    stream_id: Optional[str] = None
    rendered_text: str = ""
    last_sequence: int = -1
    is_complete: bool = False

    @field_validator("last_sequence")
    @classmethod
    def validate_last_sequence(cls, value: int) -> int:
        if value < -1:
            raise ValueError("last_sequence cannot be less than -1")
        return value


class PlannerStatusState(BaseModel):
    """Current planner status presented in the frontend status panel."""

    stage: str = ""
    message: str = ""
    progress_percent: Optional[int] = Field(default=None, ge=0, le=100)
    updated_at: datetime


class QuizState(BaseModel):
    """Frontend quiz interaction state."""

    quiz_id: Optional[str] = None
    phase: QuizPhase = QuizPhase.IDLE
    current_question: Optional[str] = None
    choices: List[str] = Field(default_factory=list)
    feedback: Optional[str] = None
    score: Optional[float] = None


class EvaluationState(BaseModel):
    """Latest and historical evaluation summary state."""

    latest_summary: Optional[str] = None
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    history_count: int = Field(default=0, ge=0)


class DiagnosticEvent(BaseModel):
    """Structured diagnostic entry for invalid or unknown websocket events."""

    severity: DiagnosticSeverity
    reason: str
    event_excerpt: str = ""
    recorded_at: datetime

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason cannot be empty")
        return value


class FrontendSession(BaseModel):
    """Top-level frontend runtime session state."""

    session_id: str
    active_tab: str
    connection_state: ConnectionState
    chat_state: ChatStreamState
    quiz_state: QuizState
    evaluation_state: EvaluationState
    planner_status: PlannerStatusState
    diagnostics: List[DiagnosticEvent] = Field(default_factory=list)

    @field_validator("session_id", "active_tab")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class SimulationScenario(BaseModel):
    """Deterministic scenario definition for mock websocket playback."""

    scenario_id: str
    name: str
    events: List[AgentEvent] = Field(default_factory=list)
    speed_multiplier: float = Field(default=1.0, gt=0)

    @field_validator("scenario_id", "name")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value
