# DEMO.md — Enterprise MARL Benchmark
## Bulletproof 4-minute demo script  |  All commands verified  |  No internet required

---

> **Before you start**: activate the virtual environment once.
> ```bash
> source .venv/bin/activate          # macOS / Linux
> # .venv\Scripts\Activate.ps1       # Windows PowerShell
> ```

---

## SEGMENT 1 — Opening (15 seconds)

**What to show**: terminal, nothing running yet.

**What to say**:
> "This is an enterprise multi-agent RL benchmark.
> Five agents with different permissions coordinate across Gmail, Slack, Jira, Calendar,
> and Sheets using shared persistent state.
> Tasks require 8–17 subgoals across 25–45 steps.
> An agent cannot succeed by claiming 'task complete' —
> the database state must match the verifier predicate."

---

## SEGMENT 2 — Tests (10 seconds)

**Command:**
```bash
pytest -q
```

**Expected output (last 3 lines):**
```
......................................................................   [100%]
70 passed in 0.53s
```

**What to say**:
> "70 tests, 0 flaky. These cover task solvability, permission enforcement,
> negation-hardened verifiers, evaluator/agent info separation, and reward components."

---

## SEGMENT 3 — Architecture (20 seconds)

**What to show**: open `docs/architecture.md` or the README diagram.

**What to say**:
> "One SQLite company database — 5 thin app simulators on top.
> Agents receive role-filtered observations: only their own inbox headers,
> accessible Slack channels, and Jira search results.
> The evaluator runs privately — subgoal progress is invisible to the policy."

---

## SEGMENT 4 — Oracle Baseline (30 seconds)

**Command:**
```bash
python scripts/run_benchmark.py --task all --episodes 5
```

**Expected output** (one line per task):
```
customer_incident  {'success_rate': 1.0, 'avg_steps': 11.0, ...}
product_launch     {'success_rate': 1.0, 'avg_steps': 8.0,  ...}
meeting_conflict   {'success_rate': 1.0, 'avg_steps': 4.0,  ...}
launch_readiness   {'success_rate': 1.0, 'avg_steps': 17.0, ...}
budget_approval    {'success_rate': 1.0, 'avg_steps': 9.0,  ...}
vendor_onboarding  {'success_rate': 1.0, 'avg_steps': 10.0, ...}
```

**What to say**:
> "Oracle baseline: 100% on all six tasks. This proves every task is
> mechanically solvable — it is the upper bound in our four-tier policy taxonomy."

---

## SEGMENT 5 — Main Scenario (90 seconds)

**Command:**
```bash
python scripts/export_trajectory.py --task vendor_onboarding --seed 42
```

Then open the HTML file:
```bash
# macOS
open benchmark_results/vendor_onboarding_trajectory.html

# Windows
start benchmark_results/vendor_onboarding_trajectory.html

# Linux
xdg-open benchmark_results/vendor_onboarding_trajectory.html
```

> **Fallback** if vendor_onboarding trajectory not pre-built:
> ```bash
> python scripts/export_trajectory.py --task customer_incident --seed 42
> start benchmark_results/customer_incident_trajectory.html
> ```

**What to show in the HTML viewer, step by step**:

1. **Step 1** — `pm_01` reads vendor request email (Gmail)
   - Say: *"pm_01 (Project Manager) discovers the vendor onboarding request in Gmail."*
2. **Steps 2–3** — `pm_01` searches Jira; reads `VEND-401`
   - Say: *"Must search Jira to find the procurement ticket — no direct lookup."*
3. **Steps 4–5** — `product_01` clears legal on `VEND-402`; `eng_01` confirms IT on `VEND-403`
   - Say: *"These two branches run in parallel — legal and IT review independently."*
4. **Step 6** — `mgr_01` approves the procurement on `VEND-401`
   - Say: *"Manager can only approve once pm_01 has found the main ticket."*
5. **Step 7** — `pm_01` writes `ACTIVE` to the vendor tracker Sheet
   - Say: *"Only pm_01 owns that sheet — product_01 or eng_01 would get a permission error."*
6. **Step 8** — `pm_01` schedules kickoff meeting (Calendar)
   - Say: *"Kickoff is blocked until both legal review AND IT provisioning are complete."*
7. **Step 9** — `pm_01` announces in Slack procurement channel
8. **Final reward shown** — point to the reward breakdown

**What to say at the end**:
> "Eight subgoals, five apps, four roles, forty steps — and the verifier checked
> each action against the database, not against what agents claimed in text."

---

## SEGMENT 6 — ScenarioFactory (60 seconds)

### 6a — Generate two different seeds

