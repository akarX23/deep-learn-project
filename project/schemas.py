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


class UserRequest(BaseModel):
    """Inbound user request routed from Frontend to backend services."""

    user_prompt: str
    user_level: List[str]
    sid: str


class StreamTokensEventBody(BaseModel):
    """Kafka payload for the ``stream-tokens`` topic, forwarded to Socket.IO.

    ``data`` is a generic dict so any producing agent can attach its own payload
    without requiring a per-agent schema variant.
    """

    from_service: str
    sid: str
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Planner Agent schemas
# ---------------------------------------------------------------------------


class PlannerRequestEvent(BaseModel):
    """Kafka event published to the planner topic for a user-initiated request.

    Carries absolute file paths so the planner can locate uploaded documents.
    No per-file metadata is included in this iteration.
    """

    user_prompt: str
    user_level: List[str] = Field(default_factory=list)
    sid: str
    file_paths: List[str] = Field(default_factory=list)


class UserLevelEnum(str, Enum):
    """Knowledge level inferred or provided for a learning request."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LevelInferenceResult(BaseModel):
    """Structured LLM output classifying user level and quiz intent."""

    level: UserLevelEnum
    confidence: float
    quiz_requested: bool = False


class TeachingRequestEvent(BaseModel):
    """Planner -> teaching agent event (one per user level)."""

    request_id: str
    user_prompt: str
    user_level: str
    rag_compiled: str = ""
    sid: str


class QuizRequestEvent(BaseModel):
    """Planner -> quiz agent event."""

    request_id: str
    user_prompt: str
    user_levels: List[str] = Field(default_factory=list)
    teaching_materials: dict[str, str] = Field(default_factory=dict)
    sid: str


class ClarifyUserLevelEvent(BaseModel):
    """Planner -> frontend event when user level cannot be confidently inferred."""

    request_id: str
    user_prompt: str
    sid: str
    reason: str = ""


class WorkflowCompleteEvent(BaseModel):
    """Planner -> frontend event emitted when a workflow finishes."""

    request_id: str
    sid: str
    rag_compiled: str = ""
    teaching_materials: dict[str, str] = Field(default_factory=dict)
    quiz_content: str = ""


class TeachingCompletionEvent(BaseModel):
    """Teaching agent -> planner completion event (one per user level)."""

    request_id: str
    sid: str
    user_level: str
    content: str = ""

    @field_validator("request_id", "user_level")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class QuizCompletionEvent(BaseModel):
    """Quiz agent -> planner completion event."""

    request_id: str
    sid: str
    quiz_content: str = ""

    @field_validator("request_id")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
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


# class TeachingCompletionEvent(BaseModel):
#     """Kafka completion payload published by the Teaching Agent to 'teaching-complete'."""

#     request_id: str
#     session_ctx: dict[str, Any]
#     topic: str
#     output_mode: str
#     status: str
#     content: Optional[TeachingContent] = None
#     tokens_used: int = Field(default=0, ge=0)
#     model: str
#     started_at: str
#     completed_at: str
#     duration_ms: int = Field(default=0, ge=0)
#     errors: List[str] = Field(default_factory=list)
#     source: str = "teaching-agent"

#     @field_validator("request_id", "topic", "output_mode", "model", "started_at", "completed_at")
#     @classmethod
#     def validate_non_empty_fields(cls, value: str) -> str:
#         if not value.strip():
#             raise ValueError("value cannot be empty")
#         return value

# ---------------------------------------------------------------------------
# Quiz Agent schemas
# ---------------------------------------------------------------------------


class QuestionType(str, Enum):
    """Discriminator for question variants in a generated quiz."""

    MCQ_SINGLE = "mcq-single"
    MCQ_MULTI = "mcq-multi"
    DESCRIPTIVE = "descriptive"


class MCQOption(BaseModel):
    """A single selectable option within an MCQ question."""

    id: str
    text: str
    is_correct: bool
    explanation: str  # Why correct or why incorrect / why it should have been selected


class UIHints(BaseModel):
    """Rendering directives consumed by the frontend quiz UI."""

    mcq_single_input: str = "radio"
    mcq_multi_input: str = "checkbox"
    mcq_multi_hint_text: str = "Select all that apply"
    descriptive_target_words: int = 150
    descriptive_soft_warning_below: int = 80


class QuizMetadata(BaseModel):
    """Quiz-level metadata attached to every generated Quiz; read by the UI."""

    question_type_counts: dict  # {"mcq-single": n, "mcq-multi": n, "descriptive": n}
    total_questions: int = Field(ge=1)
    max_score: int = Field(ge=1)
    mcq_max_score: int = Field(ge=0)
    descriptive_max_score: int = Field(ge=0)
    ui_hints: UIHints = Field(default_factory=UIHints)


class Question(BaseModel):
    """A single quiz question with all fields needed for rendering and grading."""

    id: str
    type: QuestionType
    prompt: str
    sub_concept: str
    max_points: int = Field(ge=1, default=1)
    # MCQ fields
    options: List[MCQOption] = Field(default_factory=list)
    topic_deep_dive: Optional[str] = None
    # Descriptive field
    rubric: List[str] = Field(default_factory=list)

    @field_validator("prompt", "sub_concept")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class Quiz(BaseModel):
    """A generated collection of questions for a single teaching-content item."""

    quiz_id: str
    topic: str
    questions: List[Question] = Field(min_length=1)
    metadata: QuizMetadata


class SubmittedAnswer(BaseModel):
    """A learner's response to one question."""

    question_id: str
    selected_option_ids: List[str] = Field(default_factory=list)  # MCQ
    free_text: str = ""  # Descriptive


