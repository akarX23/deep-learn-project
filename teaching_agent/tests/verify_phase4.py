"""Phase 4 verification: real LLM call showing stream tokens and completion content.

Saves four files to teaching_agent/tests/outputs/:
  verify_phase4_input.json         — the input sent to the agent
  verify_phase4_stream_tokens.json — all StreamTokensEventBody events (field+token)
  verify_phase4_completion.md      — raw_markdown sent in TeachingCompletionEvent.content
  verify_phase4_result.json        — full TeachingAgentOutput (status, metadata, content)
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

# Ensure project root is on the path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from teaching_agent.agent import TeachingAgent

INPUT = {
    "topic": "Binary Search Tree",
    "output_mode": "beginner",
    "context": "",
}

stream_events: list[dict] = []


def token_callback(field: str, token: str) -> None:
    stream_events.append({"field": field, "token": token})


print(f"Input:\n{json.dumps(INPUT, indent=2)}\n")
print("Running agent (real LLM call)...\n")

result, raw_markdown = TeachingAgent().run(INPUT, token_callback)

# --- Save files ---
output_dir = Path(__file__).parent / "outputs"
output_dir.mkdir(exist_ok=True)

input_path = output_dir / "verify_phase4_input.json"
stream_path = output_dir / "verify_phase4_stream_tokens.json"
completion_path = output_dir / "verify_phase4_completion.md"
result_path = output_dir / "verify_phase4_result.json"

input_path.write_text(json.dumps(INPUT, indent=2), encoding="utf-8")
stream_path.write_text(json.dumps(stream_events, indent=2), encoding="utf-8")
completion_path.write_text(raw_markdown, encoding="utf-8")
result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

# --- Print stream token summary ---
print(f"=== STREAM TOKENS ({len(stream_events)} events) ===")
by_field: dict[str, list[str]] = defaultdict(list)
for e in stream_events:
    by_field[e["field"]].append(e["token"])

for field, tokens in by_field.items():
    combined = "".join(tokens)
    preview = combined[:300] + "\n...[truncated]" if len(combined) > 300 else combined
    print(f"\n[{field}] — {len(tokens)} chunks, {len(combined)} chars total:")
    print(preview)

# --- Print TeachingCompletionEvent.content ---
print("\n" + "=" * 60)
print("=== TEACHING COMPLETE EVENT — content (raw_markdown) ===")
print("=" * 60)
preview_md = raw_markdown[:600] + "\n...[truncated]" if len(raw_markdown) > 600 else raw_markdown
print(preview_md)

# --- Print result status ---
print("\n" + "=" * 60)
print("=== AGENT RESULT ===")
print(f"status       : {result.status}")
print(f"tokens_used  : {result.metadata.tokens_used}")
print(f"model        : {result.metadata.model}")
diagram_status = "present" if (result.content and result.content.diagram) else "null/absent"
print(f"diagram      : {diagram_status}")

# --- Saved file paths ---
print("\n=== FILES SAVED ===")
print(f"  Input          : {input_path}")
print(f"  Stream tokens  : {stream_path}")
print(f"  Completion .md : {completion_path}")
print(f"  Full result    : {result_path}")
