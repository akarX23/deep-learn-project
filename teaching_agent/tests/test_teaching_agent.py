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
from teaching_agent.helpers import parse_markdown_response
from teaching_agent.validators import validate_mermaid

def _noop(field, token):  # no-op token callback for all integration tests
    return None


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
# Helper: parse_markdown_response
# ---------------------------------------------------------------------------


class TestParseMarkdownResponse:
    def test_all_four_sections(self):
        raw = (
            "**Explanation**\nA clear explanation.\n\n"
            "**Diagram**\ngraph TD\n  A --> B\n\n"
            "**Notes**\n- Key point\n\n"
            "**Example**\nHere is an example."
        )
        result = parse_markdown_response(raw)
        assert result["explanation"] == "A clear explanation."
        assert "graph TD" in result["diagram"]
        assert result["notes"] == "- Key point"
        assert result["example"] == "Here is an example."

    def test_diagram_absent_returns_none(self):
        raw = "**Explanation**\nA clear explanation.\n\n**Notes**\n- Key point"
        result = parse_markdown_response(raw)
        assert result["diagram"] is None

    def test_example_absent_returns_none(self):
        raw = "**Explanation**\nA clear explanation.\n\n**Notes**\n- Key point"
        result = parse_markdown_response(raw)
        assert result["example"] is None

    def test_code_fence_inside_example_preserved(self):
        raw = (
            "**Explanation**\nExplanation here.\n\n"
            "**Notes**\nNotes here.\n\n"
            "**Example**\n```python\nprint('hello')\n```"
        )
        result = parse_markdown_response(raw)
        assert "```python" in result["example"]

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_markdown_response("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse_markdown_response("   ")

    def test_missing_explanation_raises(self):
        raw = "**Notes**\nSome notes.\n\n**Example**\nSome example."
        with pytest.raises(ValueError, match="explanation"):
            parse_markdown_response(raw)

    def test_missing_notes_raises(self):
        raw = "**Explanation**\nSome explanation.\n\n**Example**\nSome example."
        with pytest.raises(ValueError, match="notes"):
            parse_markdown_response(raw)

    def test_empty_explanation_raises(self):
        raw = "**Explanation**\n   \n\n**Notes**\nSome notes."
        with pytest.raises(ValueError, match="explanation"):
            parse_markdown_response(raw)

    def test_case_insensitive_headers(self):
        raw = "**explanation**\nA clear explanation.\n\n**NOTES**\n- Key point"
        result = parse_markdown_response(raw)
        assert result["explanation"] == "A clear explanation."
        assert result["notes"] == "- Key point"


# ---------------------------------------------------------------------------
# Agent: TeachingAgent.run — real LLM calls
# ---------------------------------------------------------------------------


class TestTeachingAgentRun:
    def test_beginner_success(self):
        result, raw_markdown = TeachingAgent().run(
            {"topic": "What is a loop?", "output_mode": "beginner"}, _noop)
        assert result.status == "ok"
        assert result.output_mode == OutputMode.BEGINNER
        assert result.content is not None
        assert result.content.explanation
        assert result.content.notes
        assert result.content.diagram is not None  # required in beginner mode
        assert result.metadata.tokens_used > 0
        assert "**Explanation**" in raw_markdown

    def test_intermediate_success(self):
        result, raw_markdown = TeachingAgent().run(
            {"topic": "Recursion", "output_mode": "intermediate"}, _noop)
        assert result.status == "ok"
        assert result.output_mode == OutputMode.INTERMEDIATE
        assert result.content is not None
        assert result.content.explanation
        assert result.content.notes

    def test_advanced_success(self):
        result, raw_markdown = TeachingAgent().run(
            {"topic": "Concurrency", "output_mode": "advanced"}, _noop)
        assert result.status == "ok"
        assert result.output_mode == OutputMode.ADVANCED
        assert result.content is not None
        assert result.content.explanation
        assert result.content.notes

    def test_invalid_input_empty_topic_returns_error(self):
        # Fails at Pydantic validation — no LLM call made
        result, raw_markdown = TeachingAgent().run(
            {"topic": "", "output_mode": "beginner"}, _noop)
        assert result.status == "error"
        assert result.content is None
        assert result.metadata.tokens_used == 0
        assert raw_markdown == ""

    def test_invalid_input_missing_topic_returns_error(self):
        # Fails at Pydantic validation — no LLM call made
        result, raw_markdown = TeachingAgent().run(
            {"output_mode": "beginner"}, _noop)
        assert result.status == "error"
        assert result.content is None
        assert raw_markdown == ""

    def test_llm_failure_returns_error(self, monkeypatch):
        # Force LiteLLM to fail by pointing at a nonexistent model
        monkeypatch.setenv("TEACHING_MODEL", "openai/nonexistent-model-xyz-9999")
        result, raw_markdown = TeachingAgent().run(
            {"topic": "Loops", "output_mode": "beginner"}, _noop)
        assert result.status == "error"
        assert result.content is None
        assert raw_markdown == ""

    def test_large_context_handled_without_error(self):
        # 5000-char context is silently truncated to 4000 before the LLM call
        result, raw_markdown = TeachingAgent().run({
            "topic": "What is a variable?",
            "output_mode": "beginner",
            "context": "x" * 5000,
        }, _noop)
        assert result.status == "ok"
        assert result.content is not None

    def test_output_is_valid_pydantic_model(self):
        result, _ = TeachingAgent().run(
            {"topic": "Binary Search", "output_mode": "intermediate"}, _noop)
        assert isinstance(result, TeachingAgentOutput)
        dumped = result.model_dump_json()
        assert "status" in dumped

    def test_metadata_reflects_correct_topic_and_model(self):
        result, _ = TeachingAgent().run(
            {"topic": "Binary Search", "output_mode": "advanced"}, _noop)
        assert result.metadata.topic == "Binary Search"
        assert result.metadata.model  # non-empty model string


# ---------------------------------------------------------------------------
# Reflection loop (Phase 3) — fully offline. Generation streams markdown via
# call_llm_stream; critique/revision use call_llm (JSON). Both are monkeypatched.
# Reflection is OFF in the integrated flow (env N=0); these tests exercise it in
# isolation by setting TEACHING_MAX_REFLECTION_ITERATIONS explicitly.
# ---------------------------------------------------------------------------


# Generation comes back as streamed markdown (bold-header sections).
_GEN_MD = (
    "**Explanation**\ngen exp\n\n"
    "**Diagram**\ngraph TD\n  A --> B\n\n"
    "**Notes**\ngen notes\n\n"
    "**Example**\ngen ex"
)
# Critique + revision are JSON (the reflection round-trip).
_CRITIQUE = json.dumps({
    "quality_score": 6,
    "issues": [{"field": "notes", "issue": "too thin", "severity": "medium"}],
    "revision_instructions": "expand the notes",
})
_REVISION = json.dumps({
    "explanation": "rev exp",
    "diagram": "graph TD\n  A --> B",
    "notes": "rev notes expanded",
    "example": "rev ex",
})
_REVISION_2 = json.dumps({
    "explanation": "rev2 exp",
    "diagram": "graph TD\n  A --> B",
    "notes": "rev2 notes",
    "example": "rev2 ex",
})
_REVISION_BAD_DIAGRAM = json.dumps({
    "explanation": "rev exp",
    "diagram": "this is not valid mermaid",
    "notes": "rev notes",
    "example": "rev ex",
})
# Markdown retry response for the beginner diagram regeneration (parse_markdown_response);
# kept invalid so the fallback template is used.
_RETRY_BAD_MD = "**Explanation**\nx\n\n**Diagram**\nstill not valid\n\n**Notes**\ny"


def _streamer(markdown: str, tokens: int):
    """Build a fake call_llm_stream that yields the whole markdown as one chunk."""
    def _call_llm_stream(messages, config):
        yield markdown, tokens
    return _call_llm_stream


class _ScriptedCallLLM:
    """Fake call_llm returning a fixed sequence of (content, tokens) tuples.

    A sequence item that is an Exception is raised instead of returned, to
    simulate an LLM/transport failure on that call.
    """

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def __call__(self, messages, config):
        item = self._responses[self.calls]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def _reflection_env(monkeypatch, iterations=None, mode="beginner"):
    """Make reflection config hermetic: pin the model and control N for the mode."""
    monkeypatch.setenv("TEACHING_MODEL", "test/model")
    monkeypatch.delenv(f"TEACHING_{mode.upper()}_MAX_REFLECTION_ITERATIONS", raising=False)
    if iterations is None:
        monkeypatch.delenv("TEACHING_MAX_REFLECTION_ITERATIONS", raising=False)
    else:
        monkeypatch.setenv("TEACHING_MAX_REFLECTION_ITERATIONS", str(iterations))


def _patch_llm(monkeypatch, call_llm_responses, gen_md=_GEN_MD, gen_tokens=100):
    """Mock generation (call_llm_stream -> markdown) and reflection (call_llm -> JSON)."""
    monkeypatch.setattr(agent_module, "call_llm_stream", _streamer(gen_md, gen_tokens))
    fake = _ScriptedCallLLM(call_llm_responses)
    monkeypatch.setattr(agent_module, "call_llm", fake)
    return fake


class TestReflection:
    def test_reflection_disabled_when_iterations_zero(self, monkeypatch):
        _reflection_env(monkeypatch, 0)
        fake = _patch_llm(monkeypatch, [])
        result, _ = TeachingAgent().run(
            {"topic": "loops", "output_mode": "beginner", "context": ""}, _noop)
        assert fake.calls == 0  # no reflection calls; generation is call_llm_stream
        assert result.status == "ok"
        assert result.metadata.reflection_iterations == 0
        assert result.content.explanation == "gen exp"

    def test_reflection_runs_one_iteration_by_default(self, monkeypatch):
        _reflection_env(monkeypatch, None)  # no env vars -> code default of 1
        fake = _patch_llm(monkeypatch, [(_CRITIQUE, 50), (_REVISION, 120)])
        result, _ = TeachingAgent().run(
            {"topic": "loops", "output_mode": "beginner", "context": ""}, _noop)
        assert fake.calls == 2  # critique + revision (generation is call_llm_stream)
        assert result.status == "ok"
        assert result.metadata.reflection_iterations == 1
        assert result.content.explanation == "rev exp"  # revision, not the initial draft

    def test_reflection_falls_back_on_critique_failure(self, monkeypatch):
        _reflection_env(monkeypatch, 1)
        fake = _patch_llm(monkeypatch, [RuntimeError("critique boom")])
        result, _ = TeachingAgent().run(
            {"topic": "loops", "output_mode": "beginner", "context": ""}, _noop)
        assert fake.calls == 1
        assert result.status == "ok"
        assert result.metadata.reflection_iterations == 0
        assert result.content.explanation == "gen exp"      # initial generation
        assert result.metadata.tokens_used == 100           # failed critique added no tokens

    def test_reflection_falls_back_on_revision_failure(self, monkeypatch):
        _reflection_env(monkeypatch, 1)
        fake = _patch_llm(monkeypatch, [(_CRITIQUE, 50), RuntimeError("revision boom")])
        result, _ = TeachingAgent().run(
            {"topic": "loops", "output_mode": "beginner", "context": ""}, _noop)
        assert fake.calls == 2
        assert result.status == "ok"
        assert result.metadata.reflection_iterations == 0
        assert result.content.explanation == "gen exp"      # initial generation
        assert result.metadata.tokens_used == 150           # gen + critique counted (SC-013)

    def test_reflection_tokens_accumulated_across_all_calls(self, monkeypatch):
        _reflection_env(monkeypatch, 1)
        _patch_llm(monkeypatch, [(_CRITIQUE, 50), (_REVISION, 120)])
        result, _ = TeachingAgent().run(
            {"topic": "loops", "output_mode": "beginner", "context": ""}, _noop)
        assert result.metadata.tokens_used == 270           # gen 100 + critique 50 + revision 120

    def test_reflection_two_iterations(self, monkeypatch):
        _reflection_env(monkeypatch, 2)
        fake = _patch_llm(monkeypatch, [
            (_CRITIQUE, 50), (_REVISION, 120),
            (_CRITIQUE, 40), (_REVISION_2, 110),
        ])
        result, _ = TeachingAgent().run(
            {"topic": "loops", "output_mode": "beginner", "context": ""}, _noop)
        assert fake.calls == 4
        assert result.metadata.reflection_iterations == 2
        assert result.content.explanation == "rev2 exp"     # final revision

    def test_reflection_preserves_diagram_rules_in_revision(self, monkeypatch):
        _reflection_env(monkeypatch, 1)
        # revision returns invalid mermaid; beginner retry (markdown) also invalid -> fallback template
        _patch_llm(monkeypatch, [
            (_CRITIQUE, 50), (_REVISION_BAD_DIAGRAM, 120), (_RETRY_BAD_MD, 30),
        ])
        result, _ = TeachingAgent().run(
            {"topic": "loops", "output_mode": "beginner", "context": ""}, _noop)
        assert result.status == "ok"
        assert result.metadata.reflection_iterations == 1
        assert result.content.diagram is not None
        assert validate_mermaid(result.content.diagram)     # fallback template is valid

    def test_metadata_reflection_iterations_is_zero_when_disabled(self, monkeypatch):
        _reflection_env(monkeypatch, 0)
        _patch_llm(monkeypatch, [])
        result, _ = TeachingAgent().run(
            {"topic": "loops", "output_mode": "beginner", "context": ""}, _noop)
        assert result.metadata.reflection_iterations == 0
