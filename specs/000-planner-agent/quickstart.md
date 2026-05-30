# Quickstart: Planner Agent

## Prerequisites

- Python 3.11+
- Dependencies installed: `pip install -r requirements.txt`
- Environment variables configured (see below)

## Environment Variables

```bash
# Required: LLM configuration (via LiteLLM)
export PLANNER_LLM_MODEL="gpt-4o-mini"          # or any LiteLLM-supported model
export PLANNER_API_BASE="http://localhost:11434"  # optional: local vLLM/Ollama endpoint
export PLANNER_API_KEY="sk-..."                   # optional: only for hosted APIs

# Optional: tuning
export PLANNER_CONFIDENCE_THRESHOLD="0.6"  # routing confidence cutoff (default: 0.6)
export PLANNER_MAX_RETRIES="3"             # max retry attempts on payload failure (default: 3)
export PLANNER_TEMPERATURE="0.2"           # LLM temperature (default: 0.2 for determinism)
export PLANNER_MAX_TOKENS="512"            # max tokens per LLM call (default: 512)
```

## Run the Planner Agent (CLI)

```bash
# From repository root
python -m planner_agent.agent --input planner_agent/tests/inputs/sample_input.json
```

Expected output (truncated):

```json
{
  "status": "routed",
  "routing_decision": {
    "target_agent": "RAG_AGENT",
    "confidence_score": 0.91,
    "query_was_rewritten": false,
    "hyde_applied": false,
    "constructed_payload": { "..." }
  },
  "errors": []
}
```

## Run Tests

```bash
# Run full test suite
pytest planner_agent/tests/ -v

# Run a specific test group
pytest planner_agent/tests/test_planner_agent.py -v -k "routing"
pytest planner_agent/tests/test_planner_agent.py -v -k "ambiguous"
pytest planner_agent/tests/test_planner_agent.py -v -k "registry"

# Run with coverage
pytest planner_agent/tests/ --cov=planner_agent --cov-report=term-missing
```

## Test Input Fixtures

### Sample PlannerInput (`planner_agent/tests/inputs/sample_input.json`)

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440001",
  "user_query": "Explain gradient descent from the uploaded chapter",
  "session_context": null,
  "available_files": ["rag_agent/tests/inputs/sample.pdf"],
  "schema_version": "1.0"
}
```

### Sample Query Set (`planner_agent/tests/inputs/sample_queries.json`)

A labeled set of queries used for routing accuracy tests (SC-002):

```json
[
  {"query": "Explain gradient descent from the chapter", "expected_agent": "RAG_AGENT"},
  {"query": "Teach me about backpropagation step by step", "expected_agent": "TEACHING_AGENT"},
  {"query": "Quiz me on neural networks", "expected_agent": "QUIZ_EVAL_AGENT"},
  {"query": "help", "expected_agent": "UNKNOWN"},
  {"query": "What is machine learning?", "expected_agent": "TEACHING_AGENT"}
]
```

## Verify a Specific Flow

### Test routing accuracy across labeled queries

```bash
pytest planner_agent/tests/test_planner_agent.py::test_routing_accuracy -v
```

Expected: ≥ 90% of labeled queries route to the correct agent (SC-002).

### Test ambiguous query handling

```bash
pytest planner_agent/tests/test_planner_agent.py::test_ambiguous_query -v
```

Expected: `status == "ambiguous"`, `candidate_agents` non-empty, `constructed_payload == null`.

### Test registry extensibility

```bash
pytest planner_agent/tests/test_planner_agent.py::test_new_agent_registration -v
```

Expected: Stub agent registers and routes without changes to agent.py, classifier.py.

### Test HyDE augmentation

```bash
pytest planner_agent/tests/test_planner_agent.py::test_hyde_applied_for_short_rag_query -v
```

Expected: Short RAG-bound query produces `hyde_applied == true` in routing decision.

### Test query rewriting

```bash
pytest planner_agent/tests/test_planner_agent.py::test_query_rewrite_for_short_query -v
```

Expected: Input query "neural nets?" has `query_was_rewritten == true` in output.

## Verify Performance Budget

```bash
pytest planner_agent/tests/test_planner_agent.py::test_routing_latency_budget -v
```

Expected: Single query routing completes within 10 seconds (SC-006). Logs elapsed time.
