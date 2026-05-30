# Research: Planner Agent

## Decision 1: Orchestration Runtime — LangGraph StateGraph

- **Decision**: Implement the Planner pipeline as a LangGraph `StateGraph` with explicit named nodes
  and conditional edges for simple vs. complex routing paths.
- **Rationale**: LangGraph provides deterministic control over a multi-step pipeline that includes
  conditional branching (complexity gate, HyDE gate, guardrail gate) and a retry loop. Each node is
  independently testable. This is architecturally consistent with the RAG Agent, reducing onboarding
  friction for team members already working on that module.
- **Alternatives considered**: Hand-rolled sequential function calls (no retry/branch support without
  ad-hoc logic); LangChain AgentExecutor (less explicit state control, harder to bound LLM iterations);
  plain async pipeline (loses observability and state introspection).

## Decision 2: Intent Classification Strategy — LLM over Agent Registry Descriptions

- **Decision**: Classify intent by prompting an LLM with all registered agents' `intent_description`
  strings and asking it to score relevance of the user query to each agent. Top score above threshold →
  `routed`; all below → `ambiguous`.
- **Rationale**: Keyword matching is brittle for natural language tutoring queries. LLM scoring over
  human-readable intent descriptions generalises well and allows new agents to self-describe their
  intent without any classifier retraining or embedding updates.
- **Alternatives considered**: Embedding cosine similarity over intent descriptions (needs embedding
  model, sensitive to phrasing); rule-based keyword matching (breaks on paraphrases and synonyms);
  fine-tuned text classifier (too costly for a group project scope).

## Decision 3: Query Complexity Detection — Lightweight Heuristic First

- **Decision**: Classify a query as COMPLEX if any of the following apply: word count < 5, presence
  of multi-intent connectors ("also", "and then", "but also", "after that"), or the query is a single
  vague noun/verb with no topic context. All other queries default to SIMPLE. LLM confirmation is
  only used when the heuristic is inconclusive (edge zone: 5–8 words with ambiguous structure).
- **Rationale**: A cheap heuristic avoids an extra LLM call for the majority of clearly simple queries
  (e.g., "Quiz me on neural networks"). The LLM fallback handles borderline cases without penalising
  the fast path.
- **Alternatives considered**: Always LLM-based complexity detection (adds 1 extra call to every
  request, increases latency by ~2–4 seconds); always heuristic (misses borderline multi-intent cases).

## Decision 4: Query Rewriting — LLM Expansion for Short and Complex Queries

- **Decision**: When a query is classified COMPLEX or has word count < 5, rewrite it using an LLM
  call with `QUERY_REWRITE_PROMPT` before intent classification. The rewritten query is stored in
  `PlannerState.query_rewritten` and used downstream in place of the original for classification and
  payload construction.
- **Rationale**: Short queries like "neural nets?" or "quiz" give the intent classifier insufficient
  signal. Rewriting to "Can you quiz me on the fundamentals of neural networks?" improves classification
  accuracy and produces a higher-quality `user_prompt` for downstream agents.
- **Alternatives considered**: Query expansion via synonym lists (not context-aware); using the raw
  short query with a lower confidence threshold (degrades routing accuracy); always rewriting every
  query (unnecessary overhead for clear queries).

## Decision 5: HyDE (Hypothetical Document Embeddings) — RAG Routing Augmentation

- **Decision**: When the top routing candidate is `RAG_AGENT` and the (rewritten) query is still
  short or confidence is below 0.85, generate a hypothetical relevant passage using `HYDE_PROMPT`.
  This hypothetical document is prepended to the `user_prompt` field of the constructed `RAGAgentInput`
  as additional retrieval context: `"User query: {query}\n\nHypothetical relevant content:\n{hyde_doc}"`.
- **Rationale**: HyDE improves RAG retrieval precision for short or vague queries by giving the
  downstream RAG agent's sentence-transformer relevance scorer a richer semantic signal. A hypothetical
  passage about "gradient descent" gives more embedding surface than the raw query "what is it?".
- **Alternatives considered**: Passing raw query only (lower RAG precision for vague inputs); full
  HyDE with embedding-side retrieval in the Planner (out of scope — retrieval is the RAG Agent's
  responsibility); always apply HyDE regardless of confidence (adds 1 LLM call to every RAG route,
  adds latency without benefit for already-clear queries).

