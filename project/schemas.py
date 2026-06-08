"""Shared schemas for agent communication contracts."""

from __future__ import annotations

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
