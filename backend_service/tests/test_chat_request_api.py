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


def _payload(sid: str = "sid-1") -> dict[str, object]:
    return {
        "user_prompt": "Explain neural networks",
        "user_level": ["beginner"],
        "sid": sid,
    }


def test_chat_request_route_registered() -> None:
    app = _build_app()
    assert any(route.path == "/api/chat/request" for route in app.router.routes)


def test_chat_request_success_publishes_planner_event(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    producer = FakeProducer()
    app = _build_app(producer=producer)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/request",
            data=_payload(),
            files=[
                ("files", ("doc1.txt", b"hello", "text/plain")),
                ("files", ("doc2.txt", b"world", "text/plain")),
            ],
        )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Request accepted and queued for planner processing"
    }
    assert len(producer.sent) == 1
    topic, value = producer.sent[0]
    assert topic == "init-planner"
    assert value["user_prompt"] == "Explain neural networks"
    assert value["sid"] == "sid-1"
    assert len(value["file_paths"]) == 2
    for path in value["file_paths"]:
        assert path.startswith("/")


def test_chat_request_saves_files_to_upload_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    producer = FakeProducer()
    app = _build_app(producer=producer)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/request",
            data=_payload(),
            files=[("files", ("notes.pdf", b"%PDF-1.4 test", "application/pdf"))],
        )

    assert response.status_code == 200
    saved = list(tmp_path.iterdir())
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"%PDF-1.4 test"


def test_chat_request_missing_required_field_returns_422(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    app = _build_app(producer=FakeProducer())

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/request",
            data={"user_level": ["beginner"], "sid": "sid-1"},
        )

    # Missing required form field (user_prompt) -> FastAPI validation error.
    assert response.status_code == 422


def test_chat_request_publish_failure_returns_500(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    producer = FakeProducer(error=RuntimeError("kafka down"))
    app = _build_app(producer=producer)

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/request",
            data=_payload(),
            files=[("files", ("doc.txt", b"x", "text/plain"))],
        )

    assert response.status_code == 500
    body = response.json()
    assert "error" in body
    # Files remain on disk (retained) even when publish fails.
    assert len(list(tmp_path.iterdir())) == 1


def test_chat_request_more_than_three_files_still_accepted(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    producer = FakeProducer()
    app = _build_app(producer=producer)

    files = [
        ("files", (f"doc{i}.txt", f"content-{i}".encode(), "text/plain"))
        for i in range(4)
    ]
    with TestClient(app) as client:
        response = client.post(
            "/api/chat/request",
            data=_payload(),
            files=files,
        )

    assert response.status_code == 200
    topic, value = producer.sent[0]
    assert len(value["file_paths"]) == 4
