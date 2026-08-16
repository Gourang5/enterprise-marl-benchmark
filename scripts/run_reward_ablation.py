#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from enterprise_env.config import EnvConfig,RewardConfig
from enterprise_env.env import EnterpriseEnv
from enterprise_env.tasks.factory import make_task
from enterprise_env.evaluation.baseline import make_baseline
from enterprise_env.evaluation.metrics import aggregate

TASKS=["customer_incident","product_launch","meeting_conflict"]

def run(task,seed,reward):
    t=make_task(task);env=EnterpriseEnv(t,EnvConfig(max_steps=t.max_steps,reward=reward));env.reset(seed);p=make_baseline(task);total=0.0;done=trunc=False;info={}
    while not done and not trunc:
        a=p.action(env);_,r,done,trunc,info=env.step(a);total+=r
    out={"task":task,"seed":seed,"success":done,"truncated":trunc,"steps":env.step_count,"reward":total,"progress":info.get("progress",0.0),"invalid_action_rate":0.0,"repeated_actions":0}
    env.close();return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--episodes",type=int,default=20);ap.add_argument("--seed",type=int,default=100);ap.add_argument("--output",default="benchmark_results/reward_ablation.json");a=ap.parse_args()
    shaped=RewardConfig();sparse=RewardConfig(valid_action=0.0,progress_per_full_subgoal=0.0,coordination_bonus=0.0,redundant_action=-0.1,step_cost=-0.01,terminal_success=100.0,invalid_action=-4.0,timeout=-15.0)
    report={}
    for task in TASKS:
        report[task]={}
        for name,cfg in [("shaped",shaped),("sparse",sparse)]:
            xs=[run(task,a.seed+i,cfg) for i in range(a.episodes)];report[task][name]=aggregate(xs)
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding="utf-8");print(json.dumps(report,indent=2));print(f"Saved {path}")
if __name__=="__main__":main()
