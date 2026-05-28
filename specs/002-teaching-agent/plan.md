# Implementation Plan: Teaching Agent

**Branch**: `002-build-teaching-agent` | **Date**: 2026-05-28 | **Spec**: `/specs/002-teaching-agent/spec.md`
**Input**: Feature specification from `/specs/002-teaching-agent/spec.md`

## Summary

Implement a synchronous Teaching Agent that receives a topic, output mode, and optional
session context from the Planner Agent, calls an LLM to generate a mode-specific
structured explanation (beginner / intermediate / advanced), validates the Mermaid diagram
if one is generated, and returns a schema-safe JSON response containing explanation, diagram,
notes, example, and audit metadata.

The agent uses LiteLLM as the LLM interface through its own `teaching_agent/llm_client.py`
module (not shared with the RAG agent). Configuration is loaded from environment variables.
No graph orchestration runtime (LangGraph) is used — the pipeline is a linear single-step
sequence that does not require stateful loop orchestration.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: pydantic v2, litellm>=1.40.0, pytest>=8.0.0 (no new packages beyond existing requirements.txt)
**Storage**: N/A (pure in-memory; no file I/O beyond CLI input for development)
**Testing**: pytest
**Target Platform**: Linux runtime (local dev and container-ready execution)
**Project Type**: Agent module/library within a multi-agent backend
**Performance Goals**: Beginner mode ≤ 5s wall-clock; intermediate ≤ 10s; advanced ≤ 20s on developer hardware under a fast-endpoint model
**Constraints**: Synchronous execution only; per-mode token ceilings enforced at LiteLLM call level (512 / 1024 / 2048); Mermaid validation required before returning diagram; JSON output only; no LangGraph
**Scale/Scope**: One synchronous request per invocation; invoked once per user query by the Planner Agent

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Gate Review (Pre-Research)

- Code Quality Gate: PASS. Responsibility boundaries are explicit by module:
  `project/schemas.py`, `teaching_agent/agent.py`, `teaching_agent/llm_client.py`,
  `teaching_agent/prompts.py`, `teaching_agent/validators.py`, `teaching_agent/helpers.py`,
  `teaching_agent/config.py`. No cross-agent module imports.
- Testing Gate: PASS. Planned tests cover: schema validation per mode, cross-mode
  differentiation (same topic at all three modes), diagram presence/absence rules, Mermaid
  validity enforcement, error response structure on LLM failure and invalid input, and
  token ceiling compliance.
- UX Consistency Gate: PASS. Output format (JSON structure) is stable across all modes
  and requests. Explanation structure per mode is defined and enforced by prompt templates.
  Diagram validation prevents broken Mermaid from reaching the Streamlit renderer.
- Performance Gate: PASS. Token ceilings define measurable per-mode budgets enforced at the
  LiteLLM call boundary. Per-mode wall-clock targets are stated and verifiable.
- Maintainability Gate: PASS. Config and prompt templates are centralized in dedicated
  modules. Mermaid validation is isolated in `validators.py`. All non-obvious design
  decisions are documented in `research.md`.

### Post-Design Gate Review (After Phase 1 Artifacts)

- Code Quality Gate: PASS. Data model and contracts are defined; no cross-module ambiguity.
  Module boundary for schemas follows the established `project/schemas.py` pattern.
- Testing Gate: PASS. `quickstart.md` includes both full-run and targeted test instructions.
  Test mocking pattern mirrors the RAG agent suite (monkeypatching `call_llm`).
- UX Consistency Gate: PASS. Contract defines stable field structure; diagram null-fallback
  behavior is documented so the UI can handle both cases.
- Performance Gate: PASS. Token ceiling enforcement is at the LiteLLM call level with
  actual consumption reported in metadata. Wall-clock targets are stated.
- Maintainability Gate: PASS. Environment-variable-driven configuration eliminates
  hard-coded provider coupling. Separate prompt templates per mode are independently
  auditable.

## Project Structure

### Documentation (this feature)

```text
specs/002-teaching-agent/
├── plan.md                          # This file
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/
│   └── teaching-agent-contract.md   # Phase 1 output
├── checklists/
│   └── requirements.md
└── tasks.md                         # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
project/
└── schemas.py           # Add: OutputMode, TeachingAgentInput, TeachingContent,
                         #      TeachingMetadata, TeachingAgentOutput

teaching_agent/
├── __init__.py
├── agent.py             # TeachingAgent class: run(), input validation, prompt dispatch,
                         #                      response assembly
├── config.py            # LLMConfig dataclass, get_llm_config(), per-mode max_tokens map
├── llm_client.py        # call_llm(messages, config) → str; guards unconfigured calls
├── prompts.py           # BEGINNER_PROMPT, INTERMEDIATE_PROMPT, ADVANCED_PROMPT constants
├── validators.py        # validate_mermaid(diagram: str) → bool; regex-based structural check
├── helpers.py           # parse_llm_response(raw: str) → dict; build_error_output()
└── tests/
    ├── __init__.py
    ├── test_teaching_agent.py
    └── inputs/
        └── sample_input.json
```

**Structure Decision**: Single Python agent module following the `rag_agent/` layout.
Schemas in `project/schemas.py` (shared contract location). No new top-level directories.
No LangGraph — the linear pipeline requires only a plain class.

## Complexity Tracking

No constitution violations identified. Complexity is justified by the per-mode prompt
differentiation requirement (three separate prompt templates) and Mermaid validation,
both of which are direct spec requirements rather than architectural overhead.
