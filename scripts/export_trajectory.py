#!/usr/bin/env python3
from __future__ import annotations
import argparse,html,json
from pathlib import Path
from enterprise_env.evaluation.runner import run_episode

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--task",choices=["customer_incident","product_launch","meeting_conflict","launch_readiness","budget_approval","vendor_onboarding"],default="customer_incident");ap.add_argument("--seed",type=int,default=42);ap.add_argument("--output",default="benchmark_results/trajectory.html");a=ap.parse_args()
    result=run_episode(a.task,seed=a.seed)
    rows=[]
    for x in result["trajectory"]:
        tool=f'{x["app"]}.{x["action"]}'
        rows.append(f'<tr><td>{x["step"]}</td><td>{html.escape(x["agent"])}</td><td>{html.escape(tool)}</td><td><pre>{html.escape(json.dumps(x["parameters"],sort_keys=True))}</pre></td><td>{html.escape(x["result"]["message"])}</td><td>{x["reward"]:.2f}</td><td>{x["progress"]:.0%}</td></tr>')
    doc=f'''<!doctype html><meta charset="utf-8"><title>Enterprise MARL trajectory</title><style>body{{font-family:Arial,sans-serif;margin:32px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:8px;vertical-align:top}}th{{background:#f4f4f4}}pre{{white-space:pre-wrap;margin:0}}.ok{{font-weight:bold}}</style><h1>Trajectory: {html.escape(a.task)}</h1><p class="ok">Success: {result["success"]} | Steps: {result["steps"]} | Reward: {result["reward"]:.2f} | Progress: {result["progress"]:.0%}</p><table><thead><tr><th>Step</th><th>Agent</th><th>Tool</th><th>Parameters</th><th>Result</th><th>Reward</th><th>Progress</th></tr></thead><tbody>{''.join(rows)}</tbody></table>'''
    p=Path(a.output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(doc,encoding="utf-8");print(f"Saved {p}")
if __name__=="__main__":main()
