"""Query rewriting for vague or short user queries."""

from __future__ import annotations

import logging
from typing import Any

from orchestrator_agent.config import LLMConfig
from orchestrator_agent.llm_client import call_llm_json
from orchestrator_agent.prompts import QUERY_REWRITE_PROMPT

logger = logging.getLogger(__name__)


def rewrite_query(user_query: str, learner_level: str, config: LLMConfig) -> str:
    """Expand and clarify a vague or short query using an LLM call.

    Returns the rewritten query on success, or the original query on failure.
    """
    prompt = QUERY_REWRITE_PROMPT.format(
        user_query=user_query,
        learner_level=learner_level,
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

    try:
        data = call_llm_json(messages, config)
        rewritten = str(data.get("rewritten_query", "")).strip()
        if rewritten:
            logger.info(
                "query_rewritten original_words=%d rewritten_words=%d",
                len(user_query.split()),
                len(rewritten.split()),
            )
            return rewritten
    except Exception as exc:
        logger.warning("query_rewrite_failed error=%s using original", exc)

    return user_query
