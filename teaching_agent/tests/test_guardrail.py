"""Unit tests for teaching_agent.guardrail (Phase 6)."""

from __future__ import annotations

import pytest

from teaching_agent.config import LLMConfig
from teaching_agent.guardrail import GuardrailClassifier, get_canned_response

_FAKE_CONFIG = LLMConfig(model="test-model", max_tokens=128, temperature=0.0)


def _make_llm_response(category: str) -> tuple[str, int]:
    return (f'{{"category": "{category}", "reason": "test"}}', 5)


class TestGuardrailClassifier:
    def test_classify_greeting(self, monkeypatch):
        monkeypatch.setattr(
            "teaching_agent.guardrail.call_llm",
            lambda msgs, cfg: _make_llm_response("greeting"),
        )
        assert GuardrailClassifier().classify("Hi", _FAKE_CONFIG) == "greeting"

    def test_classify_off_topic(self, monkeypatch):
        monkeypatch.setattr(
            "teaching_agent.guardrail.call_llm",
            lambda msgs, cfg: _make_llm_response("off_topic"),
        )
        assert GuardrailClassifier().classify("Tell me a joke", _FAKE_CONFIG) == "off_topic"

    def test_classify_unclear(self, monkeypatch):
        monkeypatch.setattr(
            "teaching_agent.guardrail.call_llm",
            lambda msgs, cfg: _make_llm_response("unclear"),
        )
        assert GuardrailClassifier().classify("do it", _FAKE_CONFIG) == "unclear"

    def test_classify_valid_question(self, monkeypatch):
        monkeypatch.setattr(
            "teaching_agent.guardrail.call_llm",
            lambda msgs, cfg: _make_llm_response("valid_question"),
        )
        assert GuardrailClassifier().classify("Explain recursion", _FAKE_CONFIG) == "valid_question"

    def test_classify_fails_open_on_exception(self, monkeypatch):
        def _raise(msgs, cfg):
            raise RuntimeError("LLM unavailable")
        monkeypatch.setattr("teaching_agent.guardrail.call_llm", _raise)
        assert GuardrailClassifier().classify("Hi", _FAKE_CONFIG) == "valid_question"

    def test_classify_fails_open_on_bad_json(self, monkeypatch):
        monkeypatch.setattr(
            "teaching_agent.guardrail.call_llm",
            lambda msgs, cfg: ("not json at all", 5),
        )
        assert GuardrailClassifier().classify("Hi", _FAKE_CONFIG) == "valid_question"

    def test_classify_fails_open_on_missing_category_key(self, monkeypatch):
        monkeypatch.setattr(
            "teaching_agent.guardrail.call_llm",
            lambda msgs, cfg: ('{"reason": "no category here"}', 5),
        )
        assert GuardrailClassifier().classify("Hi", _FAKE_CONFIG) == "valid_question"

    def test_classify_fails_open_on_unknown_category(self, monkeypatch):
        monkeypatch.setattr(
            "teaching_agent.guardrail.call_llm",
            lambda msgs, cfg: ('{"category": "rude", "reason": "x"}', 5),
        )
        assert GuardrailClassifier().classify("Hi", _FAKE_CONFIG) == "valid_question"


class TestGetCannedResponse:
    def test_greeting_returns_non_empty(self):
        result = get_canned_response("greeting")
        assert isinstance(result, str) and len(result) > 0

    def test_off_topic_returns_non_empty(self):
        result = get_canned_response("off_topic")
        assert isinstance(result, str) and len(result) > 0

    def test_unclear_returns_non_empty(self):
        result = get_canned_response("unclear")
        assert isinstance(result, str) and len(result) > 0

    def test_valid_question_returns_none(self):
        assert get_canned_response("valid_question") is None

    def test_unknown_category_returns_none(self):
        assert get_canned_response("something_else") is None
