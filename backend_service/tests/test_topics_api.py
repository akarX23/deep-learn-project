from __future__ import annotations

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend_service.app.config import KafkaSettings
from backend_service.app.main import create_app


class ScenarioAdmin:
    def __init__(self, settings: KafkaSettings) -> None:
        self.settings = settings

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def create_topic(
        self,
        topic_name: str,
        num_partitions: int,
        replication_factor: int,
        config: dict[str, str] | None = None,
    ) -> str:
        if topic_name == "topic-fail":
            raise RuntimeError("kafka down")
        if topic_name == "topic-exists":
            return "already_exists"
        return "created"

    def bootstrap_topics(self, topic_names: list[str]):
        from project.schemas import StartupTopicBootstrapResult

        return StartupTopicBootstrapResult()


def _build_client() -> TestClient:
    settings = KafkaSettings(
        bootstrap_servers="kafka:9092",
        startup_retry_count=0,
        startup_retry_timeout_seconds=1,
    )
    app = create_app(settings=settings, admin_factory=ScenarioAdmin)
    return TestClient(app)


def test_topic_create_success_exists_and_runtime_error() -> None:
    with _build_client() as client:
        created = client.post(
            "/api/v1/topics",
            json={
                "topic_name": "topic-created",
                "num_partitions": 2,
                "replication_factor": 1,
            },
        )
        exists = client.post(
            "/api/v1/topics",
            json={
                "topic_name": "topic-exists",
                "num_partitions": 1,
                "replication_factor": 1,
            },
        )
        failed = client.post(
            "/api/v1/topics",
            json={
                "topic_name": "topic-fail",
                "num_partitions": 1,
                "replication_factor": 1,
            },
        )

    assert created.status_code == 201
    assert created.json()["status"] == "created"

    assert exists.status_code == 200
    assert exists.json()["status"] == "already_exists"

    assert failed.status_code == 502
    assert failed.json()["status"] == "error"


def test_topic_create_invalid_payload_returns_structured_error() -> None:
    with _build_client() as client:
        response = client.post(
            "/api/v1/topics", json={"topic_name": "", "num_partitions": 0}
        )

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["topic_name"] is None


def test_http_and_unhandled_exceptions_use_structured_envelope() -> None:
    settings = KafkaSettings(
        bootstrap_servers="kafka:9092",
        startup_retry_count=0,
        startup_retry_timeout_seconds=1,
    )
    app = create_app(settings=settings, admin_factory=ScenarioAdmin)

    @app.get("/test/http-error")
    def _http_error() -> None:
        raise HTTPException(status_code=418, detail="teapot")

    @app.get("/test/unhandled-error")
    def _unhandled_error() -> None:
        raise ValueError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        http_resp = client.get("/test/http-error")
        unhandled_resp = client.get("/test/unhandled-error")

    assert http_resp.status_code == 418
    assert http_resp.json() == {
        "topic_name": None,
        "status": "error",
        "message": "teapot",
    }

    assert unhandled_resp.status_code == 500
    assert unhandled_resp.json() == {
        "topic_name": None,
        "status": "error",
        "message": "Internal server error",
    }
