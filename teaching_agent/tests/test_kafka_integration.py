from __future__ import annotations

# from datetime import datetime, timezone  # removed: clock param no longer in handler; new schema has no timing fields
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


class _FakeProducer:
    def __init__(self):
        self.sent = []
        self.flush_count = 0

    def send(self, topic, payload):
        self.sent.append((topic, payload))

    def flush(self):
        self.flush_count += 1

    def close(self):
        pass


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
        # Old fields (pre-master-merge schema):
        # "session_ctx": {"session_id": "s-1"},
        # "topic": "What is a loop?",
        # "output_mode": "beginner",
        # "context": "",
        "sid": "s-1",
        "user_prompt": "What is a loop?",
        "user_level": "beginner",
        "rag_compiled": "",
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
    # Old assertion: captured[0][0]["topic"] == "What is a loop?"
    assert captured[0][0]["user_prompt"] == "What is a loop?"


def test_request_handler_dispatches_to_teaching_agent() -> None:
    captured = {}

    class _FakeAgent:
        def run(self, raw_input, token_callback):
            captured["raw_input"] = raw_input
            return (
                _make_ok_output(raw_input["topic"], raw_input["output_mode"]),
                "**Explanation**\nExplanation of the topic\n\n**Notes**\nKey points",
            )

    published = {}

    def _capture_publish(_producer, event):
        published["event"] = event

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=_capture_publish,
        stream_publisher=lambda p, e: None,
    )
    output = handler.process_request(
        {
            "request_id": "req-2",
            # Old fields (pre-master-merge schema):
            # "session_ctx": {"session_id": "s-2"},
            # "topic": "What is a loop?",
            # "output_mode": "beginner",
            # "context": "No prior context.",
            "sid": "s-2",
            "user_prompt": "What is a loop?",
            "user_level": "beginner",
            "rag_compiled": "No prior context.",
        },
        producer=object(),
    )

    assert captured["raw_input"]["topic"] == "What is a loop?"
    assert captured["raw_input"]["output_mode"] == "beginner"
    # Old assertion: output.status == "ok" (status removed from TeachingCompletionEvent)
    assert output is not None
    assert published["event"].request_id == "req-2"
    # Old assertion: published["event"].session_ctx == {"session_id": "s-2"}
    assert published["event"].sid == "s-2"


