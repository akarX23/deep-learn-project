"""Performance-budget validation for the reflection loop (T048, FR-018 / SC-007).

Times TeachingAgent.run() for each output mode at N=0 (reflection off) and N=1
(one reflection iteration) against a single pinned model + endpoint, and checks
the per-configuration wall-clock budgets:

    reflection off (N=0):  beginner <= 5s,  intermediate <= 10s, advanced <= 20s
    1 iteration   (N=1):   beginner <= 15s, intermediate <= 25s, advanced <= 45s

Records a documented table to teaching_agent/tests/outputs/perf_<timestamp>.md and
flags any breach. The advanced N=1 row exercises both the generation and revision
calls at the 4096 ceiling, confirming no timeout there.

Requires a reachable LLM endpoint (set TEACHING_MODEL etc.) — like run_samples.py,
this is a manual dev harness, not a hermetic pytest test.

Run:
    PYTHONPATH=. python teaching_agent/tests/perf_reflection.py
"""

from __future__ import annotations

import os
import pathlib
import time
from datetime import UTC, datetime

from teaching_agent.agent import TeachingAgent

TOPIC = "What is gradient descent?"
MODES = ["beginner", "intermediate", "advanced"]

# Per-configuration wall-clock budgets in seconds (FR-018 / plan Performance Goals).
BUDGETS_S = {
    0: {"beginner": 5, "intermediate": 10, "advanced": 20},
    1: {"beginner": 15, "intermediate": 25, "advanced": 45},
}

OUTPUTS_DIR = pathlib.Path(__file__).parent / "outputs"


def _clear_per_mode_iteration_overrides() -> None:
    """Drop per-mode N overrides so the global TEACHING_MAX_REFLECTION_ITERATIONS wins."""
    for mode in MODES:
        os.environ.pop(f"TEACHING_{mode.upper()}_MAX_REFLECTION_ITERATIONS", None)


def measure() -> list[dict]:
    """Run the mode x N matrix, timing each TeachingAgent.run()."""
    _clear_per_mode_iteration_overrides()
    agent = TeachingAgent()
    rows: list[dict] = []
    for n in (0, 1):
        os.environ["TEACHING_MAX_REFLECTION_ITERATIONS"] = str(n)
        for mode in MODES:
            t0 = time.perf_counter()
            result = agent.run({"topic": TOPIC, "output_mode": mode, "context": ""})
            elapsed = time.perf_counter() - t0
            budget = BUDGETS_S[n][mode]
            rows.append({
                "n": n,
                "mode": mode,
                "status": result.status,
                "time_s": elapsed,
                "budget_s": budget,
                "within_budget": elapsed <= budget,
                "tokens_used": result.metadata.tokens_used,
                "reflection_iterations": result.metadata.reflection_iterations,
            })
    return rows


def render_markdown(rows: list[dict]) -> str:
    """Render the results as a Markdown table with budget pass/fail."""
    lines = [
        f"# Reflection performance budget — {datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
        f"Topic: {TOPIC!r} · model: {os.getenv('TEACHING_MODEL', 'unset')}",
        "",
        "| N | mode | status | time (s) | budget (s) | within | tokens | iters |",
        "|---|------|--------|---------:|-----------:|:------:|-------:|------:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['n']} | {r['mode']} | {r['status']} | {r['time_s']:.2f} | "
            f"{r['budget_s']} | {'yes' if r['within_budget'] else 'NO'} | "
            f"{r['tokens_used']} | {r['reflection_iterations']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    rows = measure()
    OUTPUTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUTPUTS_DIR / f"perf_{stamp}.md"
    out_path.write_text(render_markdown(rows), encoding="utf-8")
    print(render_markdown(rows))
    print(f"Saved: {out_path}")

    ok_rows = [r for r in rows if r["status"] == "ok"]
    if not ok_rows:
        print(
            "\nNo successful runs — budgets NOT validated (needs a reachable LLM "
            "endpoint; set TEACHING_MODEL and provider credentials)."
        )
        return 1
    breaches = [r for r in ok_rows if not r["within_budget"]]
    if breaches:
        print(f"\n{len(breaches)} budget breach(es):")
        for r in breaches:
            print(f"  N={r['n']} {r['mode']}: {r['time_s']:.2f}s > {r['budget_s']}s")
        return 1
    print(f"\nAll {len(ok_rows)} successful runs within budget.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
