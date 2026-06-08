# Quickstart: Teaching Agent

## 1. Install dependencies

No new packages are required beyond the project's existing `requirements.txt`:

```
pydantic>=2.0
litellm>=1.40.0
pytest>=8.0.0
```

## 2. Configure environment variables

The teaching agent reads all configuration from environment variables. At minimum, set one of `TEACHING_API_BASE` or `TEACHING_API_KEY` to enable LLM calls.

| Variable                        | Default            | Notes                                          |
|---------------------------------|--------------------|------------------------------------------------|
| `TEACHING_MODEL`                | `claude-sonnet-4-6` | Any LiteLLM-compatible model string           |
| `TEACHING_API_BASE`             | —                  | Required for local vLLM (e.g., `http://localhost:8000/v1`) |
| `TEACHING_API_KEY`              | —                  | Required for hosted providers                  |
| `TEACHING_TEMPERATURE`          | `0.7`              | Optional                                       |
| `TEACHING_BEGINNER_MAX_TOKENS`  | `512`              | Optional override                              |
| `TEACHING_INTERMEDIATE_MAX_TOKENS` | `1024`          | Optional override                              |
| `TEACHING_ADVANCED_MAX_TOKENS`  | `2048`             | Optional override                              |

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

All tests mock the LLM call — no API credentials required to run the test suite.

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

## 8. Notes

- The Teaching Agent is always called by the Planner Agent. Direct invocation via CLI is only for development and testing.
- Mermaid diagram validation is structural (regex-based). Visual rendering is handled by the Streamlit UI — validate there if a diagram appears broken despite passing the agent's check.
- All three token ceilings are enforced at the LiteLLM `max_tokens` parameter level and also reported in `metadata.tokens_used`.
