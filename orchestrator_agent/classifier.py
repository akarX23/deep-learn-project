"""Query complexity detection and learner level assessment."""

from __future__ import annotations

import logging
import re
from typing import Any

from orchestrator_agent.config import LLMConfig
from orchestrator_agent.llm_client import call_llm_json
from orchestrator_agent.prompts import LEARNER_LEVEL_PROMPT
from project.schemas import UserLevelEnum, LearnerProfile

logger = logging.getLogger(__name__)

# Heuristic thresholds for complexity detection.
_COMPLEX_WORD_THRESHOLD = 5
_QUIZ_KEYWORDS: frozenset[str] = frozenset({
    "quiz", "test", "question", "questions", "practice", "evaluate",
    "assess", "exercise", "exam", "challenge", "check",
})
_MULTI_INTENT_CONNECTORS = re.compile(
    r"\b(and|also|then|after|before|additionally|furthermore|plus|as well as)\b",
    re.IGNORECASE,
)
_INJECTION_PATTERNS = re.compile(
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions|"
    r"ignore\s+all\s+instructions|"
    r"you\s+are\s+now|act\s+as\s+if|forget\s+everything|"
    r"system\s*:\s*|<\s*/?system\s*>|"
    r"jailbreak|DAN\s+mode",
    re.IGNORECASE,
)


def detect_complexity(query: str) -> str:
    """Classify a query as SIMPLE or COMPLEX using heuristics.

    Returns "COMPLEX" for short, vague, multi-intent, or injection-pattern queries.
    Returns "SIMPLE" for clear, sufficiently long, single-intent queries.
    """
    stripped = query.strip()
    word_count = len(stripped.split())

    if word_count < _COMPLEX_WORD_THRESHOLD:
        return "COMPLEX"

    if _INJECTION_PATTERNS.search(stripped):
        return "COMPLEX"

    connector_hits = len(_MULTI_INTENT_CONNECTORS.findall(stripped))
    if connector_hits >= 2:
        return "COMPLEX"

    # Queries ending with "?" and very short are ambiguous.
    if stripped.endswith("?") and word_count < 8:
        return "COMPLEX"

    return "SIMPLE"


def contains_injection_pattern(query: str) -> bool:
    """Return True if the query matches known prompt injection patterns."""
    return bool(_INJECTION_PATTERNS.search(query))


def detect_quiz_intent(query: str) -> bool:
    """Return True if the query contains quiz-intent keywords (rule-based, no LLM).

    Matches any word in the query against the quiz keyword set.
    """
    words = {w.strip("?!.,;:") for w in query.lower().split()}
    return bool(words & _QUIZ_KEYWORDS)


def assess_learner_level(
    user_query: str,
    session_context: list[Any],
    config: LLMConfig,
) -> LearnerProfile:
    """Assess the learner's proficiency level using an LLM call.

    Falls back to intermediate/0.5 confidence on any LLM or parse failure.
    """
    context_str = _format_session_context(session_context)
    prompt = LEARNER_LEVEL_PROMPT.format(
        user_query=user_query,
        session_context=context_str or "(none)",
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

    try:
        data = call_llm_json(messages, config)
        level_str = str(data.get("level", "intermediate")).lower()
        confidence = float(data.get("confidence", 0.5))
        reasoning = str(data.get("reasoning", "Assessed from query signals."))

        # Clamp confidence and validate level.
        confidence = max(0.0, min(1.0, confidence))
        try:
            level = UserLevelEnum(level_str)
        except ValueError:
            logger.warning("unknown_level level=%s defaulting to intermediate", level_str)
            level = UserLevelEnum.INTERMEDIATE
            confidence = min(confidence, 0.5)

        return LearnerProfile(
            learner_level=level,
            confidence_score=confidence,
            level_reasoning=reasoning or "No reasoning provided.",
        )

    except Exception as exc:
        logger.warning("assess_learner_level_failed error=%s using default", exc)
        return LearnerProfile(
            learner_level=UserLevelEnum.INTERMEDIATE,
            confidence_score=0.5,
            level_reasoning="Level assessment failed; defaulting to intermediate.",
        )


def _format_session_context(session_context: list[Any]) -> str:
    """Render session context turns as a readable string."""
    if not session_context:
        return ""
    lines = []
    for turn in session_context:
        if isinstance(turn, dict):
            role = turn.get("role", "user")
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")
        else:
            lines.append(str(turn))
    return "\n".join(lines)
