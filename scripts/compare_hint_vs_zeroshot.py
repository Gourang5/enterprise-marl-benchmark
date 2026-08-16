#!/usr/bin/env python3
"""Compare hint-guided vs zero-shot LLM performance across all tasks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HINT_FILE   = Path("benchmark_results/llm_results_5ep.json")
ZEROSHOT_FILE = Path("benchmark_results/llm_results_zeroshot.json")

TASKS = [
    "customer_incident",
    "product_launch",
    "meeting_conflict",
    "launch_readiness",
    "budget_approval",
    "vendor_onboarding",
]

TASK_LABELS = {
    "customer_incident":  "Customer Incident",
    "product_launch":     "Product Launch",
    "meeting_conflict":   "Meeting Conflict",
    "launch_readiness":   "Launch Readiness",
    "budget_approval":    "Budget Approval",
    "vendor_onboarding":  "Vendor Onboarding",
}


def load(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: {path} not found. Run the benchmark first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def main() -> None:
    hint_data = load(HINT_FILE)
    zs_data   = load(ZEROSHOT_FILE)

    hint_sum = hint_data["summary"]
    zs_sum   = zs_data["summary"]

    col_w = [22, 10, 10, 10, 8, 8]
    sep = "+" + "+".join("-" * (w + 2) for w in col_w) + "+"

    def row(*cells):
        parts = []
        for cell, w in zip(cells, col_w):
            parts.append(f" {str(cell):<{w}} ")
        return "|" + "|".join(parts) + "|"

    print()
    print("=" * 70)
    print("  HINT-GUIDED vs ZERO-SHOT: Head-to-Head Comparison")
    print(f"  Hint-Guided : {HINT_FILE} ({hint_data['model']})")
    print(f"  Zero-Shot   : {ZEROSHOT_FILE} ({zs_data['model']})")
    print("=" * 70)
    print()
    print(sep)
    print(row("Task", "Oracle", "Hint-Guided", "Zero-Shot", "Δ SR", "Random"))
    print(sep)

    total_hint_sr = 0.0
    total_zs_sr   = 0.0
    n = 0

    for task in TASKS:
        label = TASK_LABELS[task]
        h = hint_sum.get(task, {})
        z = zs_sum.get(task, {})

        h_sr = h.get("success_rate", float("nan"))
        z_sr = z.get("success_rate", float("nan"))
        delta = h_sr - z_sr

        total_hint_sr += h_sr
        total_zs_sr   += z_sr
        n += 1

        sign = "+" if delta >= 0 else ""
        print(row(
            label[:22],
            "100%",
            pct(h_sr),
            pct(z_sr),
            f"{sign}{delta * 100:.0f}pp",
            "0%",
        ))

    print(sep)

    avg_h = total_hint_sr / n if n else 0
    avg_z = total_zs_sr   / n if n else 0
    avg_delta = avg_h - avg_z
    sign = "+" if avg_delta >= 0 else ""
    print(row(
        "AVERAGE",
        "100%",
        pct(avg_h),
        pct(avg_z),
        f"{sign}{avg_delta * 100:.0f}pp",
        "0%",
    ))
    print(sep)

    print()
    print("Interpretation:")
    print(f"  Hint-Guided SR  : {pct(avg_h)} — validates task correctness & reward design")
    print(f"  Zero-Shot SR    : {pct(avg_z)} — measures raw LLM reasoning without workflow context")
    print(f"  Gap             : {sign}{avg_delta * 100:.0f} percentage points")
    print()
    print("  The gap quantifies the value of SOP/RAG-style workflow knowledge.")
    print("  A larger gap → tasks require structured procedural knowledge, not just reasoning.")
    print("  A smaller gap → tasks are solvable by general-purpose common sense.")
    print()

    # Save comparison JSON
    out = {"hint_guided": hint_sum, "zero_shot": zs_sum, "delta": {}}
    for task in TASKS:
        h_sr = hint_sum.get(task, {}).get("success_rate", 0)
        z_sr = zs_sum.get(task, {}).get("success_rate", 0)
        out["delta"][task] = round(h_sr - z_sr, 4)

    out_path = Path("benchmark_results/comparison_hint_vs_zeroshot.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  Comparison saved to {out_path}")


if __name__ == "__main__":
    main()
