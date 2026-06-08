from __future__ import annotations

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
            json={"topic_name": "topic-created", "num_partitions": 2, "replication_factor": 1},
        )
        exists = client.post(
            "/api/v1/topics",
            json={"topic_name": "topic-exists", "num_partitions": 1, "replication_factor": 1},
        )
        failed = client.post(
            "/api/v1/topics",
            json={"topic_name": "topic-fail", "num_partitions": 1, "replication_factor": 1},
        )

    assert created.status_code == 201
    assert created.json()["status"] == "created"

    assert exists.status_code == 200
    assert exists.json()["status"] == "already_exists"

    assert failed.status_code == 502
    assert failed.json()["status"] == "error"


def test_topic_create_invalid_payload_returns_structured_error() -> None:
    with _build_client() as client:
        response = client.post("/api/v1/topics", json={"topic_name": "", "num_partitions": 0})

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["topic_name"] is None