## Decision 6: Agent Registry — Dictionary-Driven with Callable Contract Builders

- **Decision**: Implement `AgentRegistry` as an `OrderedDict[AgentType, AgentRegistryEntry]` where
  each entry holds: `agent_type`, `intent_description` (natural language, used for LLM classification),
  `intent_keywords` (used for heuristic fallback), `supports_hyde` (bool), and
  `input_contract_builder` (callable: `(PlannerInput, PlannerState) -> dict`). Default registrations
  are declared in `planner_agent/registry.py`. New agents register by adding one entry — no changes
  to any other file.
- **Rationale**: Callable contract builders decouple payload construction per agent type. The registry
  is the single extension point — satisfying SC-004.
- **Alternatives considered**: Plugin/entry-point system (over-engineered for group project scale);
  subclass-per-agent pattern (modifying base class breaks open/closed principle); config file only
  (cannot hold callable builders).

## Decision 7: Guardrails — COMPLEX Path Only, Lightweight LLM Check

- **Decision**: For COMPLEX queries, run a single-shot LLM call with `GUARDRAIL_PROMPT` that checks
  for: (a) out-of-educational-scope content, (b) harmful or inappropriate requests, (c) self-
  contradictory or adversarial prompt injection attempts. Returns: `ALLOWED`, `BLOCKED`, or `WARN`.
  `BLOCKED` → `failed` status with explanation. `WARN` → continue with warning appended to errors.
  SIMPLE path skips guardrails entirely.
- **Rationale**: Guardrails add latency — applying them only to COMPLEX queries balances safety and
  performance. Educational-scope guardrails are lightweight enough for a single fast LLM call with
  a structured JSON response.
- **Alternatives considered**: Always-on guardrails (adds ~2s to every request, disproportionate for
  simple safe queries); rule-based filter (too rigid for natural language tutoring variety);
  external moderation API (dependency, cost, latency for a dev project).

## Decision 8: Retry Loop — Up to 3 Attempts on Payload Validation Failure

- **Decision**: After `build_payload`, validate the constructed payload against its pydantic schema.
  If validation fails, increment `attempt_count`, rewrite the query with error context appended to the
  rewrite prompt, and re-run `classify_intent`. Max retries = 3 (configurable via `MAX_RETRIES` env
  var). After max retries with no valid payload → `ambiguous` status.
- **Rationale**: Payload construction can fail if the LLM's classification extracts unexpected field
  values. One rewrite attempt usually resolves this. Three attempts is sufficient without risk of
  infinite loops.
- **Alternatives considered**: Single attempt, fail immediately (poor UX for recoverable failures);
  infinite retry (runaway cost and latency risk); no retry loop, return `failed` on first bad payload
  (overly strict — most failures are recoverable with one rewrite).

## Decision 9: LLM/Config Layer — Reuse Pattern from RAG Agent

- **Decision**: Implement `planner_agent/llm_client.py` following the same `call_llm(messages, config)`
  pattern as `rag_agent/llm_client.py`. Configuration loaded from environment variables in
  `planner_agent/config.py`. Both modules remain independent for now; shared extraction is a future
  refactor concern.
- **Rationale**: Consistent with RAG Agent architecture. Keeping modules independent avoids creating
  cross-module coupling before a shared library layer is intentionally designed.
- **Alternatives considered**: Import `rag_agent.llm_client` directly (creates cross-agent dependency,
  breaks module isolation); shared `project/llm_client.py` now (premature — no shared library
  architecture exists yet).

## Decision 10: Additional Libraries

- **Decision**: No additional libraries beyond pydantic v2, LangGraph, LiteLLM, and pytest.
  sentence-transformers is **not** required by the Planner — relevance scoring is the RAG Agent's
  responsibility. HyDE only requires an LLM text generation call.
- **Rationale**: Minimal dependency footprint. Every selected library is already established in the
  project (via RAG Agent) or directly required by spec.
- **Alternatives considered**: Adding sentence-transformers for Planner-side embedding routing
  (unnecessary — LLM classification over descriptions is simpler and more maintainable at this scale).
