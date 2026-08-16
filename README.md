# Enterprise Multi-Agent RL Benchmark — v1.3

A database-backed multi-agent RL environment where five heterogeneous agents coordinate
across five simulated enterprise applications to complete long-horizon workflows.

**Setting:** synthetic fictionalized company. All employees, messages, tickets, and data are synthetic.

---

## What Is This

Five AI agents with different roles and permissions must complete realistic enterprise workflows
together — like onboarding a vendor, resolving an incident, or approving a budget — across
Gmail, Slack, Jira, Calendar, and Sheets backed by a shared SQLite database.

**Key design decisions:**
- Agents cannot succeed by claiming "task complete" in text — the database state must match the verifier predicate
- Each agent sees only their own inbox, channels, calendar, and permitted sheets
- Subgoals are dependency-gated: later credit is blocked until prerequisites complete
- Verification is deterministic state-based, not LLM judge or string match

---

## Stack

| Layer | Choice | Why |
|---|---|---|
| Environment API | Gymnasium-compatible | Standard RL interface |
| Shared state | SQLite (in-memory, reset per seed) | Single source of truth across all apps |
| App simulators | 5 thin Python modules | Gmail, Slack, Jira, Calendar, Sheets |
| Verification | Deterministic predicate over DB | Reproducible, no LLM judge |
| Multi-agent adapter | Experimental PettingZoo AEC | Optional, not fully tested |
| LLM benchmark | Ollama / Gemini / Groq / Qwen / Anthropic | 5 providers, local and cloud |
| Dashboard | Streamlit | Debug and demo surface |
| Deployment | Docker Compose | Reproducible Ollama + benchmark |

---

## Agents

| Agent ID | Role | Apps | Sheet Access |
|---|---|---|---|
| pm_01 | Project Manager | Gmail, Slack, Jira, Calendar, Sheets | Owner (R/W) |
| eng_01 | Engineer | Slack, Jira, Calendar | Viewer |
| product_01 | Product Manager | Slack, Jira, Sheets | Editor |
| mgr_01 | Engineering Manager | Slack, Jira, Calendar | — |
| cs_01 | Customer Success | Gmail, Slack, Jira | — |

---

## Tasks

| # | Task | Subgoals | Steps | Apps | Key Research Property |
|---|---|---|---|---|---|
| 1 | Customer Incident | 7 | ~11 | Gmail, Jira, Slack, Calendar | Search/retrieval, entity correlation |
| 2 | Product Launch | 7 | ~8 | Slack, Jira, Calendar | Approval chain, multi-agent handoffs |
| 3 | Meeting Conflict | 5 | ~5 | Calendar, Slack | Constraint satisfaction, scheduling |
| 4 | Launch Readiness | 8 | ~17 | Gmail, Slack, Jira, Calendar, Sheets | Private info asymmetry, 5-app workflow |
| 5 | Budget Approval | 7 | ~8 | Jira, Sheets, Slack | Strict RBAC, approval chain |
| 6 | Vendor Onboarding | 8 | ~9 | Gmail, Slack, Jira, Calendar, Sheets | Parallel prerequisites, RBAC |

---

## RL & Evaluation Design

### Reward components
- `+subgoal_progress`: shaped credit when a new subgoal unlocks
- `+coordination_bonus`: cross-agent handoff required
- `+terminal_success`: episode completion
- `-redundant_action`: repeated read with no state change (anti-hacking)
- `-step_cost`: efficiency pressure
- `-timeout`: horizon enforcement

### Policy taxonomy

| Policy | Result | Notes |
|---|---|---|
| Random | 0/30 (5 ep/task) | Lower bound — confirms tasks are non-trivial |
| Zero-Shot LLM | 0/30 (5 ep/task) | qwen2.5:3b pilot — no hints, autonomous only |
| Hint-Guided LLM | 24/30 (5 ep/task) | SOP-guided debug baseline — not autonomous capability |
| Oracle | 30/30 (5 ep/task) | Deterministic scripted upper bound — proves solvability |

Zero-shot and hint-guided both use qwen2.5:3b via Ollama. Larger models expected to score higher.
Hint-guided result validates task and reward design, not LLM intelligence.

### Observation structure (per agent, role-filtered)
```python
obs = {
    "agent":    {employee_id, name, role, team_id},
    "inbox":    [email headers],     # body requires read_email
    "channels": [channel records],   # only channels agent belongs to
    "calendar": [event records],     # own calendar only
    "sheets":   [{sheet_id, role}],
    "task":     {id, name, instruction}
}
```

Evaluator state (`progress`, `subgoals`, `reward_components`) lives in `info["eval"]` — never exposed to the policy.

---

## Factory

### Factory V1 — ScenarioFactory (all 6 tasks, implemented)

Generates reproducible scenario variants across seed × difficulty × train/dev/test splits.

```bash
# Generate a dataset
python scripts/generate_dataset.py \
    --output generated_scenarios \
    --train 1000 --dev 200 --test 500 \
    --difficulty hard --seed 42
```

