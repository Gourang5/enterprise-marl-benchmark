import argparse
from enterprise_env.evaluation.runner import run_episode
from enterprise_env.evaluation.metrics import aggregate

ALL_TASKS = ["customer_incident", "product_launch", "meeting_conflict", "launch_readiness", "budget_approval", "vendor_onboarding"]

p = argparse.ArgumentParser()
p.add_argument("--task", default="all", choices=["all", *ALL_TASKS])
p.add_argument("--episodes", type=int, default=10)
a = p.parse_args()
tasks = ALL_TASKS if a.task == "all" else [a.task]
for task in tasks:
    rs = [run_episode(task, seed=42 + i) for i in range(a.episodes)]
    print(task, aggregate(rs))
