from enterprise_env.evaluation.runner import run_episode

def test_all_rule_baselines_solve():
    for task in ["customer_incident","product_launch","meeting_conflict","launch_readiness","budget_approval","vendor_onboarding"]:
        r=run_episode(task,seed=42)
        assert r["success"], (task,r)

def test_no_free_initial_progress():
    from enterprise_env.factory import make_env
    for task in ["customer_incident","product_launch","meeting_conflict","launch_readiness","budget_approval","vendor_onboarding"]:
        e=make_env(task);e.reset(42)
        assert e.verifier.progress(e.repo)==0.0
        e.close()

def test_repeated_read_is_penalized():
    from enterprise_env.factory import make_env
    from enterprise_env.core.actions import Action
    e=make_env("meeting_conflict");e.reset(42)
    e.step(Action("pm_01","calendar","read_calendar",{}))
    _,r,_,_,_=e.step(Action("pm_01","calendar","read_calendar",{}))
    assert r<0
    e.close()


def test_task_manifests_match_runtime_task_ids():
    from pathlib import Path
    import yaml
    from enterprise_env.tasks.factory import make_task
    root = Path(__file__).resolve().parents[1] / "tasks"
    for name in ("customer_incident", "product_launch", "meeting_conflict", "launch_readiness", "budget_approval", "vendor_onboarding"):
        manifest = yaml.safe_load((root / f"{name}.yaml").read_text())
        task = make_task(name)
        assert manifest["task_id"] == task.task_id
        assert manifest["horizon"] == task.max_steps
