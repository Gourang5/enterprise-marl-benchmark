# DEMO_SCRIPT.md — Enterprise MARL Benchmark
## 3–5 Minute Video Script | All commands verified | No internet required

---

### Before Recording
- Activate venv: `.venv\Scripts\Activate.ps1` (Windows) or `source .venv/bin/activate`
- Terminal open at project root
- Browser closed (clean start for Streamlit)

---

## SEGMENT 1 — Project Intro (0:00–0:30)

> "This is an enterprise multi-agent RL benchmark. Five AI agents with different roles
> coordinate across Gmail, Slack, Jira, Calendar, and Sheets to complete realistic
> long-horizon workflows — like vendor onboarding or incident resolution.
>
> The core idea: an agent cannot succeed by saying 'task complete' in Slack.
> The underlying SQLite database state has to match the verifier predicate.
> That's what makes this a proper research benchmark, not a demo."

---

## SEGMENT 2 — Tests (0:30–0:50)

```bash
pytest -q
```

> "118 tests, zero failures. These cover task solvability, permission enforcement,
> negation-hardened verifiers — where 'NOT approved' correctly fails but
> 'Approved. No further action.' correctly passes — evaluator/agent state separation,
> and 48 factory_v2 tests covering determinism, diversity, and oracle solvability."

---

## SEGMENT 3 — Oracle Baseline (0:50–1:20)

```bash
python scripts/run_benchmark.py --task all --episodes 5
```

> "Oracle baseline — deterministic scripted policy — 100% on all six tasks,
> five episodes each. This is the ceiling. It proves every task is mechanically solvable.
> The step counts vary: meeting_conflict resolves in 5 steps, launch_readiness needs 17.
> That's intentional — different tasks have different coordination complexity."

---

## SEGMENT 4 — Cross-App Trajectory (1:20–3:00)

```bash
python scripts/export_trajectory.py --task vendor_onboarding --seed 42
start benchmark_results/vendor_onboarding_trajectory.html
```

> "Vendor onboarding — the most complex task. Walk through each step:
>
> Step 1: pm_01 reads the vendor request email from Gmail. There are distractor emails —
> they have to search, not just open the first one.
>
> Steps 2–3: pm_01 searches Jira for the procurement ticket. No direct lookup — search required.
>
> Steps 4–5: product_01 clears the legal ticket, eng_01 confirms IT provisioning — these run
> in parallel. The next step, manager approval, is blocked until BOTH complete.
>
> Step 6: mgr_01 approves. But only because pm_01 already found the ticket.
>
> Step 7: pm_01 updates the vendor tracker sheet to ACTIVE. Only pm_01 has write access —
> any other agent gets a permission error. The verifier checks not just what was written
> but who wrote it.
>
> Steps 8–9: schedule kickoff, announce in Slack. Nine steps, five apps, four roles,
> parallel branches — verified against database state at each subgoal."

---

## SEGMENT 5 — Factory V1: ScenarioFactory (3:00–3:40)

```bash
python scripts/generate_dataset.py --output generated_scenarios --train 20 --dev 5 --test 10 --difficulty hard
python -m json.tool generated_scenarios/manifest.json
```

> "ScenarioFactory generates reproducible datasets for all six tasks. Hard difficulty
> injects 15 realistic near-miss distractors. Seeds are disjoint across train, dev,
> and test — the model never sees a training seed at test time.
> Each scenario is validated before export: zero initial progress, acyclic DAG,
> all dependency IDs resolve."

---

## SEGMENT 6 — Factory V2: Generated Worlds (3:40–4:20)

```bash
python scripts/generate_environment.py --seed 42 --run-oracle
```

> "Factory V2 goes one layer deeper — entity-level world generation.
> Seed 42 gives Smart Metrics, tickets METR-401 through 403, unique employees.
> The SHA-256 fingerprint identifies this exact world configuration."

```bash
python scripts/generate_environment.py --seed 43 --run-oracle
```

> "Seed 43 — completely different vendor, different employees, different tickets.
> Same DAG structure, different operational context. Oracle passes on both —
> every generated world is verified solvable at generation time.
>
> This is a vertical slice proof-of-concept on vendor onboarding.
> The same TaskSpec → generation → validation pipeline is designed to extend
> across task families in production."

---

## SEGMENT 7 — Closing: The Research Gap (4:20–4:50)

```bash
python scripts/compare_hint_vs_zeroshot.py
```

> "The core finding: hint-guided LLM achieves 80% — 24 out of 30 episodes — with
> full workflow instructions in context. Zero-shot LLM, operating autonomously with
> only the task description: 0 out of 30 episodes across all six tasks.
>
> That 80-point gap is the open research question. Can RL or fine-tuning close it?
> This benchmark is built to study exactly that."

---

## Full Command Sequence — Copy-Paste Ready

```bash
pytest -q
```
```bash
python scripts/run_benchmark.py --task all --episodes 5
```
```bash
python scripts/export_trajectory.py --task vendor_onboarding --seed 42
```
```bash
start benchmark_results/vendor_onboarding_trajectory.html
```
```bash
python scripts/generate_dataset.py --output generated_scenarios --train 20 --dev 5 --test 10 --difficulty hard
```
```bash
python -m json.tool generated_scenarios/manifest.json
```
```bash
python scripts/generate_environment.py --seed 42 --run-oracle
```
```bash
python scripts/generate_environment.py --seed 43 --run-oracle
```
```bash
python scripts/compare_hint_vs_zeroshot.py
```
```bash
streamlit run ui/app.py
```
