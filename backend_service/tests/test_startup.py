from __future__ import annotations

from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient

from backend_service.app.config import ComposeSettings, KafkaSettings
from backend_service.app.main import create_app


def test_settings_env_precedence_over_dotenv(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "BACKEND_KAFKA_BOOTSTRAP_SERVERS=file-kafka:9092\n"
        "BACKEND_KAFKA_STARTUP_RETRY_COUNT=7\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("BACKEND_KAFKA_BOOTSTRAP_SERVERS", "env-kafka:9092")
    settings = KafkaSettings.from_env(dotenv_path=str(env_file))

    assert settings.bootstrap_servers == "env-kafka:9092"
    assert settings.startup_retry_count == 7


def test_settings_missing_bootstrap_servers_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BACKEND_KAFKA_BOOTSTRAP_SERVERS", raising=False)
    with pytest.raises(
        RuntimeError, match="BACKEND_KAFKA_BOOTSTRAP_SERVERS is required"
    ):
        KafkaSettings.from_env(dotenv_path=str(Path("/tmp/does-not-exist.env")))


def test_startup_retry_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAdmin:
        attempts = 0

        def __init__(self, settings: KafkaSettings) -> None:
            self.settings = settings

        def connect(self) -> None:
            type(self).attempts += 1
            if type(self).attempts < 3:
                raise RuntimeError("not ready")

        def close(self) -> None:
            return None

    monkeypatch.setattr("backend_service.app.main.time.sleep", lambda _seconds: None)

    settings = KafkaSettings(
        bootstrap_servers="kafka:9092",
        startup_retry_count=3,
        startup_retry_timeout_seconds=1,
    )
    app = create_app(settings=settings, admin_factory=FakeAdmin)

    with TestClient(app):
        pass

    assert FakeAdmin.attempts == 3


def test_shutdown_lifecycle_invokes_admin_close() -> None:
    class CloseTrackingAdmin:
        closed = False

        def __init__(self, settings: KafkaSettings) -> None:
            self.settings = settings

        def connect(self) -> None:
            return None

        def close(self) -> None:
            type(self).closed = True

    settings = KafkaSettings(
        bootstrap_servers="kafka:9092",
        startup_retry_count=0,
        startup_retry_timeout_seconds=1,
    )
    app = create_app(settings=settings, admin_factory=CloseTrackingAdmin)

    with TestClient(app):
        pass

    assert CloseTrackingAdmin.closed is True


def test_startup_retry_exhausted_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class AlwaysFailAdmin:
        attempts = 0

        def __init__(self, settings: KafkaSettings) -> None:
            self.settings = settings

        def connect(self) -> None:
            type(self).attempts += 1
            raise RuntimeError("still down")

        def close(self) -> None:
            return None

    monkeypatch.setattr("backend_service.app.main.time.sleep", lambda _seconds: None)

    settings = KafkaSettings(
        bootstrap_servers="kafka:9092",
        startup_retry_count=1,
        startup_retry_timeout_seconds=1,
    )
    app = create_app(settings=settings, admin_factory=AlwaysFailAdmin)

    with pytest.raises(RuntimeError, match="Kafka startup connection failed"):
        with TestClient(app):
            pass

    assert AlwaysFailAdmin.attempts == 2


def test_compose_configuration_defaults() -> None:
    compose = ComposeSettings()
    assert compose.kafka_service_name == "kafka"
    assert compose.kafka_image == "apache/kafka:4.2.1"
    assert compose.kafka_ui_service_name == "kafka-ui"
    assert compose.kafka_ui_image == "provectuslabs/kafka-ui:latest"
    assert compose.kafka_ui_url == "http://localhost:8080"


def test_compose_kafka_and_kafka_ui_image_contract() -> None:
    compose_text = Path("docker-compose.yaml").read_text(encoding="utf-8")

    assert "kafka:" in compose_text
    assert "image: apache/kafka:4.2.1" in compose_text
    assert "kafka-ui:" in compose_text
    assert "image: provectuslabs/kafka-ui:latest" in compose_text


def test_compose_kafka_ui_bootstrap_wiring_contract() -> None:
    compose_text = Path("docker-compose.yaml").read_text(encoding="utf-8")

    assert "KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092" in compose_text


def test_compose_kraft_env_key_presence_contract() -> None:
    compose_text = Path("docker-compose.yaml").read_text(encoding="utf-8")
    required_env_keys = [
        "KAFKA_NODE_ID",
        "KAFKA_PROCESS_ROLES",
        "KAFKA_LISTENERS",
        "KAFKA_ADVERTISED_LISTENERS",
        "KAFKA_CONTROLLER_LISTENER_NAMES",
        "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP",
        "KAFKA_CONTROLLER_QUORUM_VOTERS",
        "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR",
        "KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR",
        "KAFKA_TRANSACTION_STATE_LOG_MIN_ISR",
        "KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS",
        "KAFKA_NUM_PARTITIONS",
    ]

    for key in required_env_keys:
        assert re.search(rf"^\s+{key}:", compose_text, re.MULTILINE), key


def test_kafka_ui_reachability_expectation_contract() -> None:
    compose = ComposeSettings()
    # Smoke-style expectation used by quickstart curl check.
    assert compose.kafka_ui_url.startswith("http://localhost:")
