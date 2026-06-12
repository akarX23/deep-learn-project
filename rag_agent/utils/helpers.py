"""Consolidated helpers, configuration, and LLM call utilities for the RAG agent.

This module merges responsibilities from the former helpers.py, config.py, and
llm_client.py into a single utility module as part of the simplification phase.

Consolidated from:
- rag_agent/helpers.py  (pure helper functions)
- rag_agent/config.py   (LLM/Kafka config dataclasses and env-read accessors)

LLM call wrappers live in rag_agent/utils/llm_client.py.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pure helper functions (formerly rag_agent/helpers.py)
# ---------------------------------------------------------------------------


def serialize_table_to_markdown(table_matrix: list[list[object]]) -> str:
    """Convert a 2D table matrix to a markdown table."""

    if not table_matrix:
        return ""
    rows = [["" if cell is None else str(cell).strip() for cell in row] for row in table_matrix]
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else []
    sep = ["---"] * len(header)

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in body:
        padded = row + [""] * max(0, len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(lines)


def assemble_page_content(text: str, tables: list[str], image_descriptions: list[str]) -> str:
    """Assemble text, tables, and image descriptions for one page."""

    sections: list[str] = []
    if text and text.strip():
        sections.append(text.strip())
    if tables:
        sections.append("\n\n".join(t for t in tables if t.strip()))
    if image_descriptions:
        image_block = "\n".join(f"- {item.strip()}" for item in image_descriptions if item.strip())
        if image_block:
            sections.append("Image Notes:\n" + image_block)
    return "\n\n".join(section for section in sections if section.strip())


def build_compilation_context(retained_pages: list[dict[str, Any]]) -> str:
    """Build labeled context text from retained pages for final compilation."""

    chunks: list[str] = []
    for page in retained_pages:
        content = str(page.get("content", "")).strip()
        if not content:
            continue
        file_name = str(page.get("file_name", "unknown"))
        page_number = int(page.get("page_number", 0))
        relevance_score = float(page.get("relevance_score", 0.0))
        chunks.append(
            f"### Source: {file_name} | Page {page_number} | Score {relevance_score:.3f}\n"
            f"{content}"
        )
    return "\n\n".join(chunks)


def cosine_similarity(vec_a: Iterable[float], vec_b: Iterable[float]) -> float:
    """Compute cosine similarity without external math dependencies."""

    a = list(vec_a)
    b = list(vec_b)
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


# ---------------------------------------------------------------------------
# Configuration dataclasses (formerly rag_agent/config.py)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for a LiteLLM model call."""

    model: str
    provider: str = "hosted_vllm"
    api_base: str | None = None
    api_key: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1200

    @property
    def routed_model(self) -> str:
        return build_routed_model(self.provider, self.model)


@dataclass(frozen=True)
class EmbeddingConfig:
    """Configuration for a LiteLLM embedding API call."""

    model: str
    provider: str = "hosted_vllm"
    api_base: str | None = None
    api_key: str | None = None
    max_tokens: int | None = None

    @property
    def routed_model(self) -> str:
        return build_routed_model(self.provider, self.model)


@dataclass(frozen=True)
class KafkaRuntimeConfig:
    """Runtime configuration for Kafka-backed RAG service behavior."""

    bootstrap_servers: str
    client_id: str = "rag-service"
    security_protocol: str | None = None
    sasl_mechanism: str | None = None
    sasl_username: str | None = None
    sasl_password: str | None = None
    ssl_cafile: str | None = None
    consumer_group_id: str = "rag-service"
    poll_timeout_ms: int = 1000

    @classmethod
    def from_env(cls, dotenv_path: str = ".env.local") -> "KafkaRuntimeConfig":
        """Build Kafka runtime config from backend-compatible environment variables."""

        if Path(dotenv_path).exists():
            load_dotenv(dotenv_path=dotenv_path, override=False)

        bootstrap_servers = _read_optional("BACKEND_KAFKA_BOOTSTRAP_SERVERS")
        if not bootstrap_servers:
            raise RuntimeError("BACKEND_KAFKA_BOOTSTRAP_SERVERS is required")

        client_id = "rag-service"
        consumer_group_id = f"{client_id}-consumer"
        return cls(
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
            security_protocol=_read_optional("BACKEND_KAFKA_SECURITY_PROTOCOL"),
            sasl_mechanism=_read_optional("BACKEND_KAFKA_SASL_MECHANISM"),
            sasl_username=_read_optional("BACKEND_KAFKA_SASL_USERNAME"),
            sasl_password=_read_optional("BACKEND_KAFKA_SASL_PASSWORD"),
            ssl_cafile=_read_optional("BACKEND_KAFKA_SSL_CAFILE"),
            consumer_group_id=consumer_group_id,
            poll_timeout_ms=_read_int("BACKEND_KAFKA_POLL_TIMEOUT_MS", 1000),
        )

    def producer_kwargs(self) -> dict[str, str]:
        """Return kafka-python kwargs for the producer."""

        kwargs: dict[str, str] = {
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": self.client_id,
        }
        _apply_security_options(kwargs, self)
        return kwargs

    def consumer_kwargs(self) -> dict[str, str | int | bool]:
        """Return kafka-python kwargs for the consumer."""

        kwargs: dict[str, str | int | bool] = {
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": self.client_id,
            "group_id": self.consumer_group_id,
            "enable_auto_commit": True,
            "auto_offset_reset": "earliest",
        }
        _apply_security_options(kwargs, self)
        return kwargs


