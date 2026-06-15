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


# ---------------------------------------------------------------------------
# Planner Agent schemas
# ---------------------------------------------------------------------------


class LearnerLevel(str, Enum):
    """Assessed learner proficiency level used by the Planner Agent."""

    NAIVE = "naive"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LearnerProfile(BaseModel):
    """Assessed learner profile derived from query + session context."""

    learner_level: LearnerLevel
    confidence_score: float = Field(ge=0.0, le=1.0)
    level_reasoning: str
    clarification_asked: bool = False

    @field_validator("level_reasoning")
    @classmethod
    def validate_reasoning(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("level_reasoning cannot be empty")
        return value


class LearningPlan(BaseModel):
    """Decomposed task plan specifying which agents to orchestrate."""

    required_agents: List[str]
    parallel_groups: List[List[str]] = Field(default_factory=list)
    depth: str = "conceptual"
    objective: str = ""
    reasoning: str = ""


class PlannerMessage(BaseModel):
    """Kafka message consumed from the init-planner topic."""

    request_id: str
    session_id: str
    user_id: str
    user_query: str
    session_context: List[Any] = Field(default_factory=list)
    available_files: List[str] = Field(default_factory=list)
    user_levels: List[str] = Field(
        default_factory=list,
        description="Pre-provided learner levels; if non-empty, LLM level inference is skipped.",
    )
    schema_version: str = "1.0"

    @field_validator("request_id", "session_id", "user_id", "schema_version")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value

    @field_validator("user_query")
    @classmethod
    def validate_user_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("user_query cannot be empty")
        return value


class ClarifyUserLevelMessage(BaseModel):
    """Kafka message produced to clarify-user-level when learner level is ambiguous."""

    request_id: str
    session_id: str
    clarification_question: str
    context: str = ""
    schema_version: str = "1.0"


class UserClarificationResponse(BaseModel):
    """Kafka message consumed from user-clarification-response."""

    request_id: str
    session_id: str
    response: str
    schema_version: str = "1.0"


class TeachingKafkaInput(BaseModel):
    """Input payload produced by the Planner to the teaching Kafka topic."""

    request_id: str
    user_query: str
    learner_level: str
    learning_path: dict[str, Any] = Field(default_factory=dict)
    rag_material: str = ""
    session_context: List[Any] = Field(default_factory=list)
    schema_version: str = "1.0"

    @field_validator("request_id", "user_query")
    @classmethod
    def validate_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class TeachingKafkaOutput(BaseModel):
    """Output payload consumed from the material-compiled Kafka topic."""

    request_id: str
    teaching_content: str = ""
    learner_level: str = "intermediate"
    sections: List[dict[str, Any]] = Field(default_factory=list)
    status: str
    errors: List[str] = Field(default_factory=list)
    schema_version: str = "1.0"

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"complete", "partial", "failed"}:
            raise ValueError("status must be one of: complete, partial, failed")
        return value


class QuizQuestion(BaseModel):
    """A single quiz question with answer and explanation."""

    id: str
    type: str
    question: str
    options: List[str] = Field(default_factory=list)
    answer: str
    explanation: str = ""


class QuizAgentInput(BaseModel):
    """Input payload produced by the Planner to the quiz Kafka topic."""

    request_id: str
    topic: str
    learner_level: str
    num_questions: int = Field(default=5, ge=1)
    question_types: List[str] = Field(default_factory=lambda: ["mcq", "true_false"])
    rag_material: str = ""
    schema_version: str = "1.0"

    @field_validator("request_id", "topic")
    @classmethod
    def validate_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class QuizAgentOutput(BaseModel):
    """Output payload consumed from the quiz-complete Kafka topic."""

    request_id: str
    questions: List[QuizQuestion] = Field(default_factory=list)
    learner_level: str = "intermediate"
    total_questions: int = Field(default=0, ge=0)
    status: str
    errors: List[str] = Field(default_factory=list)
    schema_version: str = "1.0"

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"complete", "partial", "failed"}:
            raise ValueError("status must be one of: complete, partial, failed")
        return value


# ---------------------------------------------------------------------------
# Planner Agent v2 schemas — used by the 9-node LangGraph workflow
# ---------------------------------------------------------------------------


class PlannerRequestEvent(BaseModel):
    """Inbound Kafka payload consumed from the init-planner topic.

    ``user_level`` carries pre-provided learner levels; when non-empty the
    planner skips LLM level inference entirely (FR-005).
    """

    user_prompt: str
    sid: str
    user_level: List[str] = Field(
        default_factory=list,
        description="Pre-provided learner levels (empty → LLM infers level).",
    )
    file_paths: List[str] = Field(default_factory=list)
    schema_version: str = "1.0"

    @field_validator("user_prompt", "sid")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class LevelInferenceResult(BaseModel):
    """Structured output from the combined level-and-quiz LLM inference call.

    A single LLM call populates both the learner level assessment and whether
    the user's query implies a desire to be tested (FR-024).
    """

    level: LearnerLevel
    confidence: float = Field(ge=0.0, le=1.0)
    quiz_requested: bool = False
    reasoning: str = ""


class ClarifyUserLevelEvent(BaseModel):
    """Kafka event published to clarify-user-level when learner level is ambiguous."""

    request_id: str
    user_prompt: str
    sid: str
    reason: str = ""
    schema_version: str = "1.0"


class TeachingRequestEvent(BaseModel):
    """Kafka event published to the teaching agent for one learner level."""

    request_id: str
    user_prompt: str
    user_level: str
    rag_compiled: str = ""
    sid: str
    schema_version: str = "1.0"

    @field_validator("request_id", "user_prompt", "user_level", "sid")
    @classmethod
    def validate_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class QuizRequestEvent(BaseModel):
    """Kafka event published to the quiz agent after teaching materials are ready."""

    request_id: str
    user_prompt: str
    user_levels: List[str] = Field(default_factory=list)
    teaching_materials: dict[str, str] = Field(default_factory=dict)
    sid: str
    schema_version: str = "1.0"

    @field_validator("request_id", "user_prompt", "sid")
    @classmethod
    def validate_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class WorkflowCompleteEvent(BaseModel):
    """Kafka event published to planner-response when all downstream agents finish."""

    request_id: str
    sid: str
    rag_compiled: str = ""
    teaching_materials: dict[str, str] = Field(default_factory=dict)
    quiz_content: str = ""
    status: str = "complete"
    schema_version: str = "1.0"

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"complete", "partial", "failed"}:
            raise ValueError("status must be one of: complete, partial, failed")
        return value


class PlannerResponse(BaseModel):
    """Final response produced to the planner-response Kafka topic."""

    request_id: str
    session_id: str
    user_id: str
    user_query: str
    learner_level: str
    learning_plan: Optional[dict[str, Any]] = None
    synthesized_content: str = ""
    study_material: str = ""
    quiz: Optional[dict[str, Any]] = None
    status: str
    errors: List[str] = Field(default_factory=list)
    schema_version: str = "1.0"

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"complete", "partial", "failed"}:
            raise ValueError("status must be one of: complete, partial, failed")
        return value

    @field_validator("request_id", "session_id", "user_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value
