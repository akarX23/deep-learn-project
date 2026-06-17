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

- Decision: (Phase 1–2) Prompt the LLM to return a JSON object containing `explanation`, `diagram`, `notes`, and `example` fields. Parse with `json.loads()`. On parse failure or missing required fields, return `status: "error"` with a descriptive message. (Phase 4 update — see Decision 14) Replaced by markdown bold-header format to enable real-time token streaming without a complex JSON stream parser.
- Rationale: A single LLM call returns all content fields in one structured response, avoiding multiple round trips. JSON-in-prompt is compatible with all LiteLLM-supported providers without requiring tool use or structured output API features.
- Alternatives considered: Tool use / function calling (not universally supported across all LiteLLM providers; complicates offline/local model usage); two-pass extraction (explanation first, then diagram/notes — doubles LLM call count per request).

## Decision 5: Token Ceiling Enforcement

- Decision: Enforce per-mode token ceilings via `TEACHING_{MODE}_MAX_TOKENS` env vars (default 4096 each) passed as `max_tokens` to the LiteLLM call. No ceiling is hardcoded in Python — all values come exclusively from environment/configuration files. Report actual consumption from `response.usage.completion_tokens` in `metadata.tokens_used`.
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

## Decision 10: Kafka Integration Architecture (Phase 2)

- Decision: Implement the Kafka layer as three separate files — `teaching_agent/kafka.py` (I/O primitives and Protocol types), `teaching_agent/handlers.py` (business logic, zero Kafka I/O), `teaching_agent/worker.py` (lifecycle and poll loop) — following the identical structure used by `rag_agent/kafka.py`, `rag_agent/handlers.py`, and `rag_agent/worker.py`.
- Rationale: Consistency across agents reduces the cognitive overhead for any developer moving between agent codebases. The three-file separation makes each layer independently unit-testable: `handlers.py` can be tested with a fake agent and a fake publisher; `worker.py` can be tested with fake consumer/producer factories. Protocol types in `kafka.py` enable simple dict-based fakes without any mocking framework.
- Alternatives considered: Single `kafka_worker.py` combining all three layers (harder to test business logic in isolation; tight coupling between I/O and domain logic); embedding Kafka logic in `agent.py` (violates single-responsibility; makes the core pipeline harder to test and reuse).

## Decision 11: Always-Publish Completion Event

- Decision: `TeachingRequestEventHandler.process_request()` always publishes a `TeachingCompletionEvent` to `"teaching-complete"` regardless of whether the core pipeline returns `status: "ok"` or `status: "error"`. A failed completion event carries `content: ""` (empty string). The new `TeachingCompletionEvent` schema no longer carries `status`, `tokens_used`, `model`, or `errors` — the Planner infers failure from an empty `content` field.
- Rationale: The Planner Agent must always receive a response to avoid hanging indefinitely. A schema-valid error completion event is more operationally useful than silence — the Planner can log it, retry, or surface it to the user. This mirrors the RAG agent pattern (`publish_rag_complete` is called in both success and failure branches of `RAGRequestEventHandler.process_request()`).
- Alternatives considered: Publish only on success, log on failure (leaves Planner waiting on failures); publish to a dead-letter topic on failure (adds infrastructure complexity without benefit at this stage; deferred to future iteration).

## Decision 12: Per-Mode LLM Configuration via Environment Variables