# ---------------------------------------------------------------------------
# Config accessor functions (formerly rag_agent/config.py)
# ---------------------------------------------------------------------------


def build_routed_model(provider: str, model: str) -> str:
    """Build a provider-routed model string used by LiteLLM."""

    provider_clean = provider.strip()
    model_clean = model.strip()
    if not provider_clean:
        raise RuntimeError("Provider must be non-empty")
    if not model_clean:
        raise RuntimeError("Model must be non-empty")
    return f"{provider_clean}/{model_clean}"


def get_text_llm_config() -> LLMConfig:
    """Build text model config from environment variables."""

    provider = os.getenv("RAG_TEXT_PROVIDER", "hosted_vllm")
    model = os.getenv("RAG_TEXT_MODEL", "gpt-4o-mini")
    return LLMConfig(
        provider=provider,
        model=model,
        api_base=_read_optional("RAG_TEXT_API_BASE"),
        api_key=_read_optional("RAG_TEXT_API_KEY"),
        temperature=_read_float("RAG_TEXT_TEMPERATURE", 0.2),
        max_tokens=_read_int("RAG_TEXT_MAX_TOKENS", 1800),
    )


def get_vlm_config() -> LLMConfig:
    """Build vision model config from environment variables."""

    provider = os.getenv("RAG_VLM_PROVIDER", "hosted_vllm")
    model = os.getenv("RAG_VLM_MODEL", "gpt-4o-mini")
    return LLMConfig(
        provider=provider,
        model=model,
        api_base=_read_optional("RAG_VLM_API_BASE"),
        api_key=_read_optional("RAG_VLM_API_KEY"),
        temperature=_read_float("RAG_VLM_TEMPERATURE", 0.1),
        max_tokens=_read_int("RAG_VLM_MAX_TOKENS", 600),
    )


def get_vlm_batch_size() -> int:
    """Return per-page VLM batch size from environment."""

    return max(1, _read_int("RAG_VLM_BATCH_SIZE", 4))


def get_embedding_config() -> EmbeddingConfig:
    """Build embedding model config from environment variables."""

    provider = os.getenv("RAG_EMBEDDING_PROVIDER", "hosted_vllm")
    model = os.getenv("RAG_EMBEDDING_MODEL", "").strip()
    # TODO: Add validation that model is non-empty before constructing config
    return EmbeddingConfig(
        provider=provider,
        model=model,
        api_base=_read_optional("RAG_EMBEDDING_API_BASE"),
        api_key=_read_optional("RAG_EMBEDDING_API_KEY"),
        max_tokens=_read_int("RAG_EMBEDDING_MAX_TOKENS", 1024),
    )


def get_embedding_model_name() -> str:
    """Return the local embedding model name from environment."""

    return os.getenv("RAG_EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")


# ---------------------------------------------------------------------------
# Internal env-read helpers
# ---------------------------------------------------------------------------


def _read_optional(name: str) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def _read_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float") from exc


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _apply_security_options(
    kwargs: dict[str, str | int | bool], config: KafkaRuntimeConfig
) -> None:
    if config.security_protocol:
        kwargs["security_protocol"] = config.security_protocol
    if config.sasl_mechanism:
        kwargs["sasl_mechanism"] = config.sasl_mechanism
    if config.sasl_username:
        kwargs["sasl_plain_username"] = config.sasl_username
    if config.sasl_password:
        kwargs["sasl_plain_password"] = config.sasl_password
    if config.ssl_cafile:
        kwargs["ssl_cafile"] = config.ssl_cafile
