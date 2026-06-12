"""Sample runner — 3 topics × 3 output modes = 9 real LLM calls.

Saves each output to teaching_agent/tests/outputs/<slug>_<mode>.json so you can
compare how explanation depth, diagram usage, and vocabulary change across modes
for the same topic.

Run:
    PYTHONPATH=. python teaching_agent/tests/run_samples.py
"""

from __future__ import annotations

import json
import pathlib

from teaching_agent.agent import TeachingAgent

TOPICS = [
    {"slug": "loop",             "topic": "What is a loop in programming?"},
    {"slug": "recursion",        "topic": "What is recursion?"},
    {"slug": "gradient_descent", "topic": "What is gradient descent?"},
]

MODES = ["beginner", "intermediate", "advanced"]

OUTPUTS_DIR = pathlib.Path(__file__).parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

agent = TeachingAgent()
results: list[dict] = []

for entry in TOPICS:
    print(f"\n{'='*60}")
    print(f"Topic: {entry['topic']}")
    print(f"{'='*60}")
    for mode in MODES:
        print(f"  [{mode}] calling LLM...", end=" ", flush=True)
        raw_input = {"topic": entry["topic"], "output_mode": mode, "context": ""}
        result = agent.run(raw_input)

        out_path = OUTPUTS_DIR / f"{entry['slug']}_{mode}.json"
        out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        status = result.status
        tokens = result.metadata.tokens_used if result.metadata else 0
        diagram = "yes" if result.content and result.content.diagram else "no"
        print(f"status={status}  tokens={tokens}  diagram={diagram}  -> {out_path.name}")

        results.append({
            "topic": entry["topic"],
            "mode": mode,
            "status": status,
            "tokens_used": tokens,
            "has_diagram": diagram == "yes",
        })

print(f"\n{'='*60}")
print("Summary")
print(f"{'='*60}")
print(f"{'Topic':<35} {'Mode':<14} {'Status':<8} {'Tokens':>6}  {'Diagram'}")
print("-" * 75)
for r in results:
    print(
        f"{r['topic']:<35} {r['mode']:<14} {r['status']:<8} {r['tokens_used']:>6}  {'yes' if r['has_diagram'] else 'no'}"
    )

failed = [r for r in results if r["status"] != "ok"]
if failed:
    print(f"\n{len(failed)} run(s) failed.")
else:
    print(f"\nAll 9 runs succeeded. Outputs saved to: {OUTPUTS_DIR}")
