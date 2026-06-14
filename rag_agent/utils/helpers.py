"""Environment extraction helpers for the RAG worker runtime.

This module intentionally keeps a small surface area: env-to-dict helper
functions only. Classes, validators, and complex config abstraction are
deferred to follow-up TODO work.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_dotenv(dotenv_path: str = ".env.local") -> None:
    if Path(dotenv_path).exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)


def build_routed_model(provider: str, model: str) -> str:
    """Build a provider-routed model string used by LiteLLM."""

    return f"{provider.strip()}/{model.strip()}"


def get_text_llm_config() -> dict[str, object]:
    """Build text model config from environment variables."""

    _load_dotenv()
    provider = os.getenv("RAG_TEXT_PROVIDER", "hosted_vllm")
    model = os.getenv("RAG_TEXT_MODEL", "gpt-4o-mini")
    return {
        "provider": provider,
        "model": model,
        "routed_model": build_routed_model(provider, model),
        "api_base": _read_optional("RAG_TEXT_API_BASE"),
        "api_key": _read_optional("RAG_TEXT_API_KEY"),
        "temperature": _read_float("RAG_TEXT_TEMPERATURE", 0.2),
        "max_tokens": _read_int("RAG_TEXT_MAX_TOKENS", 1800),
    }


def get_vlm_config() -> dict[str, object]:
    """Build vision model config from environment variables."""

    _load_dotenv()
    provider = os.getenv("RAG_VLM_PROVIDER", "hosted_vllm")
    model = os.getenv("RAG_VLM_MODEL", "gpt-4o-mini")
    batch_size = os.getenv("RAG_VLM_BATCH_SIZE", "4")
    return {
        "provider": provider,
        "model": model,
        "routed_model": build_routed_model(provider, model),
        "api_base": _read_optional("RAG_VLM_API_BASE"),
        "api_key": _read_optional("RAG_VLM_API_KEY"),
        "temperature": _read_float("RAG_VLM_TEMPERATURE", 0.1),
        "max_tokens": _read_int("RAG_VLM_MAX_TOKENS", 600),
        "batch_size": max(1, _read_int("RAG_VLM_BATCH_SIZE", 4)),
    }
    

def get_embedding_config() -> dict[str, object]:
    """Build embedding model config from environment variables."""

    _load_dotenv()
    provider = os.getenv("RAG_EMBEDDING_PROVIDER", "hosted_vllm")
    model = os.getenv("RAG_EMBEDDING_MODEL", "").strip()
    if not model:
        raise RuntimeError("RAG_EMBEDDING_MODEL is required")
    return {
        "provider": provider,
        "model": model,
        "routed_model": build_routed_model(provider, model),
        "api_base": _read_optional("RAG_EMBEDDING_API_BASE"),
        "api_key": _read_optional("RAG_EMBEDDING_API_KEY"),
        "max_tokens": _read_int("RAG_EMBEDDING_MAX_TOKENS", 1024),
    }

def get_kafka_runtime_config() -> dict[str, object]:
    """Build Kafka runtime settings directly from environment values."""

    _load_dotenv()
    bootstrap_servers = _read_optional("BACKEND_KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap_servers:
        raise RuntimeError("BACKEND_KAFKA_BOOTSTRAP_SERVERS is required")

    client_id = "rag-service"
    consumer_group_id = f"{client_id}-consumer"
    return {
        "bootstrap_servers": bootstrap_servers,
        "client_id": client_id,
        "security_protocol": _read_optional("BACKEND_KAFKA_SECURITY_PROTOCOL"),
        "sasl_mechanism": _read_optional("BACKEND_KAFKA_SASL_MECHANISM"),
        "sasl_username": _read_optional("BACKEND_KAFKA_SASL_USERNAME"),
        "sasl_password": _read_optional("BACKEND_KAFKA_SASL_PASSWORD"),
        "ssl_cafile": _read_optional("BACKEND_KAFKA_SSL_CAFILE"),
        "consumer_group_id": consumer_group_id,
        "poll_timeout_ms": _read_int("BACKEND_KAFKA_POLL_TIMEOUT_MS", 1000),
    }


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


def apply_kafka_security_options(
    kwargs: dict[str, str | int | bool], config: dict[str, object]
) -> None:
    security_protocol = config.get("security_protocol")
    sasl_mechanism = config.get("sasl_mechanism")
    sasl_username = config.get("sasl_username")
    sasl_password = config.get("sasl_password")
    ssl_cafile = config.get("ssl_cafile")

    if isinstance(security_protocol, str) and security_protocol:
        kwargs["security_protocol"] = security_protocol
    if isinstance(sasl_mechanism, str) and sasl_mechanism:
        kwargs["sasl_mechanism"] = sasl_mechanism
    if isinstance(sasl_username, str) and sasl_username:
        kwargs["sasl_plain_username"] = sasl_username
    if isinstance(sasl_password, str) and sasl_password:
        kwargs["sasl_plain_password"] = sasl_password
    if isinstance(ssl_cafile, str) and ssl_cafile:
        kwargs["ssl_cafile"] = ssl_cafile