def test_ingest_to_dispatch_flow_preserves_request_id() -> None:
    class _FakeAgent:
        def run(self, raw_input, token_callback):
            return (
                _make_ok_output(raw_input["topic"], raw_input["output_mode"]),
                "**Explanation**\nExplanation\n\n**Notes**\nNotes",
            )

    published = {}

    def _capture_publish(_producer, event):
        published["request_id"] = event.request_id

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=_capture_publish,
        stream_publisher=lambda p, e: None,
    )
    consumer = _FakeConsumer(
        {
            "teaching": [
                SimpleNamespace(
                    topic="teaching",
                    value={
                        "request_id": "req-ingest-1",
                        # Old fields (pre-master-merge schema):
                        # "session_ctx": {"session_id": "s-10"},
                        # "topic": "What is recursion?",
                        # "output_mode": "intermediate",
                        # "context": "",
                        "sid": "s-10",
                        "user_prompt": "What is recursion?",
                        "user_level": "intermediate",
                        "rag_compiled": "",
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
        def run(self, raw_input, token_callback):
            return (
                _make_ok_output(raw_input["topic"], raw_input["output_mode"]),
                "**Explanation**\nGradient descent explanation\n\n**Notes**\nKey points",
            )

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda _producer, _event: None,
        stream_publisher=lambda p, e: None,
    )

    output = handler.process_request(
        {
            "request_id": "req-3",
            "sid": "s-3",
            "user_prompt": "What is gradient descent?",
            "user_level": "advanced",
            "rag_compiled": "",
        },
        producer=object(),
    )

    assert output.request_id == "req-3"
    assert output.sid == "s-3"
    assert output.user_level == "advanced"
    assert isinstance(output.content, str)  # Phase 4: raw markdown, not JSON-serialized TeachingContent


def test_lifecycle_logging_covers_consume_process_and_publish(caplog) -> None:
    import logging

    class _FakeAgent:
        def run(self, raw_input, token_callback):
            return (
                _make_ok_output(raw_input["topic"], raw_input["output_mode"]),
                "**Explanation**\nExplanation\n\n**Notes**\nNotes",
            )

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda _producer, _event: None,
        stream_publisher=lambda p, e: None,
    )
    consumer = _FakeConsumer(
        {
            "teaching": [
                SimpleNamespace(
                    topic="teaching",
                    value={
                        "request_id": "req-5",
                        # Old fields (pre-master-merge schema):
                        # "session_ctx": {"session_id": "s-5"},
                        # "topic": "What is a stack?",
                        # "output_mode": "beginner",
                        # "context": "",
                        "sid": "s-5",
                        "user_prompt": "What is a stack?",
                        "user_level": "beginner",
                        "rag_compiled": "",
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
        def run(self, raw_input, token_callback):
            raise RuntimeError("synthetic processing failure")

    handler = TeachingRequestEventHandler(
        agent_factory=_FailingAgent,
        publisher=lambda _producer, _event: None,
        stream_publisher=lambda p, e: None,
    )
    consumer = _FakeConsumer(
        {
            "teaching": [
                SimpleNamespace(
                    topic="teaching",
                    value={
                        "request_id": "req-6",
                        # Old fields (pre-master-merge schema):
                        # "session_ctx": {"session_id": "s-6"},
                        # "topic": "What is a queue?",
                        # "output_mode": "beginner",
                        # "context": "",
                        "sid": "s-6",
                        "user_prompt": "What is a queue?",
                        "user_level": "beginner",
                        "rag_compiled": "",
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


def test_streaming_tokens_published_before_completion_event() -> None:
    publish_order: list[str] = []

    class _FakeAgent:
        def run(self, raw_input, token_callback):
            token_callback("explanation", "Hello world")
            return (
                _make_ok_output(raw_input["topic"], raw_input["output_mode"]),
                "**Explanation**\nHello world\n\n**Notes**\nNotes",
            )

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda p, e: publish_order.append("completion"),
        stream_publisher=lambda p, e: publish_order.append("stream"),
    )
    handler.process_request(
        {"request_id": "r1", "sid": "s1", "user_prompt": "Loops", "user_level": "beginner", "rag_compiled": ""},
        producer=_FakeProducer(),
    )

    stream_indices = [i for i, t in enumerate(publish_order) if t == "stream"]
    completion_indices = [i for i, t in enumerate(publish_order) if t == "completion"]
    assert stream_indices and completion_indices
    assert max(stream_indices) < completion_indices[0]


def test_stream_complete_sentinel_published_on_success() -> None:
    stream_events = []

    class _FakeAgent:
        def run(self, raw_input, token_callback):
            return (
                _make_ok_output(raw_input["topic"], raw_input["output_mode"]),
                "**Explanation**\nContent\n\n**Notes**\nNotes",
            )

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda p, e: None,
        stream_publisher=lambda p, e: stream_events.append(e),
    )
    handler.process_request(
        {"request_id": "r2", "sid": "s2", "user_prompt": "Trees", "user_level": "beginner", "rag_compiled": ""},
        producer=_FakeProducer(),
    )

    last = stream_events[-1]
    assert last.data.get("done") is True
    assert last.data.get("tokens_used") == 300  # matches _make_ok_output metadata
    assert last.from_service == "teaching-agent"


def test_stream_complete_sentinel_published_on_error() -> None:
    stream_events = []

    class _FailingAgent:
        def run(self, raw_input, token_callback):
            raise RuntimeError("agent failure")

    handler = TeachingRequestEventHandler(
        agent_factory=_FailingAgent,
        publisher=lambda p, e: None,
        stream_publisher=lambda p, e: stream_events.append(e),
    )
    handler.process_request(
        {"request_id": "r3", "sid": "s3", "user_prompt": "Trees", "user_level": "beginner", "rag_compiled": ""},
        producer=_FakeProducer(),
    )

    sentinel = stream_events[-1]
    assert sentinel.data.get("done") is True
    assert sentinel.data.get("tokens_used") == 0  # error path: no tokens consumed


def test_diagram_field_in_stream_events() -> None:
    stream_events = []

    class _FakeAgent:
        def run(self, raw_input, token_callback):
            token_callback("explanation", "Some text")
            token_callback("diagram", "graph TD\n  A-->B")
            token_callback("notes", "Key notes")
            return (
                _make_ok_output(raw_input["topic"], raw_input["output_mode"]),
                "**Explanation**\nSome text\n\n**Diagram**\ngraph TD\n  A-->B\n\n**Notes**\nKey notes",
            )

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda p, e: None,
        stream_publisher=lambda p, e: stream_events.append(e),
    )
    handler.process_request(
        {"request_id": "r4", "sid": "s4", "user_prompt": "Trees", "user_level": "beginner", "rag_compiled": ""},
        producer=_FakeProducer(),
    )

    fields = [e.data.get("field") for e in stream_events if "field" in e.data]
    assert "explanation" in fields
    assert "diagram" in fields
    assert "notes" in fields


def test_handler_passes_chat_history_to_agent() -> None:
    """Phase 5: handler maps event.chat_history into the agent.run() input dict."""
    captured = {}

    class _FakeAgent:
        def run(self, raw_input, token_callback):
            captured["raw_input"] = raw_input
            return (
                _make_ok_output(raw_input["topic"], raw_input["output_mode"]),
                "**Explanation**\nFollow-up answer\n\n**Notes**\nNotes",
            )

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda p, e: None,
        stream_publisher=lambda p, e: None,
    )
    history = [
        {"role": "user", "content": "What is gradient descent?"},
        {"role": "assistant", "content": "It is an optimization method."},
    ]
    handler.process_request(
        {
            "request_id": "req-mt-1",
            "sid": "s-mt",
            "user_prompt": "How does momentum change it?",
            "user_level": "intermediate",
            "rag_compiled": "",
            "chat_history": history,
        },
        producer=_FakeProducer(),
    )

    assert captured["raw_input"]["chat_history"] == history
    assert captured["raw_input"]["topic"] == "How does momentum change it?"


def test_handler_defaults_chat_history_when_absent() -> None:
    """Backward compat: an event without chat_history yields [] into the agent."""
    captured = {}

    class _FakeAgent:
        def run(self, raw_input, token_callback):
            captured["raw_input"] = raw_input
            return (
                _make_ok_output(raw_input["topic"], raw_input["output_mode"]),
                "**Explanation**\nAnswer\n\n**Notes**\nNotes",
            )

    handler = TeachingRequestEventHandler(
        agent_factory=_FakeAgent,
        publisher=lambda p, e: None,
        stream_publisher=lambda p, e: None,
    )
    handler.process_request(
        {"request_id": "req-mt-2", "sid": "s2", "user_prompt": "Loops",
         "user_level": "beginner", "rag_compiled": ""},
        producer=_FakeProducer(),
    )

    assert captured["raw_input"]["chat_history"] == []


def test_multi_turn_request_publishes_completion_once() -> None:
    """Phase 5: a request with chat_history still publishes exactly one
    teaching-complete event (publish-once contract preserved)."""
    sent = []

    class _FakeProducerLocal:
        def send(self, topic, payload):
            sent.append((topic, payload))

        def flush(self):
            pass

    class _FakeAgent:
        def run(self, raw_input, token_callback):
            return (
                _make_ok_output(raw_input["topic"], raw_input["output_mode"]),
                "**Explanation**\nFollow-up\n\n**Notes**\nNotes",
            )

    handler = TeachingRequestEventHandler(agent_factory=_FakeAgent)  # real publishers
    handler.process_request(
        {
            "request_id": "req-mt-3",
            "sid": "s3",
            "user_prompt": "Follow up",
            "user_level": "beginner",
            "rag_compiled": "",
            "chat_history": [{"role": "user", "content": "earlier"}],
        },
        producer=_FakeProducerLocal(),
    )

    completions = [p for t, p in sent if t == "teaching-complete"]
    assert len(completions) == 1
    assert completions[0]["request_id"] == "req-mt-3"


def _make_completion_event():
    from project.schemas import TeachingCompletionEvent

    # Old TeachingCompletionEvent (pre-master-merge schema):
    # return TeachingCompletionEvent(
    #     request_id="req-4",
    #     session_ctx={"session_id": "s-4"},
    #     topic="What is a loop?",
    #     output_mode="beginner",
    #     status="ok",
    #     content=TeachingContent(
    #         explanation="A loop repeats a block of code.",
    #         notes="Key points about loops",
    #         diagram="graph TD\n  A-->B",
    #     ),
    #     tokens_used=300,
    #     model="test-model",
    #     started_at="2026-06-13T10:00:00Z",
    #     completed_at="2026-06-13T10:00:01Z",
    #     duration_ms=1000,
    # )
    return TeachingCompletionEvent(
        request_id="req-4",
        sid="s-4",
        user_level="beginner",
        content="",
    )


def test_reflection_enabled_publishes_exactly_once(monkeypatch) -> None:
    """SC-014: with reflection on (N>=1), one consumed request -> exactly one
    TeachingCompletionEvent published to "teaching-complete". Reflection lives
    inside TeachingAgent.run(); it must not change the publish-once contract.
    (The handler also streams token events to "stream-tokens" — those are separate
    and not counted here.)
    """
    import json

    import teaching_agent.agent as agent_module

    monkeypatch.setenv("TEACHING_MODEL", "test/model")
    monkeypatch.setenv("TEACHING_MAX_REFLECTION_ITERATIONS", "1")
    monkeypatch.delenv("TEACHING_BEGINNER_MAX_REFLECTION_ITERATIONS", raising=False)

    # generation streams markdown; critique + revision are JSON via call_llm
    gen_md = "**Explanation**\ng\n\n**Diagram**\ngraph TD\n  A --> B\n\n**Notes**\nn\n\n**Example**\ne"
    crit = json.dumps({"quality_score": 6, "issues": [], "revision_instructions": "looks ok"})
    rev = json.dumps({"explanation": "r", "diagram": "graph TD\n  A --> B", "notes": "n2", "example": "e2"})

    def _gen_stream(messages, config):
        yield gen_md, 100

    monkeypatch.setattr(agent_module, "call_llm_stream", _gen_stream)
    scripted = iter([(crit, 50), (rev, 120)])
    monkeypatch.setattr(agent_module, "call_llm", lambda messages, config: next(scripted))

    sent = []

    class _FakeProducer:
        def send(self, topic, payload):
            sent.append((topic, payload))

        def flush(self):
            pass

    handler = TeachingRequestEventHandler()  # real agent + real publishers
    handler.process_request(
        {
            "request_id": "req-reflect-1",
            "sid": "s-1",
            "user_prompt": "What is a loop?",
            "user_level": "beginner",
            "rag_compiled": "",
        },
        producer=_FakeProducer(),
    )

    completions = [payload for topic, payload in sent if topic == "teaching-complete"]
    assert len(completions) == 1                       # exactly one completion event (SC-014)
    assert completions[0]["request_id"] == "req-reflect-1"
