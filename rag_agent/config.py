"""Runtime configuration for LLM, VLM, and embedding models."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


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
    """Configuration for a LiteLLM embedding API call (v2 remote embedding)."""

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
    topic_api_url: str
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
        topic_api_url = _read_optional("BACKEND_API_TOPIC_URL")
        if not bootstrap_servers:
            raise RuntimeError("BACKEND_KAFKA_BOOTSTRAP_SERVERS is required")
        if not topic_api_url:
            raise RuntimeError("BACKEND_API_TOPIC_URL is required")

        client_id = _read_optional("BACKEND_KAFKA_CLIENT_ID") or "rag-service"
        consumer_group_id = f"{client_id}-consumer"
        return cls(
            bootstrap_servers=bootstrap_servers,
            topic_api_url=topic_api_url,
            client_id=client_id,
            security_protocol=_read_optional("BACKEND_KAFKA_SECURITY_PROTOCOL"),
            sasl_mechanism=_read_optional("BACKEND_KAFKA_SASL_MECHANISM"),
            sasl_username=_read_optional("BACKEND_KAFKA_SASL_USERNAME"),
            sasl_password=_read_optional("BACKEND_KAFKA_SASL_PASSWORD"),
            ssl_cafile=_read_optional("BACKEND_KAFKA_SSL_CAFILE"),
            consumer_group_id=consumer_group_id,
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


def build_routed_model(provider: str, model: str) -> str:
    """Build a provider-routed model string used by LiteLLM."""

    provider_clean = provider.strip()
    model_clean = model.strip()
    if not provider_clean:
        raise RuntimeError("Provider must be non-empty")
    if not model_clean:
        raise RuntimeError("Model must be non-empty")
    return f"{provider_clean}/{model_clean}"


def validate_runtime_config(*, provider: str, model: str, scope: str) -> None:
    """Validate required provider/model pair for a model scope."""

    if not provider.strip():
        raise RuntimeError(f"{scope} provider is required")
    if not model.strip():
        raise RuntimeError(f"{scope} model is required")


def get_text_llm_config() -> LLMConfig:
    """Build text model config from environment variables."""

    provider = os.getenv("RAG_TEXT_PROVIDER", "hosted_vllm")
    model = os.getenv("RAG_TEXT_MODEL", "gpt-4o-mini")
    validate_runtime_config(provider=provider, model=model, scope="Text")
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
    validate_runtime_config(provider=provider, model=model, scope="VLM")
    return LLMConfig(
        provider=provider,
        model=model,
        api_base=_read_optional("RAG_VLM_API_BASE"),
        api_key=_read_optional("RAG_VLM_API_KEY"),
        temperature=_read_float("RAG_VLM_TEMPERATURE", 0.1),
        max_tokens=_read_int("RAG_VLM_MAX_TOKENS", 600),
    )


def get_embedding_config() -> EmbeddingConfig:
    """Build embedding model config from environment variables (v2: LiteLLM API)."""

    provider = os.getenv("RAG_EMBEDDING_PROVIDER", "hosted_vllm")
    model = os.getenv("RAG_EMBEDDING_MODEL", "").strip()
    validate_runtime_config(provider=provider, model=model, scope="Embedding")
    if not model:
        raise RuntimeError(
            "RAG_EMBEDDING_MODEL is required for remote embedding API. "
            "Set it in .env.local or environment variables."
        )

    return EmbeddingConfig(
        provider=provider,
        model=model,
        api_base=_read_optional("RAG_EMBEDDING_API_BASE"),
        api_key=_read_optional("RAG_EMBEDDING_API_KEY"),
        max_tokens=_read_int("RAG_EMBEDDING_MAX_TOKENS", 1024),
    )


def get_vlm_batch_size() -> int:
    """Return per-page VLM batch size from environment."""

    batch_size = _read_int("RAG_VLM_BATCH_SIZE", 4)
    if batch_size < 1:
        raise ValueError("RAG_VLM_BATCH_SIZE must be >= 1")
    return batch_size


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
