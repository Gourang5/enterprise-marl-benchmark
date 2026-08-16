from enterprise_env.evaluation.runner import run_episode

def test_flagship_task():
    r=run_episode("customer_incident",seed=42)
    assert r["success"] and r["progress"]==1.0
    assert r["steps"]>=10
