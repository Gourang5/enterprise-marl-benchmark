from __future__ import annotations
from collections import Counter


def classify_failures(result):
    """Return interpretable failure labels from a benchmark episode."""
    labels = Counter()
    trajectory = result.get("trajectory", [])
    for row in trajectory:
        message = str((row.get("result") or {}).get("message", "")).lower()
        if not (row.get("result") or {}).get("success", False):
            labels["tool_use_failure"] += 1
        if "unauthorized" in message or "read-only" in message or "not accessible" in message:
            labels["permission_failure"] += 1
        if "conflict" in message:
            labels["constraint_violation"] += 1
        if row.get("action", "").startswith("search") and not ((row.get("result") or {}).get("data") or {}):
            labels["retrieval_failure"] += 1
    seen = set()
    for row in trajectory:
        key = (row.get("agent"), row.get("app"), row.get("action"), repr(sorted((row.get("parameters") or {}).items())))
        if key in seen:
            labels["looping"] += 1
        seen.add(key)
    if result.get("policy_error"):
        labels["policy_failure"] += 1
    if result.get("truncated"):
        labels["planning_or_horizon_failure"] += 1
    if not result.get("success") and not labels:
        labels["incomplete_coordination"] += 1
    return dict(labels)
