from __future__ import annotations
from typing import Any
from .baseline import make_baseline
from .random_policy import RandomPolicy
from .llm import LLMPolicy, LLMClient
from ..factory import make_env
from .diagnostics import classify_failures


def _episode(task_name: str, policy, max_steps=None, seed=42) -> dict[str, Any]:
    env = make_env(task_name, max_steps)
    env.reset(seed=seed)
    total = 0.0; done = False; trunc = False; info: dict[str, Any] = {}
    policy_error = None
    while not done and not trunc:
        try:
            action = policy.action(env)
            _, reward, done, trunc, info = env.step(action)
            total += reward
            if hasattr(policy, "observe_result"):
                policy.observe_result(action, info, reward)
        except Exception as exc:
            policy_error = f"{type(exc).__name__}: {exc}"
            break
    trajectory = env.get_trajectory()
    invalid = sum(not bool(x["result"].get("success")) for x in trajectory)
    repeated = 0
    seen = set()
    for x in trajectory:
        key = (x["agent"], x["app"], x["action"], repr(sorted(x["parameters"].items())))
        if key in seen: repeated += 1
        seen.add(key)
    result = {
        "task": task_name,
        "seed": seed,
        "success": done,
        "truncated": trunc,
        "policy_error": policy_error,
        "steps": env.step_count,
        "reward": total,
        "progress": info.get("progress", env.verifier.progress(env.repo)),
        "invalid_actions": invalid,
        "invalid_action_rate": invalid / max(1, env.step_count),
        "repeated_actions": repeated,
        "trajectory": trajectory,
    }
    result["failure_taxonomy"] = classify_failures(result)
    result["permission_violations"] = int(result["failure_taxonomy"].get("permission_failure", 0))
    result["constraint_violations"] = int(result["failure_taxonomy"].get("constraint_violation", 0))
    if hasattr(policy, "stats"):
        result["llm"] = policy.stats.as_dict()
    env.close()
    return result


def run_episode(task_name="customer_incident", max_steps=None, seed=42):
    return _episode(task_name, make_baseline(task_name), max_steps, seed)


def run_random_episode(task_name="customer_incident", max_steps=None, seed=42):
    return _episode(task_name, RandomPolicy(seed), max_steps, seed)


def run_llm_episode(task_name: str, client: LLMClient, max_steps=None, seed=42, retries: int = 1, mode: str = "centralized", no_hints: bool = False):
    return _episode(task_name, LLMPolicy(client=client, retries=retries, mode=mode, no_hints=no_hints), max_steps, seed)
