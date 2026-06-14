from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from project.schemas import RAGAgentOutput
from rag_agent.kafka import publish_rag_complete
from rag_agent.worker import RAGWorker, process_request_event


class _FakeConsumer:
    def __init__(self, records):
        self._records = records
        self.last_timeout_ms = None
        self.subscriptions: list[list[str]] = []
        self.closed = False

    def subscribe(self, topics):
        self.subscriptions.append(topics)

    def poll(self, timeout_ms: int):
        self.last_timeout_ms = timeout_ms
        records = self._records
        self._records = {}
        return records

    def topics(self):
        return {"rag", "rag-complete"}

    def close(self):
        self.closed = True


class _FakeProducer:
    def __init__(self):
        self.closed = False
        self.flush_count = 0

    def send(self, topic, payload):
        return SimpleNamespace(topic=topic, payload=payload)

    def flush(self):
        self.flush_count += 1

    def close(self):
        self.closed = True


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


def test_consumer_batch_dispatches_event_from_rag_topic(monkeypatch) -> None:
    message = {
        "request_id": "req-1",
        "session_ctx": {"session_id": "s-1"},
        "user_request": "Explain gradient descent",
        "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
    }
    consumer = _FakeConsumer({"rag": [SimpleNamespace(value=message)]})
    producer = _FakeProducer()
    captured = {}

    monkeypatch.setattr("rag_agent.worker.create_consumer", lambda _cfg: consumer)
    monkeypatch.setattr("rag_agent.worker.create_producer", lambda _cfg: producer)
    monkeypatch.setattr(
        "rag_agent.worker.process_request_event",
        lambda payload, _producer: captured.setdefault("payload", payload),
    )

    worker = RAGWorker(config=_make_config())
    worker.start()
    worker.stop()

    assert consumer.last_timeout_ms == 5
    assert captured["payload"]["user_request"] == "Explain gradient descent"


def test_request_event_processor_dispatches_to_rag_agent() -> None:
    captured = {}

    class _FakeAgent:
        def run(self, request):
            captured["request"] = request
            return RAGAgentOutput(
                request_id=request.request_id,
                user_prompt=request.user_prompt,
                schema_version=request.schema_version,
                compiled_material="# Notes",
                extracted_pages=[],
                total_pages_processed=1,
                total_pages_included=1,
                errors=[],
                status="complete",
            )

    published = {}

    def _capture_publish(_producer, event):
        published["event"] = event

    output = process_request_event(
        {
            "request_id": "req-2",
            "session_ctx": {"session_id": "s-2"},
            "user_request": "Summarize the uploaded chapter",
            "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
        },
        producer=object(),
        agent_factory=_FakeAgent,
        publisher=_capture_publish,
    )

    assert captured["request"].user_prompt == "Summarize the uploaded chapter"
    assert captured["request"].file_paths == ["rag_agent/tests/inputs/sample.pdf"]
    assert output.status == "complete"
    assert published["event"].request_id == "req-2"
    assert published["event"].session_ctx == {"session_id": "s-2"}


def test_ingest_to_dispatch_flow_preserves_request_id() -> None:
    class _FakeAgent:
        def run(self, request):
            return RAGAgentOutput(
                request_id=request.request_id,
                user_prompt=request.user_prompt,
                schema_version=request.schema_version,
                compiled_material="# Notes",
                extracted_pages=[],
                total_pages_processed=1,
                total_pages_included=1,
                errors=[],
                status="complete",
            )

    published = {}

    def _capture_publish(_producer, event):
        published["request_id"] = event.request_id

    consumer = _FakeConsumer(
        {
            "rag": [
                SimpleNamespace(
                    topic="rag",
                    value={
                        "request_id": "req-ingest-1",
                        "session_ctx": {"session_id": "s-10"},
                        "user_request": "Summarize this file",
                        "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
                    },
                )
            ]
        }
    )

    process_request_event(
        payload=consumer._records["rag"][0].value,
        producer=object(),
        agent_factory=_FakeAgent,
        publisher=_capture_publish,
    )

    assert published["request_id"] == "req-ingest-1"


def test_publish_rag_complete_sends_to_completion_topic() -> None:
    sent = {}

    class _FakeProducer:
        def send(self, topic, payload):
            sent["topic"] = topic
            sent["payload"] = payload

        def flush(self):
            sent["flushed"] = True

    publish_rag_complete(
        _FakeProducer(),
        output := handler_completion_event(),
    )

    assert sent["topic"] == "rag-complete"
    assert sent["payload"]["request_id"] == output.request_id
    assert sent["flushed"] is True


