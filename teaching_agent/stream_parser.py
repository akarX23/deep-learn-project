"""Streaming field extractor for Teaching Agent markdown token stream."""

from __future__ import annotations

import re
from collections.abc import Callable

_SECTION_HEADER_RE = re.compile(r"\*\*(\w+)\*\*", re.IGNORECASE)
_PARTIAL_HEADER_TAIL_RE = re.compile(r"\*{1,2}\w*\*?$")

_STREAMABLE_FIELDS = {"explanation", "notes", "example"}
_BUFFERED_FIELDS = {"diagram"}
_ALL_FIELDS = _STREAMABLE_FIELDS | _BUFFERED_FIELDS


class StreamingFieldExtractor:
    """State machine that processes LLM delta chunks and emits field-keyed token events.

    Streamable fields (explanation, notes, example) are forwarded to token_callback
    immediately per chunk. The diagram field is buffered and emitted as a single event
    when the next section header is detected or finalize() is called.
    """

    def __init__(self, token_callback: Callable[[str, str], None]) -> None:
        self._callback = token_callback
        self._current_field: str | None = None
        self._diagram_buffer: str = ""
        self._raw_buffer: str = ""
        self._chunk_buffer: str = ""  # lookahead for split headers

    def feed(self, chunk: str) -> None:
        self._raw_buffer += chunk
        self._chunk_buffer += chunk

        while True:
            match = _SECTION_HEADER_RE.search(self._chunk_buffer)
            if not match:
                # No complete header — flush streamable content, hold back any
                # trailing '*' chars that could be the start of a split header.
                safe, tail = _split_at_possible_partial_header(self._chunk_buffer)
                if safe and self._current_field in _STREAMABLE_FIELDS:
                    self._callback(self._current_field, safe)
                elif safe and self._current_field == "diagram":
                    self._diagram_buffer += safe
                self._chunk_buffer = tail
                break

            field_name = match.group(1).lower()
            before = self._chunk_buffer[: match.start()]
            self._chunk_buffer = self._chunk_buffer[match.end():]

            # Flush content before this header to the current field
            if before.strip() and self._current_field in _STREAMABLE_FIELDS:
                self._callback(self._current_field, before)
            elif before.strip() and self._current_field == "diagram":
                self._diagram_buffer += before

            # Emit completed diagram before switching to a new field
            if self._current_field == "diagram" and self._diagram_buffer.strip():
                self._callback("diagram", self._diagram_buffer.strip())
                self._diagram_buffer = ""

            if field_name in _ALL_FIELDS:
                self._current_field = field_name

    def finalize(self) -> str:
        """Flush remaining buffer content and return the complete raw markdown string."""
        remaining = self._chunk_buffer
        if remaining.strip():
            if self._current_field in _STREAMABLE_FIELDS:
                self._callback(self._current_field, remaining)
            elif self._current_field == "diagram":
                self._diagram_buffer += remaining

        # Flush any diagram that had no following header
        if self._diagram_buffer.strip():
            self._callback("diagram", self._diagram_buffer.strip())
            self._diagram_buffer = ""

        self._chunk_buffer = ""
        return self._raw_buffer


def _split_at_possible_partial_header(text: str) -> tuple[str, str]:
    """Split text into (safe_to_emit, tail_to_buffer).

    Holds back any suffix that could be the start of an incomplete **Header**
    marker: a single '*', '**', '**Word', or '**Word*' at the end of text.
    """
    match = _PARTIAL_HEADER_TAIL_RE.search(text)
    if match:
        return text[: match.start()], text[match.start():]
    return text, ""
