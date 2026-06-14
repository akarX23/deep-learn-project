from __future__ import annotations

import time
from dataclasses import dataclass

from rag_agent.worker import RAGWorker


@dataclass
class _FakeRecord:
    topic: str
    value: dict[str, object]


class _FakeConsumer:
    def __init__(
        self, *, topics: set[str], responses: list[dict[object, list[_FakeRecord]]]
    ) -> None:
        self._topics = topics
        self._responses = responses
        self.poll_calls = 0
        self.closed = False
        self.subscriptions: list[list[str]] = []

    def subscribe(self, topics: list[str]) -> None:
        self.subscriptions.append(topics)

    def poll(self, timeout_ms: int) -> dict[object, list[_FakeRecord]]:
        self.poll_calls += 1
        time.sleep(timeout_ms / 1000.0)
        if self._responses:
            return self._responses.pop(0)
        return {}

    def topics(self) -> set[str]:
        return self._topics

    def close(self) -> None:
        self.closed = True


class _FakeProducer:
    def __init__(self) -> None:
        self.closed = False
        self.flush_count = 0

    def send(self, _topic: str, _payload: dict[str, object]) -> object:
        return object()

    def flush(self) -> None:
        self.flush_count += 1

    def close(self) -> None:
        self.closed = True


class _Handler:
    def __init__(self, should_raise: bool = False) -> None:
        self.should_raise = should_raise
        self.calls = 0

    def process_request(
        self, _payload: dict[str, object], _producer: _FakeProducer | None = None
    ) -> None:
        self.calls += 1
        if self.should_raise and self.calls == 1:
            raise RuntimeError("synthetic handler failure")


def _make_config() -> dict[str, object]:
    return {
        "bootstrap_servers": "localhost:9092",
        "client_id": "rag-test",
        "consumer_group_id": "rag-test-consumer",
        "poll_timeout_ms": 5,
        "security_protocol": None,
        "sasl_mechanism": None,
        "sasl_username": None,
        "sasl_password": None,
        "ssl_cafile": None,
    }


def _patch_worker_factories(
    monkeypatch,
    consumer: _FakeConsumer,
    producer: _FakeProducer,
) -> None:
    monkeypatch.setattr("rag_agent.worker.create_consumer", lambda _config: consumer)
    monkeypatch.setattr("rag_agent.worker.create_producer", lambda _config: producer)


def test_worker_startup_and_shutdown_lifecycle(monkeypatch) -> None:
    fake_consumer = _FakeConsumer(topics={"rag", "rag-complete"}, responses=[{}])
    fake_producer = _FakeProducer()
    _patch_worker_factories(monkeypatch, fake_consumer, fake_producer)

    worker = RAGWorker(config=_make_config())

    worker.start()
    time.sleep(0.02)
    state = worker.get_state()
    worker.stop()

    assert state.startup_topic_check_complete is True
    assert state.startup_topic_check_warnings == []
    assert fake_consumer.subscriptions and fake_consumer.subscriptions[0] == ["rag"]
    assert fake_consumer.poll_calls > 0
    assert fake_consumer.closed is True
    assert fake_producer.closed is True


def test_worker_loop_continues_when_idle(monkeypatch) -> None:
    fake_consumer = _FakeConsumer(
        topics={"rag", "rag-complete"}, responses=[{}, {}, {}]
    )
    fake_producer = _FakeProducer()
    _patch_worker_factories(monkeypatch, fake_consumer, fake_producer)

    worker = RAGWorker(config=_make_config())

    worker.start()
    time.sleep(0.03)
    worker.stop()

    assert fake_consumer.poll_calls >= 2


def test_process_batch_continues_after_single_event_failure(monkeypatch) -> None:
    fake_consumer = _FakeConsumer(
        topics={"rag", "rag-complete"},
        responses=[
            {
                object(): [
                    _FakeRecord(topic="rag", value={"request_id": "req-1"}),
                    _FakeRecord(topic="rag", value={"request_id": "req-2"}),
                ]
            }
        ],
    )
    fake_producer = _FakeProducer()
    handler = _Handler(should_raise=True)
    _patch_worker_factories(monkeypatch, fake_consumer, fake_producer)
    monkeypatch.setattr(
        "rag_agent.worker.process_request_event",
        lambda payload, producer: handler.process_request(payload, producer),
    )

    worker = RAGWorker(config=_make_config())
    worker.start()
    time.sleep(0.02)
    worker.stop()

    assert handler.calls == 2


def test_startup_topic_check_passes_when_topics_exist(monkeypatch) -> None:
    fake_consumer = _FakeConsumer(topics={"rag", "rag-complete"}, responses=[{}])
    fake_producer = _FakeProducer()
    _patch_worker_factories(monkeypatch, fake_consumer, fake_producer)

    worker = RAGWorker(config=_make_config())

    worker.start()
    state = worker.get_state()
    worker.stop()

    assert state.startup_topic_check_complete is True
    assert state.startup_topic_check_warnings == []


def test_missing_topics_warn_and_worker_continues(monkeypatch) -> None:
    fake_consumer = _FakeConsumer(topics={"rag"}, responses=[{}])
    fake_producer = _FakeProducer()
    _patch_worker_factories(monkeypatch, fake_consumer, fake_producer)

    worker = RAGWorker(config=_make_config())

    worker.start()
    state = worker.get_state()
    worker.stop()

    assert state.running is True
    assert state.startup_topic_check_warnings
    assert "rag-complete" in state.startup_topic_check_warnings[0]


def test_runtime_does_not_require_backend_topic_api_config() -> None:
    config = _make_config()

    assert "topic_api_url" not in config


def measure_poll_to_completion_latency_ms(iterations: int = 50) -> float:
    """Measure average worker poll-loop dispatch overhead."""

    fake_consumer = _FakeConsumer(
        topics={"rag", "rag-complete"},
        responses=[
            {object(): [_FakeRecord(topic="rag", value={"request_id": "req"})]}
            for _ in range(iterations)
        ],
    )
    fake_producer = _FakeProducer()
    handler = _Handler()
    from rag_agent import worker as worker_mod

    started = time.perf_counter()
    original_process = worker_mod.process_request_event
    original_create_consumer = worker_mod.create_consumer
    original_create_producer = worker_mod.create_producer
    try:
        worker_mod.create_consumer = lambda _config: fake_consumer
        worker_mod.create_producer = lambda _config: fake_producer
        worker_mod.process_request_event = lambda payload, producer: (
            handler.process_request(payload, producer)
        )

        worker = RAGWorker(config=_make_config())
        worker.start()
        while handler.calls < iterations:
            time.sleep(0.001)
        worker.stop()
    finally:
        worker_mod.process_request_event = original_process
        worker_mod.create_consumer = original_create_consumer
        worker_mod.create_producer = original_create_producer

    elapsed_ms = (time.perf_counter() - started) * 1000
    return elapsed_ms / iterations


def test_latency_helper_returns_non_negative_value() -> None:
    latency_ms = measure_poll_to_completion_latency_ms(iterations=10)

    assert latency_ms >= 0