- Decision: Support per-mode model, API key, max tokens, temperature, and effort via `TEACHING_{MODE}_MODEL`, `TEACHING_{MODE}_API_KEY`, `TEACHING_{MODE}_MAX_TOKENS`, `TEACHING_{MODE}_TEMPERATURE`, and `TEACHING_{MODE}_EFFORT` env vars (where `{MODE}` is `BEGINNER`, `INTERMEDIATE`, or `ADVANCED`). Model, API key, max tokens, and temperature each fall back to the shared `TEACHING_MODEL` / `TEACHING_API_KEY` / default 4096 / `TEACHING_TEMPERATURE` (default 0.7) when unset. Effort is optional with no shared fallback — when unset, no effort parameter is passed to the LLM call. No values are hardcoded in `config.py` — the Python file only contains the resolution logic.
- Rationale: Different learner levels benefit from different model tiers (e.g. a fast, cheap model for beginner explanations vs. a more capable model for advanced content) and different temperature settings (e.g. lower temperature for more deterministic beginner explanations, higher for richer advanced content). The effort parameter controls Claude 4.6's compute budget at the output level via `output_config={"effort": value}`, applied conditionally in `llm_client.py` only when the model is a Claude 4.6 variant (Sonnet 4.6, Opus 4.6); silently skipped for all other models (Haiku, Groq/Llama, etc. do not support `output_config`). Effort does NOT enable extended thinking or reasoning tokens — it purely governs output compute intensity. Keeping all values in the environment/configuration file means provider, quota, or tuning changes require only a `.env.local` edit, not a code change or redeploy. The fallback-to-shared pattern keeps configuration minimal for the common case (same model for all modes) while enabling full per-mode control when needed. `TEACHING_API_BASE` is intentionally not replicated per-mode: LiteLLM resolves the API endpoint automatically from the model string prefix for all standard cloud providers; a custom base URL is only needed for self-hosted deployments and is unlikely to differ per learner level.
- Alternatives considered: Hardcoded per-mode defaults in `config.py` (requires a Python file edit to change provider; breaks the "config file only" goal); separate config classes per mode (over-engineering — the fallback pattern covers all cases with a single `get_llm_config(output_mode)` call); using LiteLLM's `reasoning_effort` parameter for effort (rejected — it always enables extended thinking/budget tokens as a side effect, increasing latency and token cost; direct `output_config` passthrough achieves the same compute-level control without thinking overhead).

## Decision 14: Markdown Format over JSON for Token Streaming (Phase 4)

- Decision: Replace `response_format={"type": "json_object"}` and JSON prompts with a markdown prompt that uses bold section headers (`**Explanation**`, `**Diagram**`, `**Notes**`, `**Example**`) as field delimiters. `parse_llm_response()` (JSON parser) is replaced by `parse_markdown_response()` (markdown section splitter).
- Rationale: Streaming requires real-time field identification. With JSON mode, field boundaries are embedded in JSON string syntax — detecting the end of the `explanation` string value requires a character-level escape-aware parser that handles `\"`, `\\`, and Unicode escapes. This is fragile, especially when `example` fields contain Python code with quoted strings. Markdown bold headers (`**SectionName**`) are unambiguous delimiters with no escape handling needed. A state machine watching for `**Header**` on a line is trivially simple and handles all edge cases cleanly. A single LLM call still returns all four fields in one response — no extra round trips.
- Alternatives considered: JSON mode with streaming JSON parser (rejected — fragile on code examples containing `\"`; requires reimplementing a JSON string parser for the streaming path); two LLM calls — one for plain-text explanation, one for structured JSON (rejected — doubles cost and latency); streaming raw JSON tokens without field extraction (rejected — frontend receives JSON syntax noise and cannot distinguish which field is being streamed).

## Decision 15: `StreamingFieldExtractor` Design (Phase 4)

- Decision: Implement `StreamingFieldExtractor` as a stateful class in `teaching_agent/stream_parser.py`. It processes raw delta chunks from `call_llm_stream()` one chunk at a time. State machine tracks: `SEEKING_FIELD`, `IN_EXPLANATION`, `IN_DIAGRAM`, `IN_NOTES`, `IN_EXAMPLE`. On `**SectionName**` detection, the extractor transitions state. For `explanation`, `notes`, `example`: each chunk is forwarded immediately via `token_callback(field, chunk)`. For `diagram`: chunks are buffered; the complete diagram string is forwarded once via `token_callback("diagram", buffer)` when the next section header is detected or the stream ends.
- Rationale: Diagram must be buffered because partial Mermaid syntax is not renderable and would confuse the frontend renderer. Explanation, notes, and example are prose or code — partial chunks are meaningful and can be progressively rendered. The state machine approach keeps the extractor stateless between calls to `feed(chunk)` except for its own internal state variables — easy to test with arbitrary chunk sizes.
- Alternatives considered: Regex-based section splitting on the complete response (rejected — requires buffering the entire response before emitting any tokens; defeats streaming purpose); event-driven streaming JSON parser library like `ijson` (rejected — designed for byte streams, not LiteLLM delta strings; adds a dependency for a problem that markdown headers solve more simply).

