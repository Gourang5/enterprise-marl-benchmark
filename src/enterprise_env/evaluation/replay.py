from __future__ import annotations
import json
from pathlib import Path
from ..factory import make_env
from ..core.actions import Action


def save_episode(result, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return path


def replay_episode(source, strict=True):
    data = json.loads(Path(source).read_text()) if not isinstance(source, dict) else source
    env = make_env(data["task"])
    env.reset(seed=int(data.get("seed", 42)))
    mismatches = []
    for expected in data.get("trajectory", []):
        action = Action(expected["agent"], expected["app"], expected["action"], expected.get("parameters", {}))
        _, reward, done, trunc, info = env.step(action)
        actual = env.trajectory[-1]
        fields = {
            "success": (actual["result"]["success"], expected.get("result", {}).get("success")),
            "progress": (actual["progress"], expected.get("progress")),
        }
        for field, (a, e) in fields.items():
            if e is not None and a != e:
                mismatches.append({"step": actual["step"], "field": field, "expected": e, "actual": a})
        if done or trunc:
            break
    summary = {"task": data["task"], "seed": data.get("seed", 42), "steps": env.step_count, "success": env.verifier.complete(env.repo), "mismatches": mismatches}
    env.close()
    if strict and mismatches:
        raise AssertionError(f"Replay mismatches: {mismatches[:3]}")
    return summary
