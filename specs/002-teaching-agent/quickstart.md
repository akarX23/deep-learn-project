# Quickstart: Teaching Agent

## 1. Install dependencies

No new packages are required beyond the project's existing `requirements.txt`:

```
pydantic>=2.0
litellm>=1.40.0
kafka-python>=2.0.2
pytest>=8.0.0
python-dotenv>=1.0.0
```

## 2. Configure environment variables

Create a `.env` file in the project root (loaded automatically by `teaching_agent/config.py`).

**LLM — required for all runs:**

| Variable | Required | Notes |
|---|---|---|
| `TEACHING_MODEL` | **Yes** | No default. Any LiteLLM string: `groq/llama-3.3-70b-versatile`, `claude-sonnet-4-6`, `gemini/gemini-1.5-flash` |
| `TEACHING_API_BASE` | No | Override for self-hosted/non-standard endpoints |
| `TEACHING_API_KEY` | No | Override; omit to let LiteLLM read the standard provider key |
| `TEACHING_TEMPERATURE` | No | Default `0.7` |
| `TEACHING_BEGINNER_MAX_TOKENS` | No | Default `512` |
| `TEACHING_INTERMEDIATE_MAX_TOKENS` | No | Default `1024` |
| `TEACHING_ADVANCED_MAX_TOKENS` | No | Default `2048` |

Provider keys (`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`, etc.) are read automatically by LiteLLM — no special wiring needed.

**Kafka — required only for the worker (Phase 2):**

| Variable | Required | Notes |
|---|---|---|
| `BACKEND_KAFKA_BOOTSTRAP_SERVERS` | Yes (worker only) | e.g. `localhost:9092` |
| `BACKEND_KAFKA_SECURITY_PROTOCOL` | No | For SASL/SSL clusters |

## 3. Prepare sample input

Use `teaching_agent/tests/inputs/sample_input.json`:

```json
{
  "topic": "Binary Search Tree",
  "output_mode": "intermediate",
  "context": ""
}
```

## 4. Run the agent end-to-end

```bash
python -m teaching_agent.agent --input teaching_agent/tests/inputs/sample_input.json
```

Expected result:
- A schema-valid `TeachingAgentOutput` printed as JSON
- `status: "ok"`
- Non-empty `content.explanation`, `content.notes`, `content.example`
- `content.diagram` present (non-null for intermediate with a structured topic)

## 5. Run tests

```bash
pytest teaching_agent/tests/test_teaching_agent.py -q
```

Tests make **real LLM calls** — `TEACHING_MODEL` must be set in `.env` before running.
Schema, validator, and parse tests run offline with no LLM calls. Agent integration
tests hit the configured model directly.

## 6. Verify mode differentiation

Run the same topic at all three modes and confirm qualitatively different output:

```bash
# Edit sample_input.json: set output_mode to "beginner"
python -m teaching_agent.agent --input teaching_agent/tests/inputs/sample_input.json

# Edit sample_input.json: set output_mode to "advanced"
python -m teaching_agent.agent --input teaching_agent/tests/inputs/sample_input.json
```

Expected differences:
- Beginner: analogy present, diagram non-null, notes are bullet-point only, token count ≤ 512
- Advanced: formal definition present, complexity analysis present, notes are dense technical reference, token count ≤ 2048

## 7. Verify error behavior

Set `topic` to an empty string in `sample_input.json` and run:

- Response should return `status: "error"` with `content: null`
- No exception should propagate

## 8. Run the Kafka worker (Phase 2)

Requires Kafka running locally and `BACKEND_KAFKA_BOOTSTRAP_SERVERS` set in `.env`.
Topics `"teaching"` and `"teaching-complete"` are bootstrapped by the backend service
at startup — start the backend service first, or create the topics manually.

```bash
# Start backend service (bootstraps topics)
uvicorn backend_service.app.main:app --host 0.0.0.0 --port 8001

# In a separate terminal — start the Teaching Agent worker
PYTHONPATH=. python teaching_agent/worker.py
```

The worker subscribes to `"teaching"`, calls `TeachingAgent.run()` for each message,
and publishes a `TeachingCompletionEvent` to `"teaching-complete"` for every request
(including failures).

To test the Kafka path end-to-end, publish a `TeachingRequestEvent` JSON payload to
the `"teaching"` topic using any Kafka client or the Kafka UI at `http://localhost:8080`.

## 9. Notes

- At runtime, the Teaching Agent is invoked exclusively via Kafka. The Planner publishes
  to `"teaching"` and reads results from `"teaching-complete"`. CLI and direct Python
  invocation are for development and testing only.
- Mermaid diagram validation is structural (regex-based). Visual rendering is handled by
  the frontend — validate there if a diagram appears broken despite passing the agent's check.
- Token ceilings are enforced at the LiteLLM `max_tokens` parameter level and reported in
  `metadata.tokens_used` / `TeachingCompletionEvent.tokens_used`.
