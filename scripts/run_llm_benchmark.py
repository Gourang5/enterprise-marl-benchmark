#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

from enterprise_env.evaluation.llm import (
    OLLAMA_DEFAULT_MODEL,
    ANTHROPIC_DEFAULT_MODEL,
    GROQ_DEFAULT_MODEL,
    GEMINI_DEFAULT_MODEL,
    QWEN_DEFAULT_MODEL,
    make_client,
)
from enterprise_env.evaluation.metrics import aggregate
from enterprise_env.evaluation.runner import run_llm_episode


TASKS = [
    "customer_incident",
    "product_launch",
    "meeting_conflict",
    "launch_readiness",
    "budget_approval",
    "vendor_onboarding",
]

PROVIDER_DEFAULTS = {
    "gemini":    GEMINI_DEFAULT_MODEL,       # FREE — aistudio.google.com
    "qwen":      QWEN_DEFAULT_MODEL,         # FREE — dashscope.aliyuncs.com
    "groq":      GROQ_DEFAULT_MODEL,         # FREE — console.groq.com
    "ollama":    OLLAMA_DEFAULT_MODEL,       # local, no key
    "anthropic": ANTHROPIC_DEFAULT_MODEL,    # paid
}

# Environment variable that holds the API key for each provider
PROVIDER_KEY_ENV = {
    "gemini":    "GEMINI_API_KEY",
    "qwen":      "DASHSCOPE_API_KEY",
    "groq":      "GROQ_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def _default_model(provider: str) -> str | None:
    return PROVIDER_DEFAULTS.get(provider)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Enterprise MARL LLM benchmark episodes.\n\n"
            "FREE providers (no credit card):\n"
            "  gemini  — Google Gemini 2.0 Flash; get key at aistudio.google.com  (set GEMINI_API_KEY)\n"
            "  qwen    — Alibaba Qwen-Turbo via DashScope; get key at dashscope.aliyuncs.com  (set DASHSCOPE_API_KEY)\n"
            "  groq    — Groq Cloud LLaMA 3.1; get key at console.groq.com  (set GROQ_API_KEY)\n\n"
            "Other providers:\n"
            "  ollama  — local Ollama daemon (no API key required, slow on CPU)\n"
            "  anthropic — Claude API (set ANTHROPIC_API_KEY)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--provider",
        choices=["gemini", "qwen", "groq", "ollama", "anthropic"],
        default="gemini",
        help=(
            "LLM provider. Free options: gemini, qwen, groq. "
            "No-key local: ollama. Paid: anthropic."
        ),
    )

    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model name for the selected provider. "
            "Defaults: gemini=gemini-1.5-flash, qwen=qwen-turbo, groq=llama-3.1-8b-instant, "
            "ollama=qwen2.5:3b, anthropic=claude-haiku-4-5-20251001."
        ),
    )

    parser.add_argument(
        "--api-key",
        default=None,
        help=(
            "API key for the selected provider. "
            "If omitted, reads from the environment variable for that provider "
            "(GEMINI_API_KEY, DASHSCOPE_API_KEY, GROQ_API_KEY, ANTHROPIC_API_KEY)."
        ),
    )

    parser.add_argument(
        "--task",
        choices=["all", *TASKS],
        default="all",
        help="Task to benchmark. Use 'all' to run every task.",
    )

    parser.add_argument(
        "--no-hints",
        action="store_true",
        default=False,
        help=(
            "Disable workflow hints — evaluates the LLM as a zero-shot autonomous agent. "
            "Without hints, the model must reason about the task from scratch using only "
            "the objective and visible environment state. Expect significantly lower success rates."
        ),
    )

    parser.add_argument(
        "--mode",
        choices=["centralized", "decentralized"],
        default="centralized",
        help=(
            "Agent-control mode. "
            "'centralized' uses a team controller; "
            "'decentralized' uses role-local decision making."
        ),
    )

    parser.add_argument(
        "--episodes",
        type=int,
        default=1,
        help="Number of episodes to run per selected task.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=100,
        help=(
            "Starting seed. Additional episodes increment this seed "
            "by one."
        ),
    )

    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "Optional Ollama API base URL. "
            "Example: http://localhost:11434"
        ),
    )

    parser.add_argument(
        "--output",
        default="benchmark_results/llm_results.json",
        help="Path for the JSON benchmark result file.",
    )

    return parser


