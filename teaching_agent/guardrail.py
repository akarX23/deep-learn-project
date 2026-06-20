"""Guardrail classification for the Teaching Agent (Phase 6).

Classifies user input before the main pipeline runs. Non-learning inputs
(greeting, off_topic, unclear) get canned responses. valid_question passes through.
"""

from __future__ import annotations

import json
from typing import Any

from teaching_agent.config import LLMConfig
from teaching_agent.llm_client import call_llm
from teaching_agent.prompts import GUARDRAIL_PROMPT

_VALID_CATEGORIES: frozenset[str] = frozenset(
    {"greeting", "off_topic", "unclear", "valid_question"}
)

_CANNED_RESPONSES: dict[str, str] = {
    "greeting": (
        "Hi there! I'm your AI tutor. What topic would you like to learn about? "
        "I can explain concepts at beginner, intermediate, or advanced depth."
    ),
    "off_topic": (
        "I'm a specialized learning assistant for educational topics. "
        "I'm not able to help with that, but I'd love to explain any concept you're curious about!"
    ),
    "unclear": (
        "I'd be happy to help! Could you clarify what you'd like to learn? "
        "Try asking about a specific concept, algorithm, data structure, or topic."
    ),
}


def get_canned_response(category: str) -> str | None:
    """Return the canned text for a non-valid_question category, or None."""
    return _CANNED_RESPONSES.get(category)


class GuardrailClassifier:
    """Classifies a user prompt before the main teaching pipeline runs."""

    def classify(self, topic: str, config: LLMConfig) -> str:
        """Classify *topic* into one of the four guardrail categories.

        Returns the category string on success.
        Returns "valid_question" on any exception or malformed response (fail-open).
        """
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": GUARDRAIL_PROMPT.format(topic=topic)}
        ]
        try:
            raw, _ = call_llm(messages, config)
            parsed = json.loads(raw)
            category = parsed.get("category", "")
            if category in _VALID_CATEGORIES:
                return category
        except Exception:  # noqa: BLE001
            pass
        return "valid_question"