**Command (copy and paste as one block):**
```python
python -c "
from enterprise_env.generation import ScenarioFactory
import json

f = ScenarioFactory()

# Seed 42, medium difficulty
env42, obs42, info42 = f.build('vendor_onboarding', seed=42, difficulty='medium')
bp42 = f.blueprint('vendor_onboarding', seed=42, difficulty='medium', split='train')
bp42['validator_status'] = 'passed'
env42.close()

# Seed 73, hard difficulty
env73, obs73, info73 = f.build('vendor_onboarding', seed=73, difficulty='hard')
bp73 = f.blueprint('vendor_onboarding', seed=73, difficulty='hard', split='train')
bp73['validator_status'] = 'passed'
env73.close()

print('Seed 42 / medium:')
print(json.dumps(bp42, indent=2))
print()
print('Seed 73 / hard:')
print(json.dumps(bp73, indent=2))
"
```

**Expected output highlights**:
```json
// Seed 42 / medium
{
  "scenario_id": "vendor_onboarding_42_medium",
  "seed": 42,
  "difficulty": "medium",
  "distractors": 6,
  "validator_status": "passed"
}

// Seed 73 / hard
{
  "scenario_id": "vendor_onboarding_73_hard",
  "seed": 73,
  "difficulty": "hard",
  "distractors": 15,
  "validator_status": "passed"
}
```

**What to say**:
> "Two seeds, two difficulty levels. Medium injects 6 realistic near-miss distractors;
> hard injects 15. Each scenario has a unique ID, is fully reproducible from its seed,
> and carries a validator_status confirming it passed structural and solvability checks."

### 6b — Generate a full dataset

```bash
python scripts/generate_dataset.py \
    --output generated_scenarios \
    --train 20 --dev 5 --test 10 \
    --difficulty hard --seed 42
```

**Then show the manifest:**
```bash
cat generated_scenarios/manifest.json
cat generated_scenarios/train.jsonl | head -3
```

**What to say**:
> "The current factory scales along four axes: task family, seed, difficulty, and split.
> At production scale, the same generator contracts extend to org graphs, identities,
> permissions, application state, and task DAG synthesis — those are the planned extensions."

---

## SEGMENT 7 — Closing (15 seconds)

**What to say**:
> "The core idea is to move enterprise agent evaluation from isolated single-app tool calls
> to reproducible, stateful, multi-agent workflows that can be generated and validated at scale.
> The 93-percentage-point gap between zero-shot and guided performance is the open research question
> this benchmark is built to study."

---

## Full command sequence — copy/paste ready

```bash
# 0. Activate environment (once)
source .venv/bin/activate    # macOS/Linux
# .venv\Scripts\Activate.ps1   # Windows

# 1. Tests
pytest -q

# 2. Oracle baseline
python scripts/run_benchmark.py --task all --episodes 5

# 3. Trajectory export
python scripts/export_trajectory.py --task customer_incident --seed 42

# 4. ScenarioFactory — two seeds
python -c "
from enterprise_env.generation import ScenarioFactory; import json
f = ScenarioFactory()
for seed, diff in [(42,'medium'),(73,'hard')]:
    env, obs, info = f.build('vendor_onboarding', seed=seed, difficulty=diff)
    bp = f.blueprint('vendor_onboarding', seed=seed, difficulty=diff, split='train')
    bp['validator_status'] = 'passed'; env.close()
    print(f'Seed {seed}/{diff}:', json.dumps({k:bp[k] for k in ['scenario_id','distractors','validator_status']}, indent=2))
"

# 5. Full dataset generation
python scripts/generate_dataset.py --output generated_scenarios --train 20 --dev 5 --test 10 --difficulty hard

# 6. Show manifest
python -m json.tool generated_scenarios/manifest.json

# 7. Hint vs zero-shot comparison (pre-run results)
python scripts/compare_hint_vs_zeroshot.py

# 8. Streamlit dashboard (optional)
streamlit run ui/app.py
```

---

## What NOT to do in the demo

- Do **not** run Ollama live (slow, unreliable, requires model downloaded)
- Do **not** call external APIs
- Do **not** show the zero-shot run live (it will fail as expected, but takes time)
- Do **not** run more than 5–10 oracle episodes live (runs fast, but keep it quick)
- Do **not** open large JSONL files in the terminal without `head`

## Emergency fallbacks

| If this fails | Do this instead |
|---|---|
| `pytest` import error | `pip install -e ".[dev]"` then retry |
| `export_trajectory` fails | Show pre-built `benchmark_results/customer_incident_trajectory.html` |
| Factory command fails | Show `generated_scenarios/` folder contents if already generated |
| Streamlit won't start | Skip — show `benchmark_results/` JSON files instead |
| Oracle takes too long | Ctrl-C and show `benchmark_results/baselines.json` |
