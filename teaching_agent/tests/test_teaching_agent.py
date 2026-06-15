"""Automated test suite for the Teaching Agent.

Pure Python tests (schema, validator, parse) run offline with no LLM calls.
Agent integration tests make real LLM API calls using the TEACHING_MODEL from .env.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

import teaching_agent.agent as agent_module
from project.schemas import OutputMode, TeachingAgentInput, TeachingAgentOutput
from teaching_agent.agent import TeachingAgent
from teaching_agent.helpers import parse_llm_response
from teaching_agent.validators import validate_mermaid


# ---------------------------------------------------------------------------
# Schema: TeachingAgentInput
# ---------------------------------------------------------------------------


class TestTeachingAgentInputSchema:
    def test_valid_input(self):
        inp = TeachingAgentInput(topic="Recursion", output_mode="beginner")
        assert inp.topic == "Recursion"
        assert inp.output_mode == OutputMode.BEGINNER
        assert inp.context == ""

    def test_valid_with_context(self):
        inp = TeachingAgentInput(topic="Sorting", output_mode="intermediate", context="We covered lists.")
        assert inp.context == "We covered lists."

    def test_rejects_empty_topic(self):
        with pytest.raises(ValidationError):
            TeachingAgentInput(topic="   ", output_mode="beginner")

    def test_rejects_invalid_output_mode(self):
        with pytest.raises(ValidationError):
            TeachingAgentInput(topic="Loops", output_mode="expert")

    def test_all_output_modes_accepted(self):
        for mode in ("beginner", "intermediate", "advanced"):
            inp = TeachingAgentInput(topic="Topic", output_mode=mode)
            assert inp.output_mode.value == mode


# ---------------------------------------------------------------------------
# Validator: validate_mermaid
# ---------------------------------------------------------------------------


class TestValidateMermaid:
    def test_valid_graph_td(self):
        assert validate_mermaid("graph TD\n  A --> B")

    def test_valid_graph_lr(self):
        assert validate_mermaid("graph LR\n  A --> B")

    def test_valid_sequence_diagram(self):
        assert validate_mermaid("sequenceDiagram\n  Alice ->> Bob: Hello")

    def test_valid_flowchart(self):
        assert validate_mermaid("flowchart TD\n  A --> B")

    def test_invalid_empty_string(self):
        assert not validate_mermaid("")

    def test_invalid_whitespace_only(self):
        assert not validate_mermaid("   \n  ")

    def test_invalid_header_only_single_line(self):
        assert not validate_mermaid("graph TD")

    def test_invalid_unrecognized_header(self):
        assert not validate_mermaid("myDiagram\n  A --> B")

    def test_semicolon_separated_counts_as_two_segments(self):
        # validators.py splits on [\n;], so "graph TD; A --> B" has two segments
        assert validate_mermaid("graph TD; A --> B")


# ---------------------------------------------------------------------------
# Helper: parse_llm_response
# ---------------------------------------------------------------------------


class TestParseLlmResponse:
    def test_clean_json(self):
        raw = json.dumps({"explanation": "An explanation.", "notes": "A note."})
        result = parse_llm_response(raw)
        assert result["explanation"] == "An explanation."
        assert result["notes"] == "A note."

    def test_fenced_json_with_language_tag(self):
        inner = {"explanation": "An explanation.", "notes": "A note."}
        raw = "```json\n" + json.dumps(inner) + "\n```"
        result = parse_llm_response(raw)
        assert result["notes"] == "A note."

    def test_fenced_json_without_language_tag(self):
        inner = {"explanation": "An explanation.", "notes": "A note."}
        raw = "```\n" + json.dumps(inner) + "\n```"
        result = parse_llm_response(raw)
        assert result["explanation"] == "An explanation."

    def test_code_fence_inside_json_string_not_stripped(self):
        # A ```python block inside the 'example' field must NOT trigger fence-stripping
        raw = json.dumps({
            "explanation": "Explanation here.",
            "notes": "Notes here.",
            "example": "```python\nprint('hello')\n```",
        })
        result = parse_llm_response(raw)
        assert "```python" in result["example"]

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_llm_response("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_llm_response("   ")

    def test_missing_explanation_raises(self):
        raw = json.dumps({"notes": "A note."})
        with pytest.raises(ValueError, match="explanation"):
            parse_llm_response(raw)

    def test_missing_notes_raises(self):
        raw = json.dumps({"explanation": "An explanation."})
        with pytest.raises(ValueError, match="notes"):
            parse_llm_response(raw)

    def test_empty_explanation_raises(self):
        raw = json.dumps({"explanation": "   ", "notes": "ok"})
        with pytest.raises(ValueError, match="explanation"):
            parse_llm_response(raw)

    def test_non_object_json_raises(self):
        with pytest.raises(ValueError, match="not an object"):
            parse_llm_response('["list", "not", "object"]')


# ---------------------------------------------------------------------------
# Agent: TeachingAgent.run — real LLM calls
# ---------------------------------------------------------------------------


class TestTeachingAgentRun:
    def test_beginner_success(self):
        result = TeachingAgent().run({"topic": "What is a loop?", "output_mode": "beginner"})
        assert result.status == "ok"
        assert result.output_mode == OutputMode.BEGINNER
        assert result.content is not None
        assert result.content.explanation
        assert result.content.notes
        assert result.content.diagram is not None  # required in beginner mode
        assert result.metadata.tokens_used > 0

    def test_intermediate_success(self):
        result = TeachingAgent().run({"topic": "Recursion", "output_mode": "intermediate"})
        assert result.status == "ok"
        assert result.output_mode == OutputMode.INTERMEDIATE
        assert result.content is not None
        assert result.content.explanation
        assert result.content.notes

    def test_advanced_success(self):
        result = TeachingAgent().run({"topic": "Concurrency", "output_mode": "advanced"})
        assert result.status == "ok"
        assert result.output_mode == OutputMode.ADVANCED
        assert result.content is not None
        assert result.content.explanation
        assert result.content.notes

    def test_invalid_input_empty_topic_returns_error(self):
        # Fails at Pydantic validation — no LLM call made
        result = TeachingAgent().run({"topic": "", "output_mode": "beginner"})
        assert result.status == "error"
        assert result.content is None
        assert result.metadata.tokens_used == 0

    def test_invalid_input_missing_topic_returns_error(self):
        # Fails at Pydantic validation — no LLM call made
        result = TeachingAgent().run({"output_mode": "beginner"})
        assert result.status == "error"
        assert result.content is None

    def test_llm_failure_returns_error(self, monkeypatch):
        # Force LiteLLM to fail by pointing at a nonexistent model
        monkeypatch.setenv("TEACHING_MODEL", "openai/nonexistent-model-xyz-9999")
        result = TeachingAgent().run({"topic": "Loops", "output_mode": "beginner"})
        assert result.status == "error"
        assert result.content is None

    def test_large_context_handled_without_error(self):
        # 5000-char context is silently truncated to 4000 before the LLM call
        result = TeachingAgent().run({
            "topic": "What is a variable?",
            "output_mode": "beginner",
            "context": "x" * 5000,
        })
        assert result.status == "ok"
        assert result.content is not None

    def test_output_is_valid_pydantic_model(self):
        result = TeachingAgent().run({"topic": "Binary Search", "output_mode": "intermediate"})
        assert isinstance(result, TeachingAgentOutput)
        dumped = result.model_dump_json()
        assert "status" in dumped

    def test_metadata_reflects_correct_topic_and_model(self):
        result = TeachingAgent().run({"topic": "Binary Search", "output_mode": "advanced"})
        assert result.metadata.topic == "Binary Search"
        assert result.metadata.model  # non-empty model string
