from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from project.schemas import TeachingAgentOutput, TeachingContent, TeachingMetadata
from teaching_agent.handlers import TeachingRequestEventHandler
from teaching_agent.kafka import publish_teaching_complete
from teaching_agent.worker import process_consumer_batch


class _FakeConsumer:
    def __init__(self, records):
        self._records = records
        self.last_timeout_ms = None

    def poll(self, timeout_ms: int):
        self.last_timeout_ms = timeout_ms
        records = self._records
        self._records = {}
        return records


def _make_ok_output(topic: str, output_mode: str) -> TeachingAgentOutput:
    return TeachingAgentOutput(
        status="ok",
        output_mode=output_mode,
        content=TeachingContent(
            explanation=f"Explanation of {topic}",
            notes="Key points",
            diagram="graph TD\n  A-->B",
        ),
        metadata=TeachingMetadata(topic=topic, tokens_used=300, model="test-model"),
    )


def test_consumer_batch_dispatches_event_from_teaching_topic() -> None:
    message = {
        "request_id": "req-1",
        "session_ctx": {"session_id": "s-1"},
        "topic": "What is a loop?",
        "output_mode": "beginner",
        "context": "",
    }
    consumer = _FakeConsumer({"teaching": [SimpleNamespace(value=message)]})
    captured = []

    processed = process_consumer_batch(
        consumer,
        producer=object(),
        handler=lambda payload, producer: captured.append((payload, producer)),
        poll_timeout_ms=250,
    )

    assert processed == 1
    assert consumer.last_timeout_ms == 250
    assert captured[0][0]["topic"] == "What is a loop?"


def test_request_handler_dispatches_to_teaching_agent() -> None:
    captured = {}

    class _FakeAgent:
        def run(self, raw_input):
            captured["raw_input"] = raw_input
            return _make_ok_output(raw_input["topic"], raw_input["output_mode"])

    published = {}

    def _capture_publish(_producer, event):
        published["event"] = event

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=_capture_publish,
    )
    output = handler.process_request(
        {
            "request_id": "req-2",
            "session_ctx": {"session_id": "s-2"},
            "topic": "What is a loop?",
            "output_mode": "beginner",
            "context": "No prior context.",
        },
        producer=object(),
    )

    assert captured["raw_input"]["topic"] == "What is a loop?"
    assert captured["raw_input"]["output_mode"] == "beginner"
    assert output.status == "ok"
    assert published["event"].request_id == "req-2"
    assert published["event"].session_ctx == {"session_id": "s-2"}


def test_ingest_to_dispatch_flow_preserves_request_id() -> None:
    class _FakeAgent:
        def run(self, raw_input):
            return _make_ok_output(raw_input["topic"], raw_input["output_mode"])

    published = {}

    def _capture_publish(_producer, event):
        published["request_id"] = event.request_id

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=_capture_publish,
    )
    consumer = _FakeConsumer(
        {
            "teaching": [
                SimpleNamespace(
                    topic="teaching",
                    value={
                        "request_id": "req-ingest-1",
                        "session_ctx": {"session_id": "s-10"},
                        "topic": "What is recursion?",
                        "output_mode": "intermediate",
                        "context": "",
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


def test_publish_teaching_complete_sends_to_correct_topic() -> None:
    sent = {}

    class _FakeProducer:
        def send(self, topic, payload):
            sent["topic"] = topic
            sent["payload"] = payload

        def flush(self):
            sent["flushed"] = True

    event = _make_completion_event()
    publish_teaching_complete(_FakeProducer(), event)

    assert sent["topic"] == "teaching-complete"
    assert sent["payload"]["request_id"] == event.request_id
    assert sent["flushed"] is True


def test_completion_event_preserves_request_correlation() -> None:
    class _FakeAgent:
        def run(self, raw_input):
            return _make_ok_output(raw_input["topic"], raw_input["output_mode"])

    fixed_times = iter([
        datetime(2026, 6, 13, 10, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 13, 10, 0, 2, tzinfo=timezone.utc),
    ])
    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda _producer, _event: None,
        clock=lambda: next(fixed_times),
    )

    output = handler.process_request(
        {
            "request_id": "req-3",
            "session_ctx": {"session_id": "s-3", "trace_id": "trace-1"},
            "topic": "What is gradient descent?",
            "output_mode": "advanced",
            "context": "",
        },
        producer=object(),
    )

    assert output.request_id == "req-3"
    assert output.session_ctx["trace_id"] == "trace-1"
    assert output.topic == "What is gradient descent?"
    assert output.duration_ms == 2000


def test_lifecycle_logging_covers_consume_process_and_publish(caplog) -> None:
    import logging

    class _FakeAgent:
        def run(self, raw_input):
            return _make_ok_output(raw_input["topic"], raw_input["output_mode"])

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda _producer, _event: None,
    )
    consumer = _FakeConsumer(
        {
            "teaching": [
                SimpleNamespace(
                    topic="teaching",
                    value={
                        "request_id": "req-5",
                        "session_ctx": {"session_id": "s-5"},
                        "topic": "What is a stack?",
                        "output_mode": "beginner",
                        "context": "",
                    },
                )
            ]
        }
    )

    with caplog.at_level(logging.INFO):
        process_consumer_batch(
            consumer,
            producer=object(),
            handler=handler.process_request,
            poll_timeout_ms=100,
        )

    messages = [r.message for r in caplog.records]
    assert any("consumed" in m for m in messages)
    assert any("processing_started" in m or "processing_completed" in m for m in messages)
    assert any("publish_completed" in m for m in messages)


def test_error_stage_logged_when_processing_fails(caplog) -> None:
    import logging

    class _FailingAgent:
        def run(self, raw_input):
            raise RuntimeError("synthetic processing failure")

    handler = TeachingRequestEventHandler(
        agent_factory=_FailingAgent,
        publisher=lambda _producer, _event: None,
    )
    consumer = _FakeConsumer(
        {
            "teaching": [
                SimpleNamespace(
                    topic="teaching",
                    value={
                        "request_id": "req-6",
                        "session_ctx": {"session_id": "s-6"},
                        "topic": "What is a queue?",
                        "output_mode": "beginner",
                        "context": "",
                    },
                )
            ]
        }
    )

    with caplog.at_level(logging.ERROR):
        process_consumer_batch(
            consumer,
            producer=object(),
            handler=handler.process_request,
            poll_timeout_ms=100,
        )

    error_messages = [r.message for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_messages
    assert any("processing_failed" in m or "synthetic processing failure" in m for m in error_messages)


def _make_completion_event():
    from project.schemas import TeachingCompletionEvent, TeachingContent

    return TeachingCompletionEvent(
        request_id="req-4",
        session_ctx={"session_id": "s-4"},
        topic="What is a loop?",
        output_mode="beginner",
        status="ok",
        content=TeachingContent(
            explanation="A loop repeats a block of code.",
            notes="Key points about loops",
            diagram="graph TD\n  A-->B",
        ),
        tokens_used=300,
        model="test-model",
        started_at="2026-06-13T10:00:00Z",
        completed_at="2026-06-13T10:00:01Z",
        duration_ms=1000,
    )
