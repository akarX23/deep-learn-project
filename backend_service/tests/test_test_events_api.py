from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend_service.app.config import KafkaSettings
from backend_service.app.main import create_app
from project.schemas import StartupTopicBootstrapResult


class FakeAdmin:
    def __init__(self, settings: KafkaSettings) -> None:
        self.settings = settings

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def bootstrap_topics(self, topic_names: list[str]):
        return StartupTopicBootstrapResult()


class FakeFuture:
    def __init__(self, metadata=None, error: Exception | None = None) -> None:
        self.metadata = metadata
        self.error = error

    def get(self, timeout: int | None = None):
        if self.error is not None:
            raise self.error
        return self.metadata


class FakeProducer:
    def __init__(self, metadata=None, error: Exception | None = None) -> None:
        self.metadata = metadata
        self.error = error
        self.sent: list[tuple[str, dict[str, object]]] = []
        self.closed = False

    def send(self, topic: str, value: dict[str, object]) -> FakeFuture:
        self.sent.append((topic, value))
        return FakeFuture(metadata=self.metadata, error=self.error)

    def close(self) -> None:
        self.closed = True


def _build_app(
    settings: KafkaSettings,
    producer: FakeProducer | None = None,
) -> tuple[object, FakeProducer | None]:
    def producer_factory(_settings: KafkaSettings) -> FakeProducer:
        if producer is None:
            raise RuntimeError("producer not configured")
        return producer

    app = create_app(
        settings=settings,
        admin_factory=FakeAdmin,
        test_event_producer_factory=producer_factory if producer is not None else None,
    )
    return app, producer


def test_test_event_route_enabled_by_default_in_dev() -> None:
    settings = KafkaSettings(bootstrap_servers="kafka:9092", app_env="dev")

    app, _ = _build_app(settings)

    assert any(route.path == "/api/v1/test-events/rag" for route in app.router.routes)


def test_test_event_route_disabled_in_prod_without_opt_in() -> None:
    settings = KafkaSettings(bootstrap_servers="kafka:9092", app_env="prod")

    app, _ = _build_app(settings)

    assert not any(route.path == "/api/v1/test-events/rag" for route in app.router.routes)


def test_test_event_route_enabled_in_prod_with_explicit_opt_in() -> None:
    settings = KafkaSettings(
        bootstrap_servers="kafka:9092",
        app_env="prod",
        enable_test_event_apis=True,
    )

    app, _ = _build_app(settings)

    assert any(route.path == "/api/v1/test-events/rag" for route in app.router.routes)


def test_publish_rag_test_event_returns_inline_metadata() -> None:
    metadata = SimpleNamespace(partition=3, offset=42, timestamp=1234567890)
    producer = FakeProducer(metadata=metadata)
    settings = KafkaSettings(bootstrap_servers="kafka:9092", app_env="dev")
    app, producer = _build_app(settings, producer=producer)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/test-events/rag",
            json={
                "overrides": {
                    "user_request": "Summarize gradient descent",
                    "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
                    "session_ctx": {"mode": "quick"},
                }
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["topic"] == "rag"
    assert body["publish_status"] == "published"
    assert body["request_id"].startswith("test-")
    assert body["metadata"] == {
        "partition": 3,
        "offset": 42,
        "timestamp": 1234567890,
    }
    assert producer is not None
    assert producer.sent[0][0] == "rag"
    assert producer.sent[0][1]["user_request"] == "Summarize gradient descent"
    assert producer.sent[0][1]["file_paths"] == ["rag_agent/tests/inputs/sample.pdf"]


def test_publish_rag_test_event_supports_partial_metadata() -> None:
    metadata = SimpleNamespace(partition=1, offset=2, timestamp=None)
    producer = FakeProducer(metadata=metadata)
    settings = KafkaSettings(bootstrap_servers="kafka:9092", app_env="dev")
    app, _ = _build_app(settings, producer=producer)

    with TestClient(app) as client:
        response = client.post("/api/v1/test-events/rag", json={})

    assert response.status_code == 200
    assert response.json()["metadata"] == {
        "partition": 1,
        "offset": 2,
        "timestamp": None,
    }


def test_publish_rag_test_event_invalid_override_returns_structured_error() -> None:
    producer = FakeProducer(metadata=SimpleNamespace(partition=0, offset=1, timestamp=2))
    settings = KafkaSettings(bootstrap_servers="kafka:9092", app_env="dev")
    app, _ = _build_app(settings, producer=producer)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/test-events/rag",
            json={"overrides": {"file_paths": []}},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["topic_name"] is None


def test_publish_rag_test_event_failure_returns_structured_error() -> None:
    producer = FakeProducer(error=RuntimeError("kafka unavailable"))
    settings = KafkaSettings(bootstrap_servers="kafka:9092", app_env="dev")
    app, _ = _build_app(settings, producer=producer)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/test-events/rag", json={})

    assert response.status_code == 502
    body = response.json()
    assert body["status"] == "error"
    assert body["message"] == "kafka unavailable"
