from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class KafkaSettings(BaseModel):
    bootstrap_servers: str
    startup_retry_count: int = Field(default=5, ge=0)
    startup_retry_timeout_seconds: int = Field(default=2, ge=1)

    client_id: str = "backend-service"
    security_protocol: str | None = None
    sasl_mechanism: str | None = None
    sasl_username: str | None = None
    sasl_password: str | None = None
    ssl_cafile: str | None = None

    @field_validator("bootstrap_servers")
    @classmethod
    def _validate_bootstrap_servers(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("bootstrap_servers cannot be empty")
        return value

    @classmethod
    def from_env(cls, dotenv_path: str = ".env.local") -> "KafkaSettings":
        # .env.local provides local defaults. Existing process env should win.
        if Path(dotenv_path).exists():
            load_dotenv(dotenv_path=dotenv_path, override=False)

        raw_bootstrap = os.getenv("BACKEND_KAFKA_BOOTSTRAP_SERVERS")
        if not raw_bootstrap:
            raise RuntimeError("BACKEND_KAFKA_BOOTSTRAP_SERVERS is required")

        return cls(
            bootstrap_servers=raw_bootstrap,
            startup_retry_count=_read_int("BACKEND_KAFKA_STARTUP_RETRY_COUNT", 5),
            startup_retry_timeout_seconds=_read_int(
                "BACKEND_KAFKA_STARTUP_RETRY_TIMEOUT_SECONDS", 2
            ),
            client_id=os.getenv("BACKEND_KAFKA_CLIENT_ID", "backend-service"),
            security_protocol=_read_optional("BACKEND_KAFKA_SECURITY_PROTOCOL"),
            sasl_mechanism=_read_optional("BACKEND_KAFKA_SASL_MECHANISM"),
            sasl_username=_read_optional("BACKEND_KAFKA_SASL_USERNAME"),
            sasl_password=_read_optional("BACKEND_KAFKA_SASL_PASSWORD"),
            ssl_cafile=_read_optional("BACKEND_KAFKA_SSL_CAFILE"),
        )

    def admin_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": self.client_id,
        }
        if self.security_protocol:
            kwargs["security_protocol"] = self.security_protocol
        if self.sasl_mechanism:
            kwargs["sasl_mechanism"] = self.sasl_mechanism
        if self.sasl_username:
            kwargs["sasl_plain_username"] = self.sasl_username
        if self.sasl_password:
            kwargs["sasl_plain_password"] = self.sasl_password
        if self.ssl_cafile:
            kwargs["ssl_cafile"] = self.ssl_cafile
        return kwargs


class ComposeSettings(BaseModel):
    kafka_service_name: str = "kafka"
    kafka_ui_service_name: str = "kafka-ui"
    kafka_ui_image: str = "provectuslabs/kafka-ui:latest"
    kafka_bootstrap_reference: str = "kafka:9092"
    kafka_ui_url: str = "http://localhost:8080"


def _read_optional(name: str) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    cleaned = raw.strip()
    return cleaned or None


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
