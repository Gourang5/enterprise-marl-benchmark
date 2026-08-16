#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from enterprise_env.evaluation.runner import run_episode, run_random_episode
from enterprise_env.evaluation.metrics import aggregate

TASKS=["customer_incident","product_launch","meeting_conflict","launch_readiness","budget_approval","vendor_onboarding"]

def main():
    p=argparse.ArgumentParser(description="Compare deterministic rule and random baselines on paired seeds.")
    p.add_argument("--episodes",type=int,default=50)
    p.add_argument("--seed",type=int,default=100)
    p.add_argument("--output",default="benchmark_results/baselines.json")
    a=p.parse_args(); report={}
    for task in TASKS:
        rule=[run_episode(task,seed=a.seed+i) for i in range(a.episodes)]
        random=[run_random_episode(task,seed=a.seed+i) for i in range(a.episodes)]
        report[task]={"rule":aggregate(rule),"random":aggregate(random)}
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2));print(f"Saved {out}")
if __name__=="__main__":main()
