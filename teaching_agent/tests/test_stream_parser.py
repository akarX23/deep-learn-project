"""Unit tests for StreamingFieldExtractor."""
from __future__ import annotations

from teaching_agent.stream_parser import StreamingFieldExtractor


def _make_extractor():
    """Return (extractor, events_list). Events are (field, token) tuples."""
    events = []
    extractor = StreamingFieldExtractor(lambda f, t: events.append((f, t)))
    return extractor, events


def test_explanation_tokens_emitted_immediately():
    extractor, events = _make_extractor()

    extractor.feed("**Explanation**\nHere is text.")
    # Explanation tokens emitted during feed, not deferred to finalize
    assert any(f == "explanation" for f, t in events)

    extractor.feed(" More text.")
    explanation_count = sum(1 for f, _ in events if f == "explanation")
    assert explanation_count >= 2  # both feeds produced callbacks

    extractor.finalize()


def test_diagram_buffered_and_emitted_complete():
    extractor, events = _make_extractor()

    extractor.feed("**Explanation**\nSome explanation.\n\n")
    extractor.feed("**Diagram**\n")
    extractor.feed("graph TD\n")
    extractor.feed("  A --> B")
    # No diagram events yet — still buffering
    assert not any(f == "diagram" for f, t in events)

    # Next section header triggers diagram flush
    extractor.feed("\n\n**Notes**\nKey points here.")
    diagram_events = [(f, t) for f, t in events if f == "diagram"]
    assert len(diagram_events) == 1
    assert "graph TD" in diagram_events[0][1]
    assert "A --> B" in diagram_events[0][1]
    extractor.finalize()


def test_header_split_across_chunks():
    extractor, events = _make_extractor()

    # Header split across two chunks: "**Explan" + "ation**\n..."
    extractor.feed("**Explan")
    assert not any(f == "explanation" for f, t in events)  # header not yet detected

    extractor.feed("ation**\nThis is the explanation.")
    extractor.finalize()

    explanation_text = "".join(t for f, t in events if f == "explanation")
    assert "This is the explanation." in explanation_text


def test_finalize_flushes_trailing_diagram():
    extractor, events = _make_extractor()

    extractor.feed("**Explanation**\nSome explanation.\n\n")
    extractor.feed("**Diagram**\n")
    extractor.feed("graph TD\n  A --> B")
    # No following header — diagram is still buffered
    assert not any(f == "diagram" for f, t in events)

    extractor.finalize()
    diagram_events = [(f, t) for f, t in events if f == "diagram"]
    assert len(diagram_events) == 1
    assert "graph TD" in diagram_events[0][1]


def test_notes_and_example_stream_immediately():
    extractor, events = _make_extractor()

    extractor.feed("**Notes**\n- Point one")
    assert any(f == "notes" for f, t in events)  # emitted immediately, not buffered

    extractor.feed("**Example**\nHere is code.")
    assert any(f == "example" for f, t in events)  # emitted immediately

    extractor.finalize()


def test_finalize_returns_complete_raw_markdown():
    extractor, events = _make_extractor()

    chunks = [
        "**Explanation**\nExplain it.\n\n",
        "**Diagram**\ngraph TD\n  A --> B\n\n",
        "**Notes**\n- Note one\n\n",
        "**Example**\ncode here",
    ]
    for chunk in chunks:
        extractor.feed(chunk)
    raw = extractor.finalize()

    assert raw == "".join(chunks)
    assert "**Explanation**" in raw
    assert "**Diagram**" in raw
    assert "**Notes**" in raw
    assert "**Example**" in raw


def test_empty_stream_no_callback():
    extractor, events = _make_extractor()

    extractor.feed("")
    extractor.feed("   ")
    extractor.finalize()

    assert events == []
