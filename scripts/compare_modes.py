#!/usr/bin/env python3
"""Compare centralized vs decentralized LLM agent control modes.

Usage (local Ollama):
    python scripts/compare_modes.py --provider ollama --model qwen2.5:3b --episodes 3

Usage (free cloud — Gemini):
    python scripts/compare_modes.py --provider gemini --episodes 5

Deterministic baseline is always shown as a reference (no LLM needed for that column).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure project src is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enterprise_env.evaluation.runner import run_episode, run_llm_episode
from enterprise_env.evaluation.metrics import aggregate
from enterprise_env.evaluation.llm import make_client, PROVIDER_KEY_ENV, PROVIDER_DEFAULTS


TASKS = [
    "customer_incident",
    "product_launch",
    "meeting_conflict",
    "launch_readiness",
    "budget_approval",
    "vendor_onboarding",
]

MODES = ["centralized", "decentralized"]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Centralized vs decentralized LLM mode comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--provider", choices=["gemini", "qwen", "groq", "ollama", "anthropic"], default="ollama")
    p.add_argument("--model", default=None)
    p.add_argument("--api-key", default=None)
    p.add_argument("--task", choices=["all", *TASKS], default="all")
    p.add_argument("--episodes", type=int, default=3, help="Episodes per task per mode (default 3)")
    p.add_argument("--seed", type=int, default=100)
    p.add_argument("--output", default="benchmark_results/mode_comparison.json")
    p.add_argument("--no-baseline", action="store_true", help="Skip deterministic baseline column")
    return p


def _fmt(agg: dict) -> str:
    sr  = agg.get("success_rate", 0.0)
    rw  = agg.get("avg_reward", 0.0)
    st  = agg.get("avg_steps", 0.0)
    ci  = agg.get("success_rate_95ci", [0, 1])
    return f"SR={sr:.0%} [{ci[0]:.2f},{ci[1]:.2f}]  R={rw:.1f}  steps={st:.1f}"


def main() -> None:
    args = _build_parser().parse_args()
    model = args.model or PROVIDER_DEFAULTS.get(args.provider)
    if not model:
        print(f"[error] --model required for provider={args.provider}", file=sys.stderr)
        sys.exit(1)

    api_key = args.api_key
    if not api_key and args.provider in PROVIDER_KEY_ENV:
        api_key = os.getenv(PROVIDER_KEY_ENV[args.provider])
        if not api_key:
            print(f"[error] Set {PROVIDER_KEY_ENV[args.provider]} or pass --api-key", file=sys.stderr)
            sys.exit(1)

    client = make_client(args.provider, model, api_key=api_key)
    if hasattr(client, "preflight"):
        status = client.preflight()
        if args.provider == "ollama":
            print(f"Ollama ready: model={status['model']}")
        elif args.provider == "gemini":
            print(f"Gemini ready: model={status['model']}")
            model = status["model"]

    selected = TASKS if args.task == "all" else [args.task]

    print()
    print("Enterprise MARL — Centralized vs Decentralized Mode Comparison")
    print("=" * 68)
    print(f"Provider : {args.provider}")
    print(f"Model    : {model}")
    print(f"Episodes : {args.episodes} per task per mode")
    print(f"Tasks    : {', '.join(selected)}")
    print("=" * 68)

    report: dict[str, dict] = {}

    for task in selected:
        print(f"\n── {task} ──")
        task_report: dict[str, dict] = {}

        # Deterministic baseline
        if not args.no_baseline:
            baseline_results = [run_episode(task, seed=args.seed + i) for i in range(args.episodes)]
            baseline_agg = aggregate(baseline_results)
            task_report["deterministic_baseline"] = baseline_agg
            print(f"  baseline     : {_fmt(baseline_agg)}")

        # LLM centralized / decentralized
        for mode in MODES:
            mode_results = []
            for i in range(args.episodes):
                seed = args.seed + i
                print(f"  {mode:<14} seed={seed}  ", end="", flush=True)
                result = run_llm_episode(task, client, seed=seed, mode=mode)
                mode_results.append(result)
                icon = "✅" if result["success"] else "❌"
                print(f"{icon}  steps={result['steps']}  R={result['reward']:.1f}  {result.get('policy_error') or ''}")
            mode_agg = aggregate(mode_results)
            task_report[f"llm_{mode}"] = mode_agg
            print(f"  {mode} AGG: {_fmt(mode_agg)}")

        report[task] = task_report

    # ── print final comparison table ────────────────────────────────────────
    print()
    print("=" * 68)
    print("FINAL COMPARISON TABLE")
    print("=" * 68)
    col_w = 22
    header = f"{'Task':<22}{'Baseline':<{col_w}}{'LLM Centralized':<{col_w}}{'LLM Decentralized'}"
    print(header)
    print("-" * 78)
    for task, tr in report.items():
        def _sr(key: str) -> str:
            return f"{tr[key]['success_rate']:.0%}" if key in tr else "—"
        print(f"{task:<22}{_sr('deterministic_baseline'):<{col_w}}{_sr('llm_centralized'):<{col_w}}{_sr('llm_decentralized')}")
    print()

    # ── save results ─────────────────────────────────────────────────────────
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "provider": args.provider,
        "model": model,
        "episodes": args.episodes,
        "tasks": selected,
        "report": report,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
