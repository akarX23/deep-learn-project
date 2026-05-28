# Research: Teaching Agent

## Decision 1: LLM Invocation Layer

- Decision: Use LiteLLM via a dedicated `teaching_agent/llm_client.py` module containing its own `call_llm(messages, config)` function.
- Rationale: LiteLLM provides provider-neutral routing (any OpenAI-compatible endpoint, Anthropic, local vLLM) without vendor lock-in. The teaching agent owns its own client module following the same isolation pattern as `rag_agent/llm_client.py`, consistent with the project's per-agent client decision.
- Alternatives considered: Anthropic SDK directly (provider lock-in, breaks offline/local model support); sharing `rag_agent/llm_client.py` (rejected — cross-agent imports create coupling and the project decision is per-agent clients).

## Decision 2: Orchestration Runtime

- Decision: No LangGraph. Implement the teaching pipeline as a plain Python class (`TeachingAgent`) with a `run()` method that executes a linear single-step flow: validate input → build prompt → call LLM → parse response → validate diagram → return output.
- Rationale: The teaching agent has no iterative loop or conditional branching between pages. A state graph adds overhead without benefit for a single-request linear pipeline. LangGraph is appropriate for the RAG agent's page-iteration loop but not here.
- Alternatives considered: LangGraph (overkill for a linear single-step pipeline); asyncio pipeline (synchronous execution is a hard constraint per spec).

## Decision 3: Runtime Configuration Source

- Decision: Load model configuration from environment variables with centralized defaults in `teaching_agent/config.py`. Use prefix `TEACHING_` to isolate from `RAG_` variables.
- Rationale: Mirrors the `rag_agent/config.py` pattern — deployment-friendly, no secrets in code, supports local vLLM and hosted APIs via the same code path.
- Alternatives considered: Shared config module across agents (breaks per-agent isolation decision); static config file (less portable for different deployment environments).

## Decision 4: LLM Output Format and Parsing

- Decision: Prompt the LLM to return a JSON object containing `explanation`, `diagram`, `notes`, and `example` fields. Parse with `json.loads()`. On parse failure or missing required fields, return `status: "error"` with a descriptive message.
- Rationale: A single LLM call returns all content fields in one structured response, avoiding multiple round trips. JSON-in-prompt is compatible with all LiteLLM-supported providers without requiring tool use or structured output API features.
- Alternatives considered: Tool use / function calling (not universally supported across all LiteLLM providers; complicates offline/local model usage); two-pass extraction (explanation first, then diagram/notes — doubles LLM call count per request).

## Decision 5: Token Ceiling Enforcement

- Decision: Enforce per-mode token ceilings (512 beginner / 1024 intermediate / 2048 advanced) via the `max_tokens` parameter in the LiteLLM call. Report actual consumption from `response.usage.total_tokens` in `metadata.tokens_used`.
- Rationale: Setting `max_tokens` at the model call level is the only reliable way to enforce hard ceilings. Response usage reporting requires no additional counting logic.
- Alternatives considered: Post-hoc token counting and truncation (unreliable — LLM output may be incomplete mid-sentence); tiktoken counting before the call (adds dependency and is estimator-only, not a hard enforcer).

## Decision 6: Mermaid Diagram Validation

- Decision: Implement lightweight regex-based structural validation in `teaching_agent/validators.py`. Validation checks: (1) first non-empty line matches a recognized Mermaid diagram type keyword (`graph`, `flowchart`, `sequenceDiagram`, `classDiagram`, `stateDiagram`, `erDiagram`, `pie`, `mindmap`, `timeline`); (2) at least one additional non-empty line follows the type declaration (diagram has content). On validation failure, set `diagram` to `null` rather than returning invalid syntax.
- Rationale: No full Mermaid renderer is available in a pure Python environment. A structural check catches the two most common failure modes (wrong opening, empty body) without requiring a browser or Node.js process. Setting diagram to null on failure is safer than propagating invalid syntax to the UI.
- Alternatives considered: `mermaid-py` library (requires Node.js subprocess, not acceptable for a pure Python agent); no validation (invalid diagrams break the Streamlit Mermaid renderer and violate FR-007); full AST parsing (disproportionate complexity for the required safety guarantee).

## Decision 7: Per-Mode Prompt Templates

- Decision: Define three separate prompt constants in `teaching_agent/prompts.py` — `BEGINNER_PROMPT`, `INTERMEDIATE_PROMPT`, `ADVANCED_PROMPT` — each with explicit structural instructions, vocabulary register guidance, diagram requirements, and JSON output format specification embedded.
- Rationale: Separate templates make mode-specific requirements reviewable and testable in isolation. A single parameterized template with conditional blocks would be harder to audit for per-mode compliance.
- Alternatives considered: Single template with mode injections (harder to guarantee per-mode structural compliance); runtime template construction (increases prompt engineering complexity without benefit).

## Decision 8: New Dependencies

- Decision: No new dependencies are required. `pydantic>=2.0` and `litellm>=1.40.0` already in `requirements.txt` are sufficient.
- Rationale: The teaching agent's pipeline (LLM call → JSON parse → Pydantic validation → Mermaid regex check) requires only what the project already declares.
- Alternatives considered: Adding `mermaid-py` for diagram validation (rejected — see Decision 6); adding `tiktoken` for token counting (rejected — use LiteLLM usage reporting instead).

## Decision 9: Schema Placement

- Decision: Add `TeachingAgentInput`, `TeachingAgentOutput`, `TeachingContent`, `TeachingMetadata`, and `OutputMode` to `project/schemas.py` alongside existing RAG agent schemas.
- Rationale: `project/schemas.py` is the established shared contract file for inter-agent communication. Downstream agents (Planner, Quiz, Evaluation) import from one location.
- Alternatives considered: Separate `teaching_agent/schemas.py` (breaks the shared contract pattern; downstream agents would need to import from two locations).