def _write_results(
    output_path: Path,
    provider: str,
    model: str,
    mode: str,
    results: list[dict],
    summary: dict,
) -> None:
    """Write JSON and CSV benchmark artifacts."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "provider": provider,
        "model": model,
        "mode": mode,
        "tasks": sorted({result["task"] for result in results}),
        "results": results,
        "summary": summary,
    }

    output_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    csv_path = output_path.with_suffix(".csv")

    fields = [
        "task",
        "seed",
        "success",
        "truncated",
        "steps",
        "reward",
        "progress",
        "invalid_actions",
        "invalid_action_rate",
        "repeated_actions",
        "permission_violations",
        "constraint_violations",
        "policy_error",
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )
        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    field: result.get(field)
                    for field in fields
                }
            )

    print(
        f"Saved benchmark results to {output_path} "
        f"and {csv_path}"
    )


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.episodes < 1:
        parser.error("--episodes must be at least 1")

    model = args.model or _default_model(args.provider)

    if not model:
        parser.error(
            f"--model is required for provider={args.provider}"
        )

    # Resolve API key: CLI flag > env var
    api_key = args.api_key
    if not api_key and args.provider in PROVIDER_KEY_ENV:
        api_key = os.getenv(PROVIDER_KEY_ENV[args.provider])
        if not api_key:
            parser.error(
                f"Provider '{args.provider}' requires an API key. "
                f"Pass --api-key or set {PROVIDER_KEY_ENV[args.provider]} in the environment."
            )

    try:
        client = make_client(
            args.provider,
            model,
            api_key=api_key,
            base_url=getattr(args, "base_url", None),
        )
    except Exception as exc:
        parser.error(str(exc))

    # Validate provider connectivity and model availability before starting episodes.
    if hasattr(client, "preflight"):
        try:
            status = client.preflight()
        except Exception as exc:
            parser.error(str(exc))

        if args.provider == "ollama":
            print(f"Ollama ready: model={status['model']} base_url={status['base_url']}")
        elif args.provider == "gemini":
            print(f"Gemini ready: model={status['model']}")
            # preflight may have resolved a fallback model — update local var for display
            model = status["model"]

    selected_tasks = (
        TASKS
        if args.task == "all"
        else [args.task]
    )

    results: list[dict] = []

    print()
    print("Enterprise MARL LLM Benchmark")
    print("=" * 60)
    print(f"Provider : {args.provider}")
    print(f"Model    : {model}")
    print(f"Mode     : {args.mode}")
    print(f"Tasks    : {', '.join(selected_tasks)}")
    print(f"Episodes : {args.episodes} per task")
    print(f"Seed     : {args.seed}")
    _FREE = {"gemini", "qwen", "groq"}
    if args.provider == "ollama":
        print("Tip      : For faster inference try a free hosted provider:")
        print("           --provider gemini  (GEMINI_API_KEY  — aistudio.google.com)")
        print("           --provider qwen    (DASHSCOPE_API_KEY — dashscope.aliyuncs.com)")
        print("           --provider groq    (GROQ_API_KEY    — console.groq.com)")
    elif args.provider in _FREE:
        print(f"Tip      : Free hosted API — expect <2 s/call vs ~10 s/call with local Ollama")
    print("=" * 60)
    print()

    for task in selected_tasks:
        for episode_index in range(args.episodes):
            seed = args.seed + episode_index

            print(
                f"Running "
                f"provider={args.provider} "
                f"model={model} "
                f"task={task} "
                f"seed={seed}"
            )

            result = run_llm_episode(
                task,
                client,
                seed=seed,
                mode=args.mode,
                no_hints=args.no_hints,
            )

            results.append(result)

            failure_taxonomy = result.get(
                "failure_taxonomy",
                {},
            )

            print(
                "  "
                f"success={result['success']} "
                f"progress={result['progress']:.2f} "
                f"steps={result['steps']} "
                f"reward={result['reward']:.2f} "
                f"invalid_rate="
                f"{result.get('invalid_action_rate', 0.0):.2f} "
                f"permission_violations="
                f"{result.get('permission_violations', 0)} "
                f"constraint_violations="
                f"{result.get('constraint_violations', 0)} "
                f"error={result.get('policy_error')}"
            )

            if failure_taxonomy:
                active_failures = {
                    name: value
                    for name, value in failure_taxonomy.items()
                    if value
                }

                if active_failures:
                    print(
                        "  failure_taxonomy="
                        f"{json.dumps(active_failures)}"
                    )

            print()

    summary = {
        task: aggregate(
            [
                result
                for result in results
                if result["task"] == task
            ]
        )
        for task in selected_tasks
    }

    output_path = Path(args.output)

    _write_results(
        output_path=output_path,
        provider=args.provider,
        model=model,
        mode=args.mode,
        results=results,
        summary=summary,
    )

    print()
    print("SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()