## Decision 16: Stream-Complete Sentinel Design (Phase 4)

- Decision: After all field tokens are published to `"stream-tokens"`, publish one final `StreamTokensEventBody` with `data = {"done": true, "tokens_used": N}`. This is the frontend's unambiguous signal that the stream for this `sid`/`request_id` has ended. The sentinel is published on both success and error paths.
- Rationale: Per-field `is_final` flags are insufficient — the frontend cannot know from a single field's end signal whether more fields will follow (e.g. `diagram` may be null in intermediate/advanced mode, so the field order varies). A single top-level sentinel eliminates this ambiguity without the frontend needing to know which fields are expected for a given `user_level`. Using the existing `StreamTokensEventBody.data` dict (which is `dict[str, Any]`) avoids any schema change.
- Alternatives considered: `is_final` flag on each field's last token (rejected — frontend must know which field is last, which varies by mode and whether diagram is null); separate `"stream-complete"` Kafka topic (rejected — adds a topic for a use case already handled by the generic `"stream-tokens"` topic); relying on `TeachingCompletionEvent` as the "done" signal (rejected — that topic is consumed by the Planner, not the backend's Socket.IO forwarder).

## Decision 17: Raw Markdown in `TeachingCompletionEvent.content` (Phase 4)

- Decision: `TeachingCompletionEvent.content` carries the complete raw markdown string produced by the LLM (all four sections concatenated) when the pipeline succeeds; empty string `""` on failure. This replaces the previous JSON-serialized `TeachingContent` (`model_dump_json()`).
- Rationale: With markdown output, the raw LLM response is already the canonical human-readable form. Parsing it into `TeachingContent` and re-serializing to JSON adds a transformation step with no downstream benefit — the Planner and Quiz Agent can consume markdown directly. The `TeachingContent` structure is still assembled internally in `agent.py` for Mermaid validation and `TeachingAgentOutput` status tracking, but it is not serialized for the Kafka event. This simplifies `handlers.py` (no `model_dump_json()` call) and makes the `TeachingCompletionEvent` content directly renderable.
- Alternatives considered: Keep JSON-serialized `TeachingContent` in the completion event (rejected — requires `parse_markdown_response()` output to be serialized back to JSON, adding complexity and a round-trip; downstream agents would need to be updated to parse a new JSON structure anyway since `TeachingContent` fields now contain markdown prose rather than escaped JSON strings); send both raw markdown and structured JSON (rejected — over-engineering; two representations of the same content with no clear consumer of both).

## Decision 13: Kafka Event Schema Placement

- Decision: `TeachingRequestEvent` and `TeachingCompletionEvent` go in `project/schemas.py` in the Teaching Agent section. `"teaching"` is added to the existing `PlannerTopics` enum (consistent with `PlannerTopics.RAG`); a new `TeachingTopics` enum with only `TEACHING_COMPLETE = "teaching-complete"` goes in `project/topics.py`. Both are included in `get_all_topic_names()`. `sid` (Socket.IO session ID string) replaces `session_ctx` (free-form dict) as the routing identifier threaded through `TeachingRequestEvent` and echoed in `TeachingCompletionEvent` — this reflects the Planner Agent's updated schema contract post-master-merge.
- Rationale: Mirrors the RAG agent pattern exactly — `RAGRequestEvent` and `RAGCompletionEvent` live in `project/schemas.py`; `PlannerTopics` and `RAGTopics` live in `project/topics.py`. The backend service calls `get_all_topic_names()` at startup to bootstrap all topics; adding `TeachingTopics` there ensures the `"teaching"` and `"teaching-complete"` topics are created automatically without any backend service changes. Using `sid` instead of `session_ctx` aligns with the frontend WebSocket routing model — the backend needs a Socket.IO session ID, not a generic context dict, to emit events to the right client.
- Alternatives considered: Event schemas inside `teaching_agent/` (breaks the shared contract pattern; forces the Planner and Quiz Agent to import from a peer agent module, creating cross-agent coupling).
