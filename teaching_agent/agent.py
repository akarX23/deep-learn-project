"""Teaching Agent — linear single-step pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from pydantic import ValidationError

from project.schemas import (
    OutputMode,
    TeachingAgentInput,
    TeachingAgentOutput,
    TeachingContent,
    TeachingMetadata,
)
from teaching_agent.config import get_llm_config
from teaching_agent.helpers import build_error_output, build_messages, parse_llm_response
from teaching_agent.llm_client import call_llm
from teaching_agent.prompts import PROMPT_BY_MODE
from teaching_agent.validators import validate_mermaid

# Maximum characters allowed in the context field before truncation.
# Prevents an oversized prior-session summary from crowding out the completion.
_MAX_CONTEXT_CHARS = 4000

# Fallback Mermaid diagram used in beginner mode when both the initial
# generation and the retry produce an invalid diagram.
_BEGINNER_FALLBACK_DIAGRAM = "graph TD\n  A[Concept] --> B[Key Idea] --> C[Result]"


class TeachingAgent:
    """Synchronous Teaching Agent.

    Receives a topic, output mode, and optional context from the Planner Agent,
    generates a structured explanation via a single LLM call, and returns a
    schema-valid TeachingAgentOutput.

    All failure paths return status='error' with content=None.
    No unhandled exceptions propagate to the caller.
    """

    def run(self, raw_input: dict[str, Any]) -> TeachingAgentOutput:
        """Execute the teaching pipeline for a single request."""

        # Step 1: Validate input. On failure, return error before any LLM call.
        try:
            agent_input = TeachingAgentInput(**raw_input)
        except (ValidationError, TypeError):
            topic = raw_input.get("topic", "") if isinstance(raw_input, dict) else ""
            # Use the raw output_mode value to mirror it back in the error response.
            raw_mode = raw_input.get("output_mode", "") if isinstance(raw_input, dict) else ""
            safe_mode = raw_mode if raw_mode in ("beginner", "intermediate", "advanced") else "beginner"
            model = os.getenv("TEACHING_MODEL", "unknown")
            return build_error_output(str(topic), safe_mode, model)

        topic = agent_input.topic
        output_mode = agent_input.output_mode.value
        context = agent_input.context[:_MAX_CONTEXT_CHARS]

        # Step 2: Load LLM config (requires TEACHING_MODEL env var).
        try:
            config = get_llm_config(output_mode)
        except RuntimeError:
            return build_error_output(topic, output_mode, os.getenv("TEACHING_MODEL", "unknown"))

        model = config.model

        # Step 3: Render prompt and build messages.
        prompt = PROMPT_BY_MODE[output_mode].format(topic=topic, context=context)
        messages = build_messages(prompt)

        # Step 4: Call LLM and parse JSON response.
        try:
            raw_response, tokens_used = call_llm(messages, config)
        except RuntimeError:
            return build_error_output(topic, output_mode, model)

        try:
            parsed = parse_llm_response(raw_response)
        except ValueError:
            return build_error_output(topic, output_mode, model)

        # Step 5: Validate the Mermaid diagram and apply mode-specific rules.
        diagram = self._resolve_diagram(parsed.get("diagram"), output_mode, messages, config)

        # Step 6: Assemble and return the successful output.
        try:
            content = TeachingContent(
                explanation=parsed["explanation"],
                diagram=diagram,
                notes=parsed["notes"],
                example=parsed.get("example"),
            )
        except (ValidationError, KeyError):
            return build_error_output(topic, output_mode, model)

        return TeachingAgentOutput(
            status="ok",
            output_mode=OutputMode(output_mode),
            content=content,
            metadata=TeachingMetadata(
                topic=topic,
                tokens_used=tokens_used,
                model=model,
            ),
        )

    def _resolve_diagram(
        self,
        diagram_raw: str | None,
        output_mode: str,
        messages: list[dict[str, Any]],
        config: Any,
    ) -> str | None:
        """Validate the diagram and apply mode-specific fallback rules.

        - intermediate / advanced: invalid or absent → null (non-fatal).
        - beginner: required → retry once on failure → use fallback template.
        """
        if diagram_raw and validate_mermaid(diagram_raw):
            return diagram_raw

        if output_mode != "beginner":
            return None

        # Beginner mode: diagram is required — attempt one retry.
        try:
            raw_retry, _ = call_llm(messages, config)
            parsed_retry = parse_llm_response(raw_retry)
            diagram_retry = parsed_retry.get("diagram")
            if diagram_retry and validate_mermaid(diagram_retry):
                return diagram_retry
        except (RuntimeError, ValueError):
            pass

        return _BEGINNER_FALLBACK_DIAGRAM


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teaching Agent — development CLI runner")
    parser.add_argument("--input", required=True, help="Path to JSON input file")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as fh:
        raw = json.load(fh)

    result = TeachingAgent().run(raw)
    print(result.model_dump_json(indent=2))
