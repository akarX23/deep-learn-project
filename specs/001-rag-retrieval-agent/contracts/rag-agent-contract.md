# Contract: RAG Agent Planner Interface

## Purpose
Defines the request and response contract between Planner and RAG Retrieval Agent.

## Request Schema: RAGAgentInput

```json
{
  "request_id": "uuid-string",
  "user_prompt": "Explain gradient descent from the uploaded chapter",
  "file_paths": [
    "rag_agent/tests/inputs/sample.pdf"
  ],
  "include_tables": true,
  "include_images": true,
  "relevance_threshold": 0.6,
  "schema_version": "1.0"
}
```

### Field constraints
- request_id: required UUID string.
- user_prompt: required non-empty string.
- file_paths: required array of PDF paths.
- include_tables/include_images: optional booleans, default true.
- relevance_threshold: optional float in [0.0, 1.0], default 0.6.
- schema_version: optional string, default "1.0".

## Response Schema: RAGAgentOutput

```json
{
  "request_id": "uuid-string",
  "user_prompt": "Explain gradient descent from the uploaded chapter",
  "schema_version": "1.0",
  "compiled_material": "# Study Material\\n...",
  "extracted_pages": [
    {
      "file_name": "sample.pdf",
      "page_number": 1,
      "relevance_score": 0.84,
      "status": "SUCCESS",
      "ocr_used": false,
      "errors": []
    }
  ],
  "total_pages_processed": 6,
  "total_pages_included": 4,
  "errors": [],
  "status": "complete"
}
```

### extracted_pages item constraints
- status enum: SUCCESS | SKIPPED_IRRELEVANT | FAILED_EXTRACTION.
- page_number is 1-based.
- relevance_score is normalized to [0.0, 1.0].
- ocr_used is always false in v1.
- retained_content is intentionally absent; compiled_material is the only assembled text in the response.

## Status semantics
- complete: all reachable files/pages processed with usable output and no blocking errors.
- partial: some pages/files failed, but usable compiled material exists.
- failed: no usable compiled material can be produced.

## Error handling contract
- Non-fatal issues are accumulated in response.errors and/or per-page errors.
- Fatal runtime errors raise exceptions and may produce failed status when captured by caller boundary.

## Determinism and ordering
- Tool call order is LLM-driven (non-deterministic) under LangGraph orchestration.
- Output schema and field semantics remain deterministic regardless of call order.
