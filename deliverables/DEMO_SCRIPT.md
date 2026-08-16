# Demo Script — Enterprise MARL Benchmark v1.2 (6–8 min)

---

## Segment 1: Setup & Architecture (0:00–1:00)

**0:00** — Open repo in terminal. Show top-level structure:
```
src/enterprise_env/   ← environment core
tasks/                ← YAML task manifests
scripts/              ← benchmark runners
ui/                   ← Streamlit dashboard
benchmark_results/    ← pre-run results
docs/policy_design.md ← academic justification
```

**0:20** — Run tests:
```bash
python -m pytest tests/ -v
```
→ 34 passed, 0 failed. Call out what's tested: task solvability, no free initial progress, permissions, reward, DB.

**0:40** — Briefly show the architecture diagram from README:
"One SQLite company → 5 apps as controlled interfaces → 5 heterogeneous agents →
dependency-gated subgoal DAGs → deterministic state verifier"

---

## Segment 2: Oracle Baseline + Trajectory (1:00–2:30)

**1:00** — Run oracle baseline across all 6 tasks:
```bash
python scripts/run_benchmark.py --task all
```
→ 100% success on all tasks. Explain: "This proves every task is mechanically solvable.
It's the oracle upper bound in our four-tier policy taxonomy."

**1:30** — Export and open the trajectory viewer:
```bash
python scripts/export_trajectory.py --task customer_incident --seed 42
```
Open `benchmark_results/customer_incident_trajectory.html`.

Walk through one episode step by step:
- Step 1: cs_01 reads email from customer
- Step 2: cs_01 searches Jira for open incidents
- Step 3: eng_01 reads the Jira ticket (cross-agent coordination)
- Step 4: eng_01 posts engineering findings
- Step 5: pm_01 posts resolution to Slack
→ Point out reward components, subgoal unlock sequence, agent turns

---

## Segment 3: Streamlit Dashboard (2:30–3:30)

**2:30** — Launch the UI:
```bash
streamlit run ui/app.py
```
Navigate to http://localhost:8501

- Show task cards (6 tasks, difficulty, subgoal count)
- Show the four-tier policy taxonomy section with color-coded cards
- Show the vendor_onboarding parallel DAG visualization
- Click through task details, show agent/app table

---

## Segment 4: LLM Benchmark — Hint-Guided vs Zero-Shot (3:30–6:00)

**3:30** — Explain the research question:
"We have two evaluation modes. Hint-guided is like an onboarded employee with SOPs.
Zero-shot is truly autonomous — the model must reason from scratch."

**3:45** — Run hint-guided episode (already done, show from llm_results_5ep.json):
```bash
cat benchmark_results/llm_results_5ep.json | python -m json.tool | head -50
```
OR show the summary: "93% overall success rate — 4/6 tasks at 100%"

**4:15** — Run zero-shot comparison for one task (live or from pre-run results):
```bash
python scripts/run_llm_benchmark.py --provider ollama --model qwen2.5:3b \
    --task customer_incident --episodes 1 --no-hints
```
→ Show it fail (policy error, missing parameters, loops) OR show low success rate

**5:00** — Run the comparison script:
```bash
python scripts/compare_hint_vs_zeroshot.py
```
→ Show the table. Narrate: "The ~90-100pp gap proves that workflow knowledge —
what companies encode in SOPs and runbooks — is the critical missing piece for
autonomous enterprise agents. This is exactly what RAG systems attempt to inject."

---

## Segment 5: Difficulty Benchmark + Factory (6:00–7:30)

**6:00** — Show difficulty results:
```bash
cat benchmark_results/difficulty_results.json | python -m json.tool
```
→ Oracle: 100% at all 4 levels. Random: 0% at all levels.
"Distractor injection doesn't fool the oracle — it has perfect information.
But it will challenge learned agents trained without that immunity."

**6:30** — Briefly show ScenarioFactory:
```python
# generation.py — show ScenarioFactory.build()
```
"4 difficulty tiers × 6 tasks × N seeds = a full dataset for training & evaluation.
The train/dev/test split prevents benchmark contamination."

**7:00** — Show docs/policy_design.md — the academic justification:
"We deliberately separate two research questions:
 1. Is the task well-designed? → hint-guided answers this (100% → yes)
 2. Can LLMs generalize autonomously? → zero-shot answers this (low → future work)
The next step is behavioral cloning or PPO on top of this environment."

---

## Segment 6: Docker (Optional, if time permits)

```bash
docker compose up
```
→ Ollama + model bootstrap + benchmark + Streamlit UI — one command deployment.

---

## Key Talking Points

- "70 tests pass — every design decision is verified, including negation-hardening"
- "Not a toy: 5 apps, 5 agents, 6 tasks, 40 subgoals total, realistic permissions"
- "The four-tier taxonomy is the contribution: not just 'does LLM solve it?' but 'why or why not?'"
- "The gap between zero-shot and hint-guided is the research question for the next year"
- "Infrastructure is ready for PPO, QMIX, BC without any changes to the environment"
