# Research: RAG Retrieval Agent

## Decision 1: PDF Extraction Library
- Decision: Use PyMuPDF (`fitz`) for page count, text extraction, table extraction, and image extraction.
- Rationale: One dependency covers all required per-page operations with good performance and direct page access.
- Alternatives considered: `pdfplumber` (good tables but weaker image flow integration), `pypdf` (lighter but insufficient extraction coverage).

## Decision 2: Orchestration Runtime
- Decision: Use LangGraph for deterministic page-processing flow with explicit state transitions.
- Rationale: StateGraph provides clear control over page iteration, conditional continuation, and final compilation.
- Alternatives considered: Hand-rolled loops (less structured), generic agent executors (less explicit state control).

## Decision 3: LLM Invocation Layer
- Decision: Route text, VLM, and embedding calls through a unified LiteLLM client abstraction.
- Rationale: Keeps provider integration consistent and reduces SDK-specific branching.
- Alternatives considered: Provider-specific SDKs (more lock-in, duplicated code paths).

## Decision 4: Embedding Source
- Decision: Use remote LiteLLM-backed embedding API as the primary relevance scoring source.
- Rationale: Aligns embedding configuration and operational model with text/VLM flows and avoids local model distribution overhead.
- Alternatives considered: Local sentence-transformers as primary path (extra model management), hybrid dual-path fallback (higher complexity).

## Decision 5: Provider Key Strategy
- Decision: Define separate provider environment variables for each modality:
  - `RAG_TEXT_PROVIDER`
  - `RAG_VLM_PROVIDER`
  - `RAG_EMBEDDING_PROVIDER`
- Rationale: Allows independent routing across providers per modality while preserving a uniform call interface.
- Alternatives considered: Single global provider variable (insufficient flexibility), mandatory explicit provider with no default (higher setup friction).

## Decision 6: Provider Default Value
- Decision: Default each modality provider to `hosted_vllm` when not explicitly set.
- Rationale: Provides a predictable baseline configuration and keeps existing setups working without extra env edits.
- Alternatives considered: No default (fail-fast but less ergonomic), defaulting to provider-specific names tied to one vendor.

## Decision 7: Model Routing Composition
- Decision: Compose LiteLLM model identifiers as `<provider>/<model>` for text, VLM, and embedding calls.
- Rationale: Explicit composition preserves compatibility with provider-routed LiteLLM backends and avoids ambiguous model resolution.
- Alternatives considered: Passing raw model name only (insufficient for provider-keyed routing).

## Decision 8: Document Handle Lifecycle
- Decision: Open each source PDF once per request and cache handles as `dict[str, fitz.Document]` on `RAGAgent`, outside serializable LangGraph state.
- Rationale: `fitz.Document` is non-serializable; request-scoped cache avoids repeated open overhead and prevents graph state serialization issues.
- Alternatives considered: Re-open per page (performance penalty), placing handles in graph state (serialization risk).

## Decision 9: Image Description Batching
- Decision: Batch image description calls per page using `VLM_BATCH_SIZE`, preserving image order and page association.
- Rationale: Reduces API round trips while maintaining deterministic provenance at page granularity.
- Alternatives considered: One call per image (higher latency), cross-page batching (context/provenance ambiguity).

## Decision 10: Output Payload Shape
- Decision: Exclude retained page content from `extracted_pages`; return compiled text only in `compiled_material`.
- Rationale: Prevents payload bloat while preserving the audit record required by Planner.
- Alternatives considered: Retaining page text in response (larger payload, redundant content).

## Implementation Outcomes (2026-06-08)
- Provider-aware routing is now applied across text, VLM, and embedding calls via `<provider>/<model>` composition.
- Default provider value `hosted_vllm` is active for all three modalities when provider env vars are unset.
- Request execution now loads runtime model configs once per run and reuses open `fitz.Document` handles for page processing.
- Full regression suite passes (`pytest -q`: 21 passed).
- Representative runtime validation completed on sample input: 1.93s, `status=complete`, 6 pages processed, 5 included.

## Tradeoffs Observed
- Requiring explicit embedding model configuration improves correctness but introduces startup failure when env is missing.
- Embedding and LLM calls remain network/service dependent; fallback logic keeps pipeline non-fatal for per-page relevance when embedding calls fail.