def test_completion_event_preserves_request_correlation() -> None:
    class _FakeAgent:
        def run(self, request):
            return RAGAgentOutput(
                request_id=request.request_id,
                user_prompt=request.user_prompt,
                schema_version=request.schema_version,
                compiled_material="# Notes",
                extracted_pages=[],
                total_pages_processed=3,
                total_pages_included=2,
                errors=["warning"],
                status="partial",
            )

    fixed_times = iter(
        [
            datetime(2026, 6, 11, 16, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 6, 11, 16, 0, 1, tzinfo=timezone.utc),
        ]
    )
    output = process_request_event(
        {
            "request_id": "req-3",
            "session_ctx": {"session_id": "s-3", "trace_id": "trace-1"},
            "user_request": "Summarize section 2",
            "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
        },
        producer=object(),
        agent_factory=_FakeAgent,
        publisher=lambda _producer, _event: None,
        clock=lambda: next(fixed_times),
    )

    assert output.request_id == "req-3"
    assert output.session_ctx["trace_id"] == "trace-1"
    assert output.user_prompt == "Summarize section 2"
    assert output.duration_ms == 1000


def test_lifecycle_logging_covers_consume_process_and_publish(
    caplog, monkeypatch
) -> None:
    import logging

    class _FakeAgent:
        def run(self, request):
            return RAGAgentOutput(
                request_id=request.request_id,
                user_prompt=request.user_prompt,
                schema_version=request.schema_version,
                compiled_material="# Notes",
                extracted_pages=[],
                total_pages_processed=1,
                total_pages_included=1,
                errors=[],
                status="complete",
            )

    consumer = _FakeConsumer(
        {
            "rag": [
                SimpleNamespace(
                    topic="rag",
                    value={
                        "request_id": "req-5",
                        "session_ctx": {"session_id": "s-5"},
                        "user_request": "Explain gradient descent",
                        "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
                    },
                )
            ]
        }
    )

    producer = _FakeProducer()
    monkeypatch.setattr("rag_agent.worker.create_consumer", lambda _cfg: consumer)
    monkeypatch.setattr("rag_agent.worker.create_producer", lambda _cfg: producer)
    monkeypatch.setattr(
        "rag_agent.worker.process_request_event",
        lambda payload, prod: process_request_event(
            payload,
            prod,
            agent_factory=_FakeAgent,
            publisher=lambda _producer, _event: None,
        ),
    )

    with caplog.at_level(logging.INFO):
        worker = RAGWorker(config=_make_config())
        worker.start()
        worker.stop()

    messages = [r.message for r in caplog.records]
    assert any("consumed" in m for m in messages)
    assert any(
        "processing_started" in m or "processing_completed" in m for m in messages
    )
    assert any("publish_completed" in m for m in messages)


def test_error_stage_logged_when_processing_fails(caplog, monkeypatch) -> None:
    import logging

    class _FailingAgent:
        def run(self, request):
            raise RuntimeError("synthetic processing failure")

    consumer = _FakeConsumer(
        {
            "rag": [
                SimpleNamespace(
                    topic="rag",
                    value={
                        "request_id": "req-6",
                        "session_ctx": {"session_id": "s-6"},
                        "user_request": "Explain failure flow",
                        "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
                    },
                )
            ]
        }
    )

    producer = _FakeProducer()
    monkeypatch.setattr("rag_agent.worker.create_consumer", lambda _cfg: consumer)
    monkeypatch.setattr("rag_agent.worker.create_producer", lambda _cfg: producer)
    monkeypatch.setattr(
        "rag_agent.worker.process_request_event",
        lambda payload, prod: process_request_event(
            payload,
            prod,
            agent_factory=_FailingAgent,
            publisher=lambda _producer, _event: None,
        ),
    )

    with caplog.at_level(logging.ERROR):
        worker = RAGWorker(config=_make_config())
        worker.start()
        worker.stop()

    error_messages = [r.message for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_messages
    assert any(
        "processing_failed" in m or "synthetic processing failure" in m
        for m in error_messages
    )


def handler_completion_event():
    from project.schemas import RAGCompletionEvent

    return RAGCompletionEvent(
        request_id="req-4",
        session_ctx={"session_id": "s-4"},
        user_prompt="Summarize chapter 4",
        compiled_material="# Output",
        status="complete",
        errors=[],
        total_pages_processed=4,
        total_pages_included=4,
        started_at="2026-06-11T16:00:00Z",
        completed_at="2026-06-11T16:00:01Z",
        duration_ms=1000,
    )
