"""Tests verifying that when RAG-compiled context is provided, the Teaching Agent
prioritises it as the primary source over general knowledge.

Strategy: each test embeds distinctive phrases in `context` that a generic
LLM explanation would never produce unprompted (e.g. specific course terms,
named operations, exact load-factor values). Assertions check that at least
one of those phrases appears in the raw_markdown output.

Makes real LLM calls. Saves input + output files to teaching_agent/tests/outputs/
so the content can be inspected manually.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from teaching_agent.agent import TeachingAgent

_OUTPUT_DIR = Path(__file__).parent / "outputs"
_OUTPUT_DIR.mkdir(exist_ok=True)

_noop = lambda f, t: None


def _save(prefix: str, input_data: dict, raw_markdown: str, result_json: str) -> None:
    (_OUTPUT_DIR / f"{prefix}_input.json").write_text(
        json.dumps(input_data, indent=2), encoding="utf-8"
    )
    (_OUTPUT_DIR / f"{prefix}_output.md").write_text(raw_markdown, encoding="utf-8")
    (_OUTPUT_DIR / f"{prefix}_result.json").write_text(result_json, encoding="utf-8")


# ---------------------------------------------------------------------------
# Beginner — Stack
# Context contains: "peek", "stack overflow", "browser history navigation",
# "undo functionality", "function call management"
# A generic explanation would not mention all three real-world applications
# together, or use "peek" as a named operation unprompted.
# ---------------------------------------------------------------------------

_BEGINNER_INPUT = {
    "topic": "Stack data structure",
    "output_mode": "beginner",
    "context": (
        "In our course, a stack is a LIFO (Last In, First Out) data structure. "
        "Key operations taught in Lecture 4:\n"
        "  - push: add an element to the top\n"
        "  - pop: remove the top element\n"
        "  - peek: view the top element without removing it\n"
        "The course identifies three real-world applications: (1) browser history "
        "navigation (back button), (2) undo functionality in text editors, and "
        "(3) function call management via the call stack in programming languages. "
        "'Stack overflow' occurs when the stack exceeds its maximum capacity — "
        "this is the origin of the website name stackoverflow.com."
    ),
}

_BEGINNER_CONTEXT_PHRASES = ["peek", "browser history", "undo", "call stack", "stack overflow"]


def test_beginner_prioritises_rag_context():
    result, raw_markdown = TeachingAgent().run(_BEGINNER_INPUT, _noop)

    _save("context_priority_beginner", _BEGINNER_INPUT, raw_markdown, result.model_dump_json(indent=2))

    assert result.status == "ok", f"Agent returned error: {result}"
    assert result.content is not None

    lower = raw_markdown.lower()
    matched = [p for p in _BEGINNER_CONTEXT_PHRASES if p.lower() in lower]
    assert matched, (
        f"Expected at least one context-specific phrase in output.\n"
        f"Looked for: {_BEGINNER_CONTEXT_PHRASES}\n"
        f"None found in output (first 500 chars):\n{raw_markdown[:500]}"
    )


# ---------------------------------------------------------------------------
# Intermediate — Hash Tables
# Context contains: "load factor α below 0.7", "open addressing",
# "separate chaining", "linear probing", "2/3 threshold"
# A generic explanation rarely cites a specific load-factor threshold.
# ---------------------------------------------------------------------------

_INTERMEDIATE_INPUT = {
    "topic": "Hash tables",
    "output_mode": "intermediate",
    "context": (
        "From the course notes on hash tables:\n"
        "  - Hash index formula: index = hash(key) % table_size\n"
        "  - Two collision resolution strategies are covered: open addressing "
        "(specifically linear probing) and separate chaining.\n"
        "  - The course emphasises that the load factor α (number of entries / "
        "table size) should be kept below 0.7 to maintain O(1) average performance.\n"
        "  - Instructor note: Python's built-in dict uses open addressing with a "
        "load factor threshold of approximately 2/3, after which the table is resized.\n"
        "  - Worst-case lookup degrades to O(n) when many collisions cluster "
        "(primary clustering in linear probing)."
    ),
}

_INTERMEDIATE_CONTEXT_PHRASES = [
    "load factor", "open addressing", "separate chaining",
    "linear probing", "0.7", "2/3", "primary clustering",
]


def test_intermediate_prioritises_rag_context():
    result, raw_markdown = TeachingAgent().run(_INTERMEDIATE_INPUT, _noop)

    _save("context_priority_intermediate", _INTERMEDIATE_INPUT, raw_markdown, result.model_dump_json(indent=2))

    assert result.status == "ok", f"Agent returned error: {result}"
    assert result.content is not None

    lower = raw_markdown.lower()
    matched = [p for p in _INTERMEDIATE_CONTEXT_PHRASES if p.lower() in lower]
    assert len(matched) >= 2, (
        f"Expected at least 2 context-specific phrases in output.\n"
        f"Looked for: {_INTERMEDIATE_CONTEXT_PHRASES}\n"
        f"Only matched: {matched}\n"
        f"Output (first 500 chars):\n{raw_markdown[:500]}"
    )


# ---------------------------------------------------------------------------
# Advanced — Transformer Attention
# Context contains: "d_model=512", "sqrt(d_k)", "saturation",
# "sinusoidal positional encoding", "Vaswani et al."
# Generic explanations rarely cite all original hyperparameters together.
# ---------------------------------------------------------------------------

_ADVANCED_INPUT = {
    "topic": "Scaled dot-product attention in Transformers",
    "output_mode": "advanced",
    "context": (
        "From Vaswani et al. (2017) — Attention is All You Need:\n"
        "  - Model dimensions: d_model=512, d_ff=2048, h=8 attention heads.\n"
        "  - Scaled dot-product attention formula:\n"
        "    Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V\n"
        "  - The sqrt(d_k) scaling factor is critical: without it, large d_k values "
        "cause dot products to grow in magnitude, pushing softmax into saturation "
        "regions where gradients vanish.\n"
        "  - Positional encoding uses sinusoidal functions:\n"
        "    PE(pos, 2i) = sin(pos / 10000^(2i/d_model))\n"
        "  - Course note: multi-head attention allows the model to jointly attend "
        "to information from different representation subspaces at different positions."
    ),
}

_ADVANCED_CONTEXT_PHRASES = [
    "sqrt(d_k)", "saturation", "sinusoidal", "vaswani",
    "d_model", "d_ff", "positional encoding",
]


def test_advanced_prioritises_rag_context():
    result, raw_markdown = TeachingAgent().run(_ADVANCED_INPUT, _noop)

    _save("context_priority_advanced", _ADVANCED_INPUT, raw_markdown, result.model_dump_json(indent=2))

    assert result.status == "ok", f"Agent returned error: {result}"
    assert result.content is not None

    lower = raw_markdown.lower()
    matched = [p for p in _ADVANCED_CONTEXT_PHRASES if p.lower() in lower]
    assert len(matched) >= 2, (
        f"Expected at least 2 context-specific phrases in output.\n"
        f"Looked for: {_ADVANCED_CONTEXT_PHRASES}\n"
        f"Only matched: {matched}\n"
        f"Output (first 500 chars):\n{raw_markdown[:500]}"
    )
