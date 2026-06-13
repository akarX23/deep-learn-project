from __future__ import annotations

import logging


def test_agent_module_logger_uses_dunder_name() -> None:
    module_logger = logging.getLogger("rag_agent.agent")
    assert module_logger.name == "rag_agent.agent"


def test_worker_module_logger_uses_dunder_name() -> None:
    module_logger = logging.getLogger("rag_agent.worker")
    assert module_logger.name == "rag_agent.worker"


def test_handlers_module_logger_uses_dunder_name() -> None:
    module_logger = logging.getLogger("rag_agent.handlers")
    assert module_logger.name == "rag_agent.handlers"


def test_kafka_module_logger_uses_dunder_name() -> None:
    module_logger = logging.getLogger("rag_agent.kafka")
    assert module_logger.name == "rag_agent.kafka"


def test_worker_logs_startup_warning_for_missing_topics(caplog) -> None:
    """Verify standard logging emits a warning when topics are missing at startup."""
    import time
    from dataclasses import dataclass

    from rag_agent.worker import RAGWorker

    @dataclass
    class _FakeRecord:
        topic: str
        value: dict[str, object]

    class _FakeConsumer:
        def __init__(self, topics):
            self._topics = topics

        def subscribe(self, topics):
            pass

        def poll(self, timeout_ms):
            time.sleep(timeout_ms / 1000.0)
            return {}

        def topics(self):
            return self._topics

        def close(self):
            pass

    class _FakeProducer:
        def send(self, _t, _p):
            return None

        def flush(self):
            pass

        def close(self):
            pass

    config = {
        "bootstrap_servers": "localhost:9092",
        "client_id": "rag-service",
        "consumer_group_id": "rag-service-consumer",
        "poll_timeout_ms": 5,
        "security_protocol": None,
        "sasl_mechanism": None,
        "sasl_username": None,
        "sasl_password": None,
        "ssl_cafile": None,
    }
    # Only rag is present; rag-complete is missing
    fake_consumer = _FakeConsumer(topics={"rag"})

    with caplog.at_level(logging.WARNING, logger="rag_agent.worker"):
        worker = RAGWorker(
            config=config,
            producer_factory=lambda _c: _FakeProducer(),
            consumer_factory=lambda _c: fake_consumer,
            request_processor=lambda _payload, _producer: None,
        )
        worker.start()
        worker.stop()

    assert any(
        "missing" in record.message.lower() or "startup_topic_check" in record.message
        for record in caplog.records
    )