Difficulty presets: `easy` (2 distractors) / `medium` (6) / `hard` (15) / `adversarial` (30).
Splits are seed-disjoint — the model never sees a training seed at test time.

### Factory V2 — Generated Worlds (vendor_onboarding vertical slice, prototype)

Adds entity-level world generation: different employee names, emails, vendor names, and ticket IDs per seed.
A policy trained across seeds cannot memorize ticket IDs — it must learn the workflow.

```bash
# Seed 42: Smart Metrics, METR-401/402/403, sha256:841edac7c2667c37
python scripts/generate_environment.py --seed 42 --run-oracle

# Seed 43: Stellar Services, SERV-401/402/403, sha256:cbebc420d7920829
python scripts/generate_environment.py --seed 43 --run-oracle
```

Factory V2 validates the generative architecture on vendor onboarding as a vertical slice.
The same `TaskSpec → world generation → validation` pipeline is designed to extend across
task families. Productionization would expand generators and automated QA coverage rather
than require a new core architecture.

**Status:** proof-of-concept on 1 of 6 tasks. ScenarioFactory covers all 6 for seed/difficulty variation.

---

## Installation

Python 3.10+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\Activate.ps1       # Windows PowerShell

pip install -e ".[dev]"
pytest -q                          # 118 passed
```

Optional extras:
```bash
pip install -e ".[rl]"    # PettingZoo AEC adapter (experimental)
pip install -e ".[ui]"    # Streamlit dashboard
```

---

## Quick Demo

```bash
# Oracle — 100% all 6 tasks
python scripts/run_benchmark.py --task all --episodes 5

# Trajectory HTML viewer
python scripts/export_trajectory.py --task vendor_onboarding --seed 42
start benchmark_results/vendor_onboarding_trajectory.html   # Windows
# open ...html   # macOS

# Factory V2 generated world
python scripts/generate_environment.py --seed 42 --run-oracle
python scripts/generate_environment.py --seed 43 --run-oracle

# Hint vs zero-shot comparison
python scripts/compare_hint_vs_zeroshot.py

# Streamlit dashboard
streamlit run ui/app.py
```

---

## Tests

```bash
pytest -q    # 118 passed, 0 failed, 0 flaky
```

- 70 core environment tests: task solvability, permission enforcement, negation-hardened verifiers,
  evaluator/agent info separation, reward components
- 48 factory_v2 tests: determinism, diversity, fingerprint, validator, oracle solvability (5 seeds),
  cross-app propagation, legacy regression

---

## LLM Benchmark

Five providers supported (three free, no credit card):

```bash
# Ollama (local, no key)
python scripts/run_llm_benchmark.py --provider ollama --model qwen2.5:3b --task all --episodes 5

# Gemini (free — recommended for Windows, fastest)
$env:GEMINI_API_KEY="AIza..."
python scripts/run_llm_benchmark.py --provider gemini --task all --episodes 5

# Groq (free, fast)
$env:GROQ_API_KEY="gsk_..."
python scripts/run_llm_benchmark.py --provider groq --task all --episodes 5

# Zero-shot (no hints)
python scripts/run_llm_benchmark.py --provider ollama --no-hints --task all --episodes 5
```

See `RUN_WINDOWS_FREE_LLM.md` for the Windows step-by-step guide.

---

## Limitations

- Turn-based sequential execution — true parallel MARL requires an action encoder on top
- PettingZoo AEC adapter is experimental, not fully tested with standard MARL libraries
- Entity IDs fixed per task family — splits are seed-disjoint but not entity-disjoint (Factory V1)
- Zero-shot evaluated on qwen2.5:3b only — result is model-dependent, not a ceiling
- Factory V2 entity-level generation implemented for vendor_onboarding only (prototype)
- No Figma, GitHub, HRMS, or finance system simulators in this version

---

## Submission Assets

| Asset | Location |
|---|---|
| Slide deck content | `deliverables/PRESENTATION_CONTENT.md` |
| Demo script | `deliverables/DEMO_SCRIPT.md` |
| Development prompt trace | `deliverables/development_prompt_trace.md` |
| Pre-run benchmark results | `benchmark_results/` |
| RL interface reference | `docs/rl_interface.md` |

---

## Docker (Reproducible Ollama Run)

```bash
cp .env.example .env
docker compose up --build --abort-on-container-exit benchmark
```

Compose starts Ollama, waits for health, pulls the configured model, and runs the benchmark.
Results are written to `benchmark_results/` on the host.

---

## Design Principles

1. One source of truth across all apps (SQLite)
2. Thin app simulators — not SaaS clones
3. Partial, asymmetric per-agent observations
4. Search and discovery before direct mutation
5. Heterogeneous permissions enforced at every action
6. Dependency-rich tasks with valid action interleavings
7. State-based deterministic verification
8. Reward progress and outcome, not clicks
9. Seeded reproducibility with inspectable traces
10. Research instrument first — UI is a debug surface
