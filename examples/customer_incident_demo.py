from enterprise_env.evaluation.runner import run_episode

r=run_episode("customer_incident",seed=42)
print(f"success={r['success']} steps={r['steps']} reward={r['reward']:.2f} progress={r['progress']:.0%}")
for x in r["trajectory"]:
    print(f"{x['step']:02d} {x['agent']:10s} {x['app']:8s}.{x['action']:16s} reward={x['reward']:6.2f} progress={x['progress']:.0%}")
