#!/usr/bin/env python3
"""Difficulty-split benchmark table.

Runs each task at every difficulty level (easy / medium / hard / adversarial)
using the deterministic rule baseline and the random baseline.  Reports how
distractor density affects success rate, reward, and average steps.

Usage:
    python scripts/run_difficulty_benchmark.py --episodes 10
    python scripts/run_difficulty_benchmark.py --task meeting_conflict --episodes 20

Output:
    benchmark_results/difficulty_results.json
    benchmark_results/difficulty_results.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enterprise_env.generation import ScenarioFactory, PRESETS
from enterprise_env.evaluation.baseline import make_baseline
from enterprise_env.evaluation.random_policy import RandomPolicy
from enterprise_env.evaluation.metrics import aggregate


TASKS = [
    "customer_incident",
    "product_launch",
    "meeting_conflict",
    "launch_readiness",
    "budget_approval",
    "vendor_onboarding",
]

DIFFICULTIES = ["easy", "medium", "hard", "adversarial"]

factory = ScenarioFactory()


def _run_episode_on_factory(task_name: str, policy, seed: int, difficulty: str) -> dict[str, Any]:
    """Run one episode using a ScenarioFactory-built env (includes distractor injection)."""
    env, _, _ = factory.build(task_name, seed=seed, difficulty=difficulty)
    total = 0.0
    done = False
    trunc = False
    info: dict[str, Any] = {}
    policy_error = None
    while not done and not trunc:
        try:
            action = policy.action(env)
            _, reward, done, trunc, info = env.step(action)
            total += reward
        except Exception as exc:
            policy_error = f"{type(exc).__name__}: {exc}"
            break
    trajectory = env.get_trajectory()
    invalid = sum(not bool(x["result"].get("success")) for x in trajectory)
    result = {
        "task": task_name,
        "seed": seed,
        "difficulty": difficulty,
        "distractors": PRESETS[difficulty].distractors or 0,
        "success": done,
        "truncated": trunc,
        "policy_error": policy_error,
        "steps": env.step_count,
        "reward": total,
        "progress": info.get("progress", env.verifier.progress(env.repo)),
        "invalid_actions": invalid,
        "invalid_action_rate": invalid / max(1, env.step_count),
    }
    env.close()
    return result


def _make_policy(policy_name: str, task_name: str, seed: int):
    if policy_name == "deterministic":
        return make_baseline(task_name)
    if policy_name == "random":
        return RandomPolicy(seed)
    raise ValueError(f"Unknown policy: {policy_name}")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Difficulty-split benchmark across distractor densities")
    p.add_argument("--task", choices=["all", *TASKS], default="all")
    p.add_argument("--episodes", type=int, default=10, help="Episodes per (task, difficulty, policy)")
    p.add_argument("--seed", type=int, default=100)
    p.add_argument("--output", default="benchmark_results/difficulty_results.json")
    return p


def main() -> None:
    args = _build_parser().parse_args()
    selected = TASKS if args.task == "all" else [args.task]

    print()
    print("Enterprise MARL — Difficulty-Split Benchmark")
    print("=" * 68)
    print(f"Tasks      : {', '.join(selected)}")
    print(f"Difficulty : {', '.join(DIFFICULTIES)}")
    print(f"Episodes   : {args.episodes} per (task × difficulty × policy)")
    print("Policies   : deterministic baseline + random baseline")
    print("=" * 68)

    all_rows: list[dict] = []
    report: dict[str, Any] = {}

    for task in selected:
        report[task] = {}
        print(f"\n── {task} ──")
        for diff in DIFFICULTIES:
            distractors = PRESETS[diff].distractors or 0
            diff_results: dict[str, dict] = {}
            for policy_name in ("deterministic", "random"):
                episodes = []
                for i in range(args.episodes):
                    seed = args.seed + i
                    policy = _make_policy(policy_name, task, seed)
                    result = _run_episode_on_factory(task, policy, seed, diff)
                    episodes.append(result)
                agg = aggregate(episodes)
                diff_results[policy_name] = agg
                icon = "✅" if agg["success_rate"] == 1.0 else ("⚠️" if agg["success_rate"] > 0 else "❌")
                print(
                    f"  {diff:<12} {policy_name:<14} "
                    f"SR={agg['success_rate']:.0%}  "
                    f"R={agg['avg_reward']:.1f}  "
                    f"steps={agg['avg_steps']:.1f}  "
                    f"distractors={distractors}  {icon}"
                )
                all_rows.append({
                    "task": task,
                    "difficulty": diff,
                    "distractors": distractors,
                    "policy": policy_name,
                    "episodes": args.episodes,
                    "success_rate": agg["success_rate"],
                    "avg_reward": agg["avg_reward"],
                    "reward_std": agg["reward_std"],
                    "avg_steps": agg["avg_steps"],
                    "avg_progress": agg["avg_progress"],
                    "timeout_rate": agg["timeout_rate"],
                    "avg_invalid_action_rate": agg["avg_invalid_action_rate"],
                })
            report[task][diff] = diff_results

    # ── print summary table ──────────────────────────────────────────────────
    print()
    print("=" * 80)
    print("DIFFICULTY TABLE  (Deterministic SR  vs  Random SR)")
    print("=" * 80)
    print(f"{'Task':<22}{'Easy':>10}{'Medium':>10}{'Hard':>10}{'Adversarial':>14}")
    print(f"{'':22}{'Det/Rnd':>10}{'Det/Rnd':>10}{'Det/Rnd':>10}{'Det/Rnd':>14}")
    print("-" * 68)
    for task in selected:
        row_parts = [f"{task:<22}"]
        for diff in DIFFICULTIES:
            d = report[task][diff]
            det = d["deterministic"]["success_rate"]
            rnd = d["random"]["success_rate"]
            cell = f"{det:.0%}/{rnd:.0%}"
            w = 14 if diff == "adversarial" else 10
            row_parts.append(f"{cell:>{w}}")
        print("".join(row_parts))
    print()

    # ── save results ─────────────────────────────────────────────────────────
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tasks": selected,
        "difficulties": DIFFICULTIES,
        "episodes_per_cell": args.episodes,
        "report": report,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    csv_path = out.with_suffix(".csv")
    if all_rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_rows)

    print(f"Saved {out} and {csv_path}")


if __name__ == "__main__":
    main()
