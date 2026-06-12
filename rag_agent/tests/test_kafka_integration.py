from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from project.schemas import RAGAgentOutput
from rag_agent.handlers import RAGRequestEventHandler
from rag_agent.logging import StructuredLogger
from rag_agent.kafka import publish_rag_complete
from rag_agent.worker import process_consumer_batch


class _FakeConsumer:
    def __init__(self, records):
        self._records = records
        self.last_timeout_ms = None

    def poll(self, timeout_ms: int):
        self.last_timeout_ms = timeout_ms
        records = self._records
        self._records = {}
        return records


class _CapturingLogger:
    def __init__(self) -> None:
        self.entries = []

    def log(self, level, message) -> None:
        import json

        self.entries.append((level, json.loads(message)))


def test_consumer_batch_dispatches_event_from_rag_topic() -> None:
    message = {
        "request_id": "req-1",
        "session_ctx": {"session_id": "s-1"},
        "user_request": "Explain gradient descent",
        "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
    }
    consumer = _FakeConsumer({"rag": [SimpleNamespace(value=message)]})
    captured = []

    processed = process_consumer_batch(
        consumer,
        producer=object(),
        handler=lambda payload, producer: captured.append((payload, producer)),
        poll_timeout_ms=250,
    )

    assert processed == 1
    assert consumer.last_timeout_ms == 250
    assert captured[0][0]["user_request"] == "Explain gradient descent"


def test_request_handler_dispatches_to_rag_agent() -> None:
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

    handler = RAGRequestEventHandler(agent_factory=_FakeAgent, publisher=_capture_publish)
    output = handler.process_request(
        {
            "request_id": "req-2",
            "session_ctx": {"session_id": "s-2"},
            "user_request": "Summarize the uploaded chapter",
            "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
        },
        producer=object(),
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

    handler = RAGRequestEventHandler(agent_factory=_FakeAgent, publisher=_capture_publish)
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

    process_consumer_batch(
        consumer,
        producer=object(),
        handler=handler.process_request,
        poll_timeout_ms=50,
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
    handler = RAGRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda _producer, _event: None,
        clock=lambda: next(fixed_times),
    )

    output = handler.process_request(
        {
            "request_id": "req-3",
            "session_ctx": {"session_id": "s-3", "trace_id": "trace-1"},
            "user_request": "Summarize section 2",
            "file_paths": ["rag_agent/tests/inputs/sample.pdf"],
        },
        producer=object(),
    )

    assert output.request_id == "req-3"
    assert output.session_ctx["trace_id"] == "trace-1"
    assert output.user_prompt == "Summarize section 2"
    assert output.duration_ms == 1000


def test_lifecycle_logging_covers_consume_process_and_publish() -> None:
    captured_logger = _CapturingLogger()
    lifecycle_logger = StructuredLogger(captured_logger)

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

    handler = RAGRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda _producer, _event: None,
        lifecycle_logger=lifecycle_logger,
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

    process_consumer_batch(
        consumer,
        producer=object(),
        handler=handler.process_request,
        poll_timeout_ms=100,
        lifecycle_logger=lifecycle_logger,
    )

    stages = [entry[1]["stage"] for entry in captured_logger.entries]
    assert stages == [
        "consumed",
        "processing_started",
        "processing_completed",
        "publish_completed",
    ]


def test_error_stage_logged_when_processing_fails() -> None:
    captured_logger = _CapturingLogger()
    lifecycle_logger = StructuredLogger(captured_logger)

    class _FailingAgent:
        def run(self, request):
            raise RuntimeError("synthetic processing failure")

    handler = RAGRequestEventHandler(
        agent_factory=_FailingAgent,
        publisher=lambda _producer, _event: None,
        lifecycle_logger=lifecycle_logger,
    )
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

    process_consumer_batch(
        consumer,
        producer=object(),
        handler=handler.process_request,
        poll_timeout_ms=100,
        lifecycle_logger=lifecycle_logger,
    )

    error_entries = [entry[1] for entry in captured_logger.entries if entry[1]["stage"] == "error"]
    assert error_entries
    assert error_entries[0]["metadata"]["failure_stage"] == "processing"


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