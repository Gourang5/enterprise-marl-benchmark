"""factory_v2 — generated-mode enterprise world factory.

Public API:

    from enterprise_env.factory_v2 import CompanySpec, generate_world, build_env, run_generated_episode

    spec  = CompanySpec(seed=42, scenario="vendor_onboarding")
    world = generate_world(spec)          # deterministic; no live env needed
    # world.fingerprint and world.validation_status are set automatically

    env   = build_env(world)             # creates a live EnterpriseEnv
    result = run_generated_episode(world) # oracle run; proves solvability

Legacy / static environments are completely unaffected by this module.
"""
from __future__ import annotations
from typing import Any

from .spec import CompanySpec
from .world import WorldGenerator, GeneratedWorld
from .validator import WorldValidator, ValidationError
from .manifest import build_manifest, compute_fingerprint


def generate_world(spec: CompanySpec, validate: bool = True) -> GeneratedWorld:
    """Generate a validated world from a CompanySpec.

    Same seed + same spec always produces the same world.
    Different seed produces visibly different employees and vendor entities.

    Args:
        spec: Declarative configuration (seed, scenario, difficulty).
        validate: Run WorldValidator after generation (default True).

    Returns:
        GeneratedWorld with fingerprint and validation_status set.

    Raises:
        ValidationError: If validate=True and world has errors.
    """
    world = WorldGenerator(spec).generate()
    world.fingerprint = compute_fingerprint(world)
    if validate:
        validator = WorldValidator()
        errors = validator.validate(world)
        world.validation_status = "PASS" if not errors else "FAIL"
        if errors:
            raise ValidationError(
                f"World (seed={spec.seed}) failed validation:\n"
                + "\n".join(f"  {e}" for e in errors)
            )
    else:
        world.validation_status = "skipped"
    return world


def build_env(world: GeneratedWorld):
    """Create a live EnterpriseEnv from a validated GeneratedWorld.

    The environment is created but NOT reset.
    Call env.reset(world.spec.seed) for a deterministic episode.

    Returns:
        EnterpriseEnv (from enterprise_env.env)
    """
    from enterprise_env.env import EnterpriseEnv
    from enterprise_env.config import EnvConfig
    from .tasks.vendor_onboarding import GeneratedVendorOnboardingTask

    if world.spec.scenario != "vendor_onboarding":
        raise NotImplementedError(
            f"Generated env only supports 'vendor_onboarding'; got {world.spec.scenario!r}"
        )
    task = GeneratedVendorOnboardingTask(world)
    return EnterpriseEnv(task, EnvConfig(max_steps=task.max_steps))


def run_generated_episode(world: GeneratedWorld) -> dict[str, Any]:
    """Run the oracle scripted policy on the generated environment.

    Proves solvability: success_rate should be 1.0 on a valid world.
    Does NOT require Ollama.

    Returns:
        Episode result dict (mirrors run_episode() output):
        {task, seed, success, steps, reward, progress, trajectory, ...}
    """
    from enterprise_env.evaluation.diagnostics import classify_failures
    from .tasks.vendor_onboarding import GeneratedVendorOnboardingBaseline

    env = build_env(world)
    env.reset(seed=world.spec.seed)
    policy = GeneratedVendorOnboardingBaseline(world)

    total: float = 0.0
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
    repeated = 0
    seen: set = set()
    for x in trajectory:
        key = (x["agent"], x["app"], x["action"], repr(sorted(x["parameters"].items())))
        if key in seen:
            repeated += 1
        seen.add(key)

    result: dict[str, Any] = {
        "task":               "vendor_onboarding_gen",
        "seed":               world.spec.seed,
        "success":            done,
        "truncated":          trunc,
        "policy_error":       policy_error,
        "steps":              env.step_count,
        "reward":             total,
        "progress":           info.get("progress", env.verifier.progress(env.repo)),
        "invalid_actions":    invalid,
        "invalid_action_rate":invalid / max(1, env.step_count),
        "repeated_actions":   repeated,
        "trajectory":         trajectory,
        "world_fingerprint":  world.fingerprint,
    }
    result["failure_taxonomy"] = classify_failures(result)
    env.close()
    return result


__all__ = [
    "CompanySpec",
    "GeneratedWorld",
    "ValidationError",
    "generate_world",
    "build_env",
    "run_generated_episode",
    "build_manifest",
    "compute_fingerprint",
]
