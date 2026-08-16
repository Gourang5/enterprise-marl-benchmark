# 4-minute demo script

1. **0:00-0:30 — Problem and architecture.** Open the README architecture diagram. Explain that the apps are thin simulators over one shared company state.
2. **0:30-1:00 — Show the fixture.** Run `python scripts/inspect_company.py`. Point out consistent employee IDs and role permissions.
3. **1:00-2:10 — Run the incident.** Run `python examples/customer_incident_demo.py`. Emphasize search/discovery, cross-agent handoff, Jira state changes, Calendar coordination, and final notification.
4. **2:10-2:45 — Inspect trajectory.** Run `python scripts/export_trajectory.py --task customer_incident --seed 42`, then open `benchmark_results/customer_incident_trajectory.html`. Show reward components and subgoal progression.
5. **2:45-3:20 — Evaluation.** Run `python scripts/compare_baselines.py --episodes 25`. Show rule baseline 100% and random baseline 0% on the validated seeds.
6. **3:20-3:45 — LLM harness.** Show `scripts/run_llm_benchmark.py`; explain centralized vs decentralized control and provider-neutral action JSON.
7. **3:45-4:00 — Factory.** Show `generation.py` and explain seeded noise, DAG validation, reproducibility, and the path to mass-producing task variants.
