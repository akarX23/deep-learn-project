from __future__ import annotations

from fastapi.testclient import TestClient

from backend_service.app.config import KafkaSettings
from backend_service.app.main import create_app
from project.schemas import StartupTopicBootstrapResult


class FakeFuture:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def get(self, timeout: int | None = None):
        if self.error is not None:
            raise self.error
        return None


class FakeProducer:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.sent: list[tuple[str, dict[str, object]]] = []
        self.closed = False

    def send(self, topic: str, value: dict[str, object]) -> FakeFuture:
        self.sent.append((topic, value))
        return FakeFuture(error=self.error)

    def close(self) -> None:
        self.closed = True


class FakeAdmin:
    def __init__(
        self, settings: KafkaSettings, producer: FakeProducer | None = None
    ) -> None:
        self.settings = settings
        self._producer = producer

    def connect(self) -> None:
        return None

    def close(self) -> None:
        if self._producer is not None:
            self._producer.close()

    def bootstrap_topics(self, topic_names: list[str]):
        return StartupTopicBootstrapResult()

    @property
    def producer(self) -> FakeProducer:
        if self._producer is None:
            raise RuntimeError("producer not configured")
        return self._producer


def _build_app(producer: FakeProducer | None = None):
    settings = KafkaSettings(bootstrap_servers="kafka:9092", app_env="dev")

    def admin_factory(kafka_settings: KafkaSettings) -> FakeAdmin:
        return FakeAdmin(kafka_settings, producer=producer)

    return create_app(settings=settings, admin_factory=admin_factory)


def _payload(sid: str = "sid-1") -> dict[str, str]:
    return {
        "sid": sid,
        "user_prompt": "Generate a quiz on neural networks",
        "teaching_material": "Neural networks are layered function approximators.",
    }


def test_quiz_request_route_registered() -> None:
    app = _build_app()
    assert any(route.path == "/api/quiz/request" for route in app.router.routes)


def test_quiz_request_success_publishes_quiz_event() -> None:
    producer = FakeProducer()
    app = _build_app(producer=producer)

    with TestClient(app) as client:
        response = client.post("/api/quiz/request", json=_payload())

    assert response.status_code == 200
    assert response.json() == {"message": "Quiz request accepted and queued"}
    assert len(producer.sent) == 1

    topic, value = producer.sent[0]
    assert topic == "quiz-request"
    assert value["sid"] == "sid-1"
    assert value["user_prompt"] == "Generate a quiz on neural networks"
    assert len(value["user_levels"]) == 1
    assert value["user_levels"][0] in {"beginner", "intermediate", "advanced"}

    level = value["user_levels"][0]
    assert value["teaching_materials"] == {
        level: "Neural networks are layered function approximators."
    }


def test_quiz_request_missing_required_field_returns_422() -> None:
    app = _build_app(producer=FakeProducer())

    with TestClient(app) as client:
        response = client.post(
            "/api/quiz/request",
            json={"sid": "sid-1", "teaching_material": "material only"},
        )

    assert response.status_code == 422


def test_quiz_request_publish_failure_returns_500() -> None:
    producer = FakeProducer(error=RuntimeError("kafka down"))
    app = _build_app(producer=producer)

    with TestClient(app) as client:
        response = client.post("/api/quiz/request", json=_payload())

    assert response.status_code == 500
    body = response.json()
    assert "error" in body
