from __future__ import annotations

import time
from dataclasses import dataclass

from teaching_agent.config import KafkaRuntimeConfig
from teaching_agent.worker import TeachingWorker, process_consumer_batch


@dataclass
class _FakeRecord:
    topic: str
    value: dict[str, object]


class _FakeConsumer:
    def __init__(self, *, topics: set[str], responses: list[dict]) -> None:
        self._topics = topics
        self._responses = responses
        self.poll_calls = 0
        self.closed = False
        self.subscriptions: list[list[str]] = []

    def subscribe(self, topics: list[str]) -> None:
        self.subscriptions.append(topics)

    def poll(self, timeout_ms: int) -> dict:
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

    def send(self, _topic: str, _payload: dict) -> object:
        return object()

    def flush(self) -> None:
        self.flush_count += 1

    def close(self) -> None:
        self.closed = True


class _Handler:
    def __init__(self, should_raise: bool = False) -> None:
        self.should_raise = should_raise
        self.calls = 0

    def process_request(self, _payload: dict, _producer=None):
        self.calls += 1
        if self.should_raise and self.calls == 1:
            raise RuntimeError("synthetic handler failure")
        return None


def _make_config() -> KafkaRuntimeConfig:
    return KafkaRuntimeConfig(
        bootstrap_servers="localhost:9092",
        client_id="teaching-test",
        consumer_group_id="teaching-test-consumer",
        poll_timeout_ms=5,
    )


def test_worker_startup_and_shutdown_lifecycle() -> None:
    fake_consumer = _FakeConsumer(topics={"teaching", "teaching-complete"}, responses=[{}])
    fake_producer = _FakeProducer()

    worker = TeachingWorker(
        config=_make_config(),
        producer_factory=lambda _config: fake_producer,
        consumer_factory=lambda _config: fake_consumer,
        handler_factory=lambda: _Handler(),
    )

    worker.start()
    time.sleep(0.02)
    state = worker.get_state()
    worker.stop()

    assert state.startup_topic_check_complete is True
    assert state.startup_topic_check_warnings == []
    assert fake_consumer.subscriptions and fake_consumer.subscriptions[0] == ["teaching"]
    assert fake_consumer.poll_calls > 0
    assert fake_consumer.closed is True
    assert fake_producer.closed is True


def test_worker_loop_continues_when_idle() -> None:
    fake_consumer = _FakeConsumer(topics={"teaching", "teaching-complete"}, responses=[{}, {}, {}])
    fake_producer = _FakeProducer()

    worker = TeachingWorker(
        config=_make_config(),
        producer_factory=lambda _config: fake_producer,
        consumer_factory=lambda _config: fake_consumer,
        handler_factory=lambda: _Handler(),
    )

    worker.start()
    time.sleep(0.03)
    worker.stop()

    assert fake_consumer.poll_calls >= 2


def test_process_batch_continues_after_single_event_failure() -> None:
    fake_consumer = _FakeConsumer(
        topics={"teaching", "teaching-complete"},
        responses=[
            {
                object(): [
                    _FakeRecord(topic="teaching", value={"request_id": "req-1"}),
                    _FakeRecord(topic="teaching", value={"request_id": "req-2"}),
                ]
            }
        ],
    )
    fake_producer = _FakeProducer()
    handler = _Handler(should_raise=True)

    processed = process_consumer_batch(
        fake_consumer,
        fake_producer,
        handler.process_request,
        poll_timeout_ms=1,
    )

    assert processed == 2
    assert handler.calls == 2


def test_startup_topic_check_passes_when_topics_exist() -> None:
    fake_consumer = _FakeConsumer(topics={"teaching", "teaching-complete"}, responses=[{}])
    fake_producer = _FakeProducer()

    worker = TeachingWorker(
        config=_make_config(),
        producer_factory=lambda _config: fake_producer,
        consumer_factory=lambda _config: fake_consumer,
        handler_factory=lambda: _Handler(),
    )

    worker.start()
    state = worker.get_state()
    worker.stop()

    assert state.startup_topic_check_complete is True
    assert state.startup_topic_check_warnings == []


def test_missing_topics_warn_and_worker_continues() -> None:
    fake_consumer = _FakeConsumer(topics={"teaching"}, responses=[{}])
    fake_producer = _FakeProducer()

    worker = TeachingWorker(
        config=_make_config(),
        producer_factory=lambda _config: fake_producer,
        consumer_factory=lambda _config: fake_consumer,
        handler_factory=lambda: _Handler(),
    )

    worker.start()
    state = worker.get_state()
    worker.stop()

    assert state.running is True
    assert state.startup_topic_check_warnings
    assert "teaching-complete" in state.startup_topic_check_warnings[0]


def measure_poll_to_completion_latency_ms(iterations: int = 50) -> float:
    """Measure average process_consumer_batch dispatch overhead."""

    fake_consumer = _FakeConsumer(
        topics={"teaching", "teaching-complete"},
        responses=[
            {object(): [_FakeRecord(topic="teaching", value={"request_id": "req"})]}
            for _ in range(iterations)
        ],
    )
    fake_producer = _FakeProducer()
    handler = _Handler()

    started = time.perf_counter()
    for _ in range(iterations):
        process_consumer_batch(
            fake_consumer,
            fake_producer,
            handler.process_request,
            poll_timeout_ms=1,
        )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return elapsed_ms / iterations


def test_latency_helper_returns_non_negative_value() -> None:
    latency_ms = measure_poll_to_completion_latency_ms(iterations=10)

    assert latency_ms >= 0
