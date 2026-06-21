"""Teaching Agent — linear single-step pipeline."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from project.schemas import (
    OutputMode,
    ReflectionCritique,
    TeachingAgentInput,
    TeachingAgentOutput,
    TeachingContent,
    TeachingMetadata,
)
from teaching_agent.config import (
    get_guardrail_config,
    get_llm_config,
    get_max_reflection_iterations,
    get_reflection_config,
)
from teaching_agent.guardrail import GuardrailClassifier, get_canned_response
from teaching_agent.helpers import (
    build_error_output,
    build_messages,
    parse_llm_response,
    parse_markdown_response,
    sanitize_mermaid_labels,
)
from teaching_agent.llm_client import call_llm, call_llm_stream
from teaching_agent.prompts import (
    PROMPT_BY_MODE,
    REFLECTION_PROMPT_BY_MODE,
    REVISION_PROMPT_BY_MODE,
)
from teaching_agent.stream_parser import StreamingFieldExtractor
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

    def run(
        self, raw_input: dict[str, Any], token_callback: Callable[[str, str], None]
    ) -> tuple[TeachingAgentOutput, str]:
        """Execute the teaching pipeline for a single request.

        Returns (TeachingAgentOutput, raw_markdown). raw_markdown is the complete
        LLM response string; empty string on any error path.
        """
        # Store token_callback for use in _resolve_diagram for diagram retry progress.
        self._token_callback = token_callback

        # Step 1: Validate input. On failure, return error before any LLM call.
        try:
            agent_input = TeachingAgentInput(**raw_input)
        except (ValidationError, TypeError):
            topic = raw_input.get("topic", "") if isinstance(raw_input, dict) else ""
            # Use the raw output_mode value to mirror it back in the error response.
            raw_mode = raw_input.get("output_mode", "") if isinstance(raw_input, dict) else ""
            safe_mode = raw_mode if raw_mode in ("beginner", "intermediate", "advanced") else "beginner"
            model = os.getenv("TEACHING_MODEL", "unknown")
            return build_error_output(str(topic), safe_mode, model), ""

        topic = agent_input.topic
        output_mode = agent_input.output_mode.value
        context = agent_input.context[:_MAX_CONTEXT_CHARS]

        # Step 0: Guardrail classification. Skipped when chat_history is non-empty
        # (follow-up queries always run the full pipeline). If classification fails for
        # any reason, fall through to Step 1 (fail-open).
        if not agent_input.chat_history:
            try:
                guardrail_config = get_guardrail_config()
            except RuntimeError:
                guardrail_config = None

            if guardrail_config is not None:
                try:
                    token_callback("_progress", "Detecting question validity")
                    category = GuardrailClassifier().classify(topic, guardrail_config)
                except Exception:  # noqa: BLE001
                    category = "valid_question"
                canned = get_canned_response(category)
                if canned is not None:
                    token_callback("explanation", canned)
                    return TeachingAgentOutput(
                        status="ok",
                        output_mode=OutputMode(output_mode),
                        content=None,
                        metadata=TeachingMetadata(
                            topic=topic,
                            tokens_used=0,
                            model=guardrail_config.model,
                        ),
                    ), canned

        # Step 2: Load LLM config (requires TEACHING_MODEL env var).
        try:
            config = get_llm_config(output_mode)
        except RuntimeError:
            return build_error_output(topic, output_mode, os.getenv("TEACHING_MODEL", "unknown")), ""

        model = config.model

        # Step 3: Render prompt and build messages. Phase 5: prior conversation
        # turns (if any) are prepended; an empty chat_history reproduces the
        # single-turn message list exactly.
        prompt = PROMPT_BY_MODE[output_mode].format(topic=topic, context=context)
        messages = build_messages(prompt, agent_input.chat_history)

        # Step 4: Stream LLM response through field extractor.
        extractor = StreamingFieldExtractor(token_callback)
        try:
            tokens_used = 0
            for delta, chunk_tokens in call_llm_stream(messages, config):
                extractor.feed(delta)
                if chunk_tokens:
                    tokens_used = chunk_tokens
        except RuntimeError:
            return build_error_output(topic, output_mode, model), ""

        raw_markdown, diagram_raw = extractor.finalize()

        try:
            parsed = parse_markdown_response(raw_markdown)
        except ValueError:
            return build_error_output(topic, output_mode, model), ""

        # Step 5: Validate the Mermaid diagram and apply mode-specific rules.
        # Diagram is validated (and retried if needed) before being sent to the frontend.
        diagram = self._resolve_diagram(diagram_raw, output_mode, messages, config)
        if diagram:
            token_callback("diagram", diagram)

        # Step 6: Assemble the initial (pre-reflection) content.
        try:
            content = TeachingContent(
                explanation=parsed["explanation"],
                diagram=diagram,
                notes=parsed["notes"],
                example=parsed.get("example"),
            )
        except (ValidationError, KeyError):
            return build_error_output(topic, output_mode, model), ""

        # Step 7: Reflection loop (Phase 3). Runs after the initial content is
        # assembled, before the final response. N=0 (or any critique/revision
        # failure) leaves the initial content unchanged. tokens_used accrues over
        # every LLM call that returns; reflection_iterations counts only fully
        # completed (critique + revision) cycles.
        tokens_accumulator = [tokens_used]
        current_content = content
        completed_iterations = 0

        try:
            max_iterations = get_max_reflection_iterations(output_mode)
        except ValueError:
            max_iterations = 0  # misconfigured env var -> reflection disabled (no crash)

        if max_iterations > 0:
            try:
                reflection_config = get_reflection_config(output_mode)
            except RuntimeError:
                reflection_config = None

            if reflection_config is not None:
                for _ in range(max_iterations):
                    critique = self._reflect(
                        current_content, topic, output_mode,
                        reflection_config, tokens_accumulator,
                    )
                    if critique is None:
                        break
                    revised = self._revise(
                        current_content, critique, topic, output_mode,
                        context, config, tokens_accumulator,
                    )
                    if revised is None:
                        break
                    current_content = revised
                    completed_iterations += 1

        # Step 8: Assemble and return the final output.
        return TeachingAgentOutput(
            status="ok",
            output_mode=OutputMode(output_mode),
            content=current_content,
            metadata=TeachingMetadata(
                topic=topic,
                tokens_used=sum(tokens_accumulator),
                model=model,
                reflection_iterations=completed_iterations,
            ),
        ), raw_markdown

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
        if not isinstance(diagram_raw, str):
            diagram_raw = None
        if diagram_raw:
            diagram_raw = sanitize_mermaid_labels(diagram_raw)
            if validate_mermaid(diagram_raw):
                return diagram_raw

        if output_mode != "beginner":
            return None

        # Beginner mode: diagram is required — attempt one retry.
        self._token_callback("_progress", "Retrying Mermaid diagram generation.")
        try:
            raw_retry, _ = call_llm(messages, config)
            parsed_retry = parse_markdown_response(raw_retry)
            diagram_retry = parsed_retry.get("diagram")
            if diagram_retry:
                diagram_retry = sanitize_mermaid_labels(diagram_retry)
                if validate_mermaid(diagram_retry):
                    return diagram_retry
        except (RuntimeError, ValueError):
            pass

        return _BEGINNER_FALLBACK_DIAGRAM

    def _reflect(
        self,
        current_content: TeachingContent,
        topic: str,
        output_mode: str,
        config: Any,
        tokens_accumulator: list[int],
    ) -> ReflectionCritique | None:
        """Critique the current content (Phase 3); None on any failure.

        Any LLM call that returns is counted in tokens_accumulator (SC-013 counts
        all calls in the lifecycle), even if the response later fails to parse.
        """
        prompt = REFLECTION_PROMPT_BY_MODE[output_mode].format(
            topic=topic,
            output_mode=output_mode,
            current_output=current_content.model_dump_json(),
        )
        messages = build_messages(prompt)
        try:
            raw_response, tokens_used = call_llm(messages, config)
        except RuntimeError:
            return None
        tokens_accumulator.append(tokens_used)
        try:
            parsed = parse_llm_response(raw_response, required_fields=())
        except ValueError:
            return None
        try:
            return ReflectionCritique(**parsed)
        except ValidationError:
            return None

    def _revise(
        self,
        current_content: TeachingContent,
        critique: ReflectionCritique,
        topic: str,
        output_mode: str,
        context: str,
        config: Any,
        tokens_accumulator: list[int],
    ) -> TeachingContent | None:
        """Produce a revised TeachingContent from the critique (Phase 3).

        Uses the generation config (same model + ceiling). Applies the same
        diagram rules as initial generation. Returns None on any failure.
        """
        prompt = REVISION_PROMPT_BY_MODE[output_mode].format(
            topic=topic,
            output_mode=output_mode,
            context=context,
            current_output=current_content.model_dump_json(),
            revision_instructions=critique.revision_instructions,
        )
        messages = build_messages(prompt)
        try:
            raw_response, tokens_used = call_llm(messages, config)
        except RuntimeError:
            return None
        tokens_accumulator.append(tokens_used)
        try:
            parsed = parse_llm_response(raw_response)
        except ValueError:
            return None
        diagram = self._resolve_diagram(parsed.get("diagram"), output_mode, messages, config)
        try:
            return TeachingContent(
                explanation=parsed["explanation"],
                diagram=diagram,
                notes=parsed["notes"],
                example=parsed.get("example"),
            )
        except (ValidationError, KeyError):
            return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teaching Agent — development CLI runner")
    parser.add_argument("--input", required=True, help="Path to JSON input file")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as fh:
        raw = json.load(fh)

    result, _ = TeachingAgent().run(raw, lambda f, t: None)
    print(result.model_dump_json(indent=2))
