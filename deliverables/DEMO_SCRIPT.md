# Demo Script — Enterprise MARL Benchmark v1.2 (4–6 min)

---

## Segment 1: Architecture (0:00–1:00)

**0:00** — Open terminal in the project root. Show structure briefly:
```
src/enterprise_env/   ← environment core
  tasks/              ← 6 task definitions with subgoal DAGs
  evaluation/         ← baselines, metrics, failure taxonomy
scripts/              ← benchmark runners
ui/                   ← Streamlit dashboard
benchmark_results/    ← pre-run JSON/CSV results
docs/                 ← policy design, factory, architecture
```

**0:20** — Run tests to confirm everything works:
```bash
python -m pytest tests/ -v
```
→ **70 passed, 0 failed.** Call out what is tested: task solvability, negation-hardened
verifiers, no free initial progress, permission enforcement, reward components,
info leakage prevention, evaluator/agent info separation.

**0:40** — Briefly describe the architecture:
"One SQLite company database → 5 thin app simulators → 5 heterogeneous agents
→ dependency-gated subgoal DAGs → deterministic state verifier.
An agent cannot succeed by saying 'task complete' — the DB state must match."

---

## Segment 2: Oracle Baseline (1:00–2:00)

**1:00** — Run the oracle baseline across all 6 tasks:
```bash
python scripts/run_benchmark.py --task all --episodes 10
```
→ 100% success rate on all 6 tasks. Explain:
"This confirms every task is mechanically solvable. It is the oracle upper bound
in our four-tier taxonomy: Random (0%) → Zero-Shot LLM (0%) → Hint-Guided (93%) → Oracle (100%)."

**1:30** — Show the pre-run baseline results:
```bash
python -m json.tool benchmark_results/baselines.json | head -30
```
→ 100% success, 0 invalid actions, 0 permission violations.

---

## Segment 3: Trajectory Viewer (2:00–2:45)

**2:00** — Export and view a trajectory:
```bash
python scripts/export_trajectory.py --task customer_incident --seed 42
```
Open `benchmark_results/customer_incident_trajectory.html` in a browser.

Walk through the episode:
- Step 1: cs_01 reads email from customer (Gmail)
- Step 2: cs_01 searches Jira for open incidents
- Step 3: eng_01 reads the Jira ticket (cross-agent coordination)
- Step 4: eng_01 posts engineering findings on the ticket
- Step 5: pm_01 resolves the issue and notifies Customer Success

Point out: reward components, subgoal unlock sequence, which agent acts each step,
how the verifier fires only when the correct agent posts the correct content to the correct record.

---

## Segment 4: ScenarioFactory (2:45–3:30)

**2:45** — Show the factory generating a different seed and difficulty:
```bash
python -c "
from enterprise_env.generation import ScenarioFactory
f = ScenarioFactory()
env, obs, info = f.build('vendor_onboarding', seed=99, difficulty='hard')
print('Difficulty:', info['difficulty'])
print('Distractors injected:', info['distractors'])
print('Subgoals:', len(env.task.subgoals()))
env.close()
"
```
→ Difficulty: hard, Distractors: 15, Subgoals: 8

**3:00** — Generate a dataset split:
```bash
python scripts/generate_dataset.py \
    --output generated_scenarios \
    --train 20 --dev 5 --test 10 \
    --difficulty hard
```
→ Produces `generated_scenarios/train.jsonl`, `dev.jsonl`, `test.jsonl`, `manifest.json`.
"Each scenario is validated at export time: zero initial progress, acyclic DAG,
all dependency IDs resolve. This is training data for RL or fine-tuning without
test contamination — seed-disjoint splits enforced by the factory."

---

## Segment 5: LLM Results (3:30–5:00)

**3:30** — Show hint-guided vs zero-shot comparison from pre-run results:
```bash
python scripts/compare_hint_vs_zeroshot.py
```
→ Show table. Narrate:
"Hint-guided (SOP-guided): 93% overall — validates task design and reward.
Zero-shot (qwen2.5:3b, no SOPs): 0% across all 6 tasks.
The gap is the open research question this benchmark establishes."

**4:00** — Optional live episode (requires Ollama):
```bash
python scripts/run_llm_benchmark.py \
    --provider ollama --model qwen2.5:3b \
    --task customer_incident --episodes 1
```

---

## Segment 6: Streamlit Dashboard (5:00–6:00, optional)

```bash
streamlit run ui/app.py
```
Navigate to http://localhost:8501 — task cards, four-tier policy taxonomy,
vendor_onboarding DAG visualization, failure analysis.

---

## Exact Commands That Work

```bash
# One-time setup
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\Activate.ps1       # Windows PowerShell
pip install -e ".[dev]"

# Verify (70 passed)
pytest -q

# Oracle baseline
python scripts/run_benchmark.py --task all --episodes 10

# Trajectory export
python scripts/export_trajectory.py --task customer_incident --seed 42

# ScenarioFactory demo
python scripts/generate_dataset.py --output generated_scenarios --train 20 --dev 5 --test 10

# Hint vs zero-shot comparison table
python scripts/compare_hint_vs_zeroshot.py

# Streamlit dashboard
streamlit run ui/app.py

# Live LLM episode (Ollama must be running)
python scripts/run_llm_benchmark.py --provider ollama --model qwen2.5:3b \
    --task customer_incident --episodes 1
```

---

## Key Talking Points

- **"70 tests, 0 flaky"** — every design decision is automatically verified
- **"Deterministic verification"** — DB state must match; cannot succeed by claiming success in text
- **"Negation-hardened verifier"** — 'NOT approved' fails; 'Approved. No further action.' passes
- **"Four-tier taxonomy"** — separates environment quality (oracle/hint) from model quality (zero-shot)
- **"0% zero-shot gap"** — establishes the open research problem for RL and fine-tuning
- **"Factory scales"** — seed-disjoint train/dev/test in one command
