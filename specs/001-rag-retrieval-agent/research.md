# Research: RAG Retrieval Agent

## Decision 1: PDF Extraction Library
- Decision: Use PyMuPDF for all PDF-related operations (page count, text extraction, table detection, image extraction).
- Rationale: PyMuPDF supports all required per-page primitives in one dependency and has performant random-access page APIs that fit synchronous processing.
- Alternatives considered: pdfplumber (table support is useful but weaker image handling integration), pypdf (lightweight but lacks robust table extraction), OCR-first stacks (out of scope for v1 assumptions).

## Decision 2: LLM/VLM Invocation Layer
- Decision: Route all model calls through LiteLLM via a single call_llm(messages, config) abstraction in rag_agent/llm_client.py.
- Rationale: A single call path reduces provider lock-in and keeps the agent independent from vendor-specific SDKs.
- Alternatives considered: Direct provider SDKs (higher lock-in, duplicated logic), LangChain model wrappers as primary call layer (unnecessary extra abstraction for this scope).

## Decision 3: Runtime Configuration Source
- Decision: Load model configuration from environment variables (model name, api_base, api_key, temperature, max_tokens), with defaults centralized in rag_agent/config.py.
- Rationale: Environment variables are deployment-friendly, avoid secrets in code, and allow local vLLM and hosted APIs without code changes.
- Alternatives considered: Hard-coded config constants (not portable), static JSON config file only (less secure for key management), CLI flag-only configuration (harder for orchestration environments).

## Decision 4: Agent Reasoning Loop Runtime
- Decision: Implement the page-processing reasoning loop with LangGraph state transitions and tool nodes.
- Rationale: LangGraph provides explicit stateful orchestration and deterministic control surfaces around non-deterministic LLM decisions.
- Alternatives considered: Hand-rolled while loop with ad-hoc tool dispatch (less observable and harder to extend), LangChain AgentExecutor only (less explicit state graph control).

## Decision 5: Relevance Scoring Strategy
- Decision: Use sentence-transformers all-MiniLM-L6-v2 loaded once at RAGAgent initialization; score page_content against user_prompt by cosine similarity.
- Rationale: Lightweight embeddings with good semantic quality for educational-topic retrieval, minimizing repeated model load overhead.
- Alternatives considered: Larger embedding models (higher latency/memory), keyword-only scoring (insufficient semantic match quality).

## Decision 6: Table Serialization Approach
- Decision: Convert extracted 2D table matrices into Markdown tables in helpers.serialize_table_to_markdown.
- Rationale: Markdown is the final output format and keeps table content directly usable in compilation context.
- Alternatives considered: HTML tables (less consistent with output requirement), CSV serialization (loses contextual readability in compiled material).

## Decision 7: Failure Handling and Status Derivation
- Decision: Treat per-page and per-file extraction failures as non-fatal where possible; collect errors and derive output status as complete, partial, or failed.
- Rationale: Planner requires actionable partial outputs when at least one file/page succeeds.
- Alternatives considered: Fail-fast on first error (reduces usable output), silent skip without error list (breaks auditability).

## Decision 8: Additional Libraries
- Decision: Do not introduce additional external libraries beyond requested dependencies and pytest for testing.
- Rationale: Current requirements are satisfiable with the selected stack; avoiding new dependencies keeps implementation risk low.
- Alternatives considered: Adding PDF fixture-generation tooling; rejected for now because static sample assets satisfy testing requirements.

---

## Decision 9 (v2): fitz Document Lifecycle — One-Time Load Per Request
- Decision: Store open `fitz.Document` handles in a `dict[str, fitz.Document]` on the `RAGAgent` instance, populated before `graph.invoke()` and released in a `finally` block after it returns.
- Rationale: `fitz.Document` is a native C object that cannot be pickled; placing it in LangGraph `AgentState` breaks checkpointing and graph portability. Instance-level storage is the standard approach for non-serializable resources in LangGraph pipelines.
- Alternatives considered: fitz.Document in AgentState (breaks checkpointing), pre-built list of fitz.Page objects (loses document metadata access), thread-local context (unnecessary for single-threaded synchronous processing).

## Decision 10 (v2): VLM Image Batching Per Page
- Decision: Chunk images per page into batches of `RAG_VLM_BATCH_SIZE` (default 4); send each batch as a multi-image LiteLLM content message; concatenate descriptions in order.
- Rationale: Modern VLMs accept multi-image content arrays in a single API call. Batching per page reduces round-trips while preserving page-level provenance. Cross-page batching would blur context association.
- Alternatives considered: One call per image (O(N) round-trips), batch across pages (provenance ambiguity), batch per file (same provenance issue).

## Decision 11 (v2): Image Description Prompt — General + Contextual
- Decision: `IMAGE_DESCRIPTION_PROMPT` combines a general educational-content analyst instruction with a context line embedding the user's study prompt.
- Rationale: Anchoring to the user prompt biases VLM output toward topic-relevant visual content (diagrams, equations) and away from decorative noise.
- Alternatives considered: Generic description-only prompt (topic-agnostic output), long multi-paragraph instruction (wastes VLM token budget).

## Decision 12 (v2): retained_content Removed from Output Schema
- Decision: Remove `ExtractedPage.retained_content` from the Pydantic schema entirely. Internally assembled page text is kept as plain strings in the agent during `_compile_material`, never written to `ExtractedPage`.
- Rationale: Per-page full text in output multiplies payload size linearly. Downstream consumers need only `compiled_material`. Audit metadata (status, score, errors) suffices for diagnostics.
- Alternatives considered: Strip at serialization time (misleading schema), keep as `Optional[str] = None` (semantically ambiguous), keep field (payload bloat).

## Decision 13 (v2): Import Grouping Convention
- Decision: Enforce three grouped import blocks (stdlib → third-party → project-local) separated by blank lines across all modules in `rag_agent/` and `project/`.
- Rationale: Matches PEP 8 and isort conventions; improves dependency scanability and future linting enforcement via `ruff I` rules.
- Alternatives considered: Flat alphabetical imports (mixes stdlib/third-party), ad-hoc ordering (inconsistent across files).

## Decision 14 (v2): .env.local and requirements.txt Sectioning
- Decision: Single `.env.local` with comment-based section headers (`# === Shared ===`, `# === RAG Agent ===`, placeholder sections for Planner/Teaching). Single `requirements.txt` with comment-based sections (`# --- Shared ---`, `# --- RAG Agent ---`, placeholder sections, `# --- Development / Testing ---`).
- Rationale: All standard dotenv parsers and pip ignore `#` comments. Sections improve discoverability without breaking existing tooling.
- Alternatives considered: Separate `.env.<agent>` files (multiple files to source), separate requirements files (install complexity).
