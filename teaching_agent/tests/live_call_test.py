"""Live API call test — requires .env with TEACHING_MODEL and provider key set.

Run:
    PYTHONPATH=. python teaching_agent/tests/live_call_test.py

This makes a real LLM call. Not part of the automated pytest suite.
"""

from teaching_agent.agent import TeachingAgent
from teaching_agent.config import get_llm_config
from teaching_agent.helpers import build_messages
from teaching_agent.llm_client import call_llm
from teaching_agent.prompts import PROMPT_BY_MODE

# --- Step 1: Direct call_llm check (exposes the raw LiteLLM error if any) ---
print("=== Step 1: Direct LLM call (bypasses agent error-swallowing) ===")
cfg = get_llm_config("beginner")
print(f"model: {cfg.model}  max_tokens: {cfg.max_tokens}")
prompt = PROMPT_BY_MODE["beginner"].format(topic="What is a loop?", context="")
messages = build_messages(prompt)
try:
    content, tokens = call_llm(messages, cfg)
    print(f"SUCCESS — tokens_used: {tokens}")
    print(f"Response (first 200 chars): {content[:200]}\n")
except RuntimeError as exc:
    print(f"FAILED — {exc}\n")
    raise SystemExit(1)

# --- Step 2: Full agent pipeline ---
print("=== Step 2: Full agent pipeline ===")
sample_input = {
    "topic": "What is a loop in programming?",
    "output_mode": "beginner",
    "context": "",
}
result = TeachingAgent().run(sample_input)
print(result.model_dump_json(indent=2))

assert result.status == "ok", f"Expected status='ok', got '{result.status}'"
assert result.content is not None, "content should not be None on success"
assert result.content.explanation, "explanation should be non-empty"
assert result.content.notes, "notes should be non-empty"
assert result.content.diagram is not None, "diagram required in beginner mode"
assert result.metadata.tokens_used > 0, "tokens_used should be > 0"

print("\nLive call test PASSED.")
