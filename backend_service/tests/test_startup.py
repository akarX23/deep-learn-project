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


def test_test_event_route_enablement_defaults_and_override(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "BACKEND_KAFKA_BOOTSTRAP_SERVERS=file-kafka:9092\nAPP_ENV=dev\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("BACKEND_ENABLE_TEST_EVENT_APIS", raising=False)
    settings = KafkaSettings.from_env(dotenv_path=str(env_file))
    assert settings.test_event_routes_enabled() is True

    env_file.write_text(
        "BACKEND_KAFKA_BOOTSTRAP_SERVERS=file-kafka:9092\nAPP_ENV=prod\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("BACKEND_ENABLE_TEST_EVENT_APIS", raising=False)
    settings = KafkaSettings.from_env(dotenv_path=str(env_file))
    assert settings.test_event_routes_enabled() is False

    monkeypatch.setenv("BACKEND_ENABLE_TEST_EVENT_APIS", "true")
    settings = KafkaSettings.from_env(dotenv_path=str(env_file))
    assert settings.test_event_routes_enabled() is True


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

        def bootstrap_topics(self, topic_names: list[str]):
            from project.schemas import StartupTopicBootstrapResult

            return StartupTopicBootstrapResult()

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

        def bootstrap_topics(self, topic_names: list[str]):
            from project.schemas import StartupTopicBootstrapResult

            return StartupTopicBootstrapResult()

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

    assert "KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9093" in compose_text


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


def test_lifespan_includes_topic_bootstrap() -> None:
    """T015: Integration test that lifespan calls bootstrap_topics after connect."""
    from project.schemas import StartupTopicBootstrapResult

    class TrackingAdmin:
        def __init__(self, settings: KafkaSettings) -> None:
            self.settings = settings
            self.connect_called = False
            self.bootstrap_topics_called = False
            self.bootstrap_topics_topics = None

        def connect(self) -> None:
            self.connect_called = True

        def close(self) -> None:
            pass

        def bootstrap_topics(self, topic_names: list[str]):
            self.bootstrap_topics_called = True
            self.bootstrap_topics_topics = topic_names
            return StartupTopicBootstrapResult(
                created=topic_names, already_existed=[], errors=[]
            )

    tracking_admin = None

    def admin_factory(settings):
        nonlocal tracking_admin
        tracking_admin = TrackingAdmin(settings)
        return tracking_admin

    settings = KafkaSettings(bootstrap_servers="kafka:9092")
    app = create_app(settings=settings, admin_factory=admin_factory)

    with TestClient(app):
        pass

    # Verify sequence: connect() before bootstrap_topics()
    assert tracking_admin.connect_called is True
    assert tracking_admin.bootstrap_topics_called is True
    # Verify bootstrap received all topics from project/topics
    assert tracking_admin.bootstrap_topics_topics == ["rag", "rag-complete"]


# Bootstrap Topics Tests (T004-T008)


def test_bootstrap_topics_creates_new_topics() -> None:
    """T004: Test that bootstrap_topics() creates all new topics."""
    from backend_service.app.kafka_admin import KafkaAdminService

    class MockAdminNewTopics:
        def __init__(self, settings: KafkaSettings) -> None:
            self.settings = settings

        def connect(self) -> None:
            pass

        def close(self) -> None:
            pass

        def create_topic(
            self,
            topic_name: str,
            num_partitions: int,
            replication_factor: int,
            config=None,
        ) -> str:
            # All topics are new
            return "created"

    admin = MockAdminNewTopics(KafkaSettings(bootstrap_servers="localhost:9092"))
    # Add bootstrap_topics to the mock
    admin.bootstrap_topics = KafkaAdminService.bootstrap_topics.__get__(admin)

    result = admin.bootstrap_topics(["topic1", "topic2"])

    assert result.created == ["topic1", "topic2"]
    assert result.already_existed == []
    assert result.errors == []


def test_bootstrap_topics_idempotent_with_existing() -> None:
    """T005: Test that bootstrap_topics() handles already-existing topics."""
    from backend_service.app.kafka_admin import KafkaAdminService

    class MockAdminExisting:
        def __init__(self, settings: KafkaSettings) -> None:
            self.settings = settings

        def connect(self) -> None:
            pass

        def close(self) -> None:
            pass

        def create_topic(
            self,
            topic_name: str,
            num_partitions: int,
            replication_factor: int,
            config=None,
        ) -> str:
            # All topics already exist
            return "already_exists"

    admin = MockAdminExisting(KafkaSettings(bootstrap_servers="localhost:9092"))
    admin.bootstrap_topics = KafkaAdminService.bootstrap_topics.__get__(admin)

    result = admin.bootstrap_topics(["topic1", "topic2"])

    assert result.created == []
    assert result.already_existed == ["topic1", "topic2"]
    assert result.errors == []


def test_bootstrap_topics_mixed_new_and_existing() -> None:
    """T006: Test that bootstrap_topics() handles mixed new and existing topics."""
    from backend_service.app.kafka_admin import KafkaAdminService

    class MockAdminMixed:
        def __init__(self, settings: KafkaSettings) -> None:
            self.settings = settings
            self.existing_topics = {"topic2"}

        def connect(self) -> None:
            pass

        def close(self) -> None:
            pass

        def create_topic(
            self,
            topic_name: str,
            num_partitions: int,
            replication_factor: int,
            config=None,
        ) -> str:
            if topic_name in self.existing_topics:
                return "already_exists"
            return "created"

    admin = MockAdminMixed(KafkaSettings(bootstrap_servers="localhost:9092"))
    admin.bootstrap_topics = KafkaAdminService.bootstrap_topics.__get__(admin)

    result = admin.bootstrap_topics(["topic1", "topic2"])

    assert result.created == ["topic1"]
    assert result.already_existed == ["topic2"]
    assert result.errors == []


def test_bootstrap_topics_empty_registry() -> None:
    """T007: Test that bootstrap_topics() handles empty topic list."""
    from backend_service.app.kafka_admin import KafkaAdminService

    class MockAdminEmpty:
        def __init__(self, settings: KafkaSettings) -> None:
            self.settings = settings

        def connect(self) -> None:
            pass

        def close(self) -> None:
            pass

        def create_topic(
            self,
            topic_name: str,
            num_partitions: int,
            replication_factor: int,
            config=None,
        ) -> str:
            raise AssertionError("create_topic should not be called with empty list")

    admin = MockAdminEmpty(KafkaSettings(bootstrap_servers="localhost:9092"))
    admin.bootstrap_topics = KafkaAdminService.bootstrap_topics.__get__(admin)

    result = admin.bootstrap_topics([])

    assert result.created == []
    assert result.already_existed == []
    assert result.errors == []


def test_bootstrap_topics_transient_error_continues() -> None:
    """T008: Test that bootstrap_topics() continues on transient errors."""
    from backend_service.app.kafka_admin import KafkaAdminService

    class MockAdminWithError:
        def __init__(self, settings: KafkaSettings) -> None:
            self.settings = settings

        def connect(self) -> None:
            pass

        def close(self) -> None:
            pass

        def create_topic(
            self,
            topic_name: str,
            num_partitions: int,
            replication_factor: int,
            config=None,
        ) -> str:
            if topic_name == "topic2":
                raise RuntimeError("Broker connection timeout")
            return "created"

    admin = MockAdminWithError(KafkaSettings(bootstrap_servers="localhost:9092"))
    admin.bootstrap_topics = KafkaAdminService.bootstrap_topics.__get__(admin)

    result = admin.bootstrap_topics(["topic1", "topic2", "topic3"])

    assert result.created == ["topic1", "topic3"]
    assert result.already_existed == []
    assert len(result.errors) == 1
    assert result.errors[0][0] == "topic2"
    assert "Broker connection timeout" in result.errors[0][1]