class PerOptionExplanation(BaseModel):
    """Explanation panel for a single mishandled MCQ option on the results screen."""

    option_id: str
    explanation_type: str  # "wrong-selected" | "missed-correct"
    explanation: str


class QuestionResult(BaseModel):
    """Per-question scoring outcome returned in QuizResult."""

    question_id: str
    score: float = Field(ge=0)
    max_score: int = Field(ge=0)
    # MCQ single
    is_correct: Optional[bool] = None
    wrong_answer_explanation: Optional[str] = None
    # MCQ multi / single on wrong
    topic_deep_dive: Optional[str] = None
    per_option_explanations: List[PerOptionExplanation] = Field(default_factory=list)
    # Descriptive
    model_answer: Optional[str] = None
    feedback: Optional[str] = None


class QuizResult(BaseModel):
    """Aggregated evaluation outcome returned by QuizAgent.evaluate()."""

    overall_score: float = Field(ge=0)
    max_score: int = Field(ge=1)
    overall_percentage: float = Field(ge=0, le=100)
    mcq_subtotal: float = Field(ge=0)
    descriptive_subtotal: float = Field(ge=0)
    question_results: List[QuestionResult] = Field(default_factory=list)
    weak_sub_concepts: List[str] = Field(default_factory=list)
    recommended_action: str  # "re-teach" | "practice-more" | "advance"

    @field_validator("recommended_action")
    @classmethod
    def validate_recommended_action(cls, value: str) -> str:
        if value not in {"re-teach", "practice-more", "advance"}:
            raise ValueError(
                "recommended_action must be one of: re-teach, practice-more, advance"
            )
        return value


class QuizAgentMetadata(BaseModel):
    """Audit record for a Quiz Agent response."""

    topic: str
    tokens_used: int = Field(ge=0)
    model: str


class QuizAgentInput(BaseModel):
    """Input payload sent to QuizAgent.generate()."""

    topic: str
    teaching_content: str
    mcq_single_count: int = Field(default=5, ge=1)
    mcq_multi_count: int = Field(default=3, ge=1)

    @field_validator("topic", "teaching_content")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class QuizAgentOutput(BaseModel):
    """Output payload returned by both phases of the Quiz Agent."""

    status: str  # "generated" | "evaluated" | "error"
    quiz: Optional[Quiz] = None
    result: Optional[QuizResult] = None
    metadata: Optional[QuizAgentMetadata] = None
    errors: List[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"generated", "evaluated", "error"}:
            raise ValueError("status must be one of: generated, evaluated, error")
        return value
