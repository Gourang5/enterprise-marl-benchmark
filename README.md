# Enterprise Multi-Agent RL Environment — Final Submission v1.2 (Factory + Sheets Edition)

A database-first, multi-agent enterprise RL benchmark for long-horizon workflows across simulated Gmail, Slack, Jira, Calendar and Sheets.

**Setting:** a fictionalized synthetic instance inspired by **Walmart Global Tech**. All employees, messages, incidents, customers and project data are synthetic and do not represent real Walmart information.

## Why this version is stronger

- One shared SQLite company world and consistent identities across every app.
- Agent observations do **not** expose hidden verifier/subgoal state or the full Jira database.
- Search-first information discovery in Gmail, Slack and Jira.
- Real dependency-gated subgoal DAGs: later credit is unavailable until prerequisites are achieved.
- Six distinct research tasks with different failure modes, including multiple five-app cross-team workflows.
- Actor-selected/event-driven multi-agent turns instead of mandatory five-person round-robin filler actions.
- Role-based permissions and heterogeneous capabilities.
- Reward anti-hacking: successful no-op/repeated reads are penalized rather than rewarded.
- Deterministic state-based verification with zero free progress at reset.
- Rule-based baselines for **all six tasks**.
- Factory validation hook for task DAGs and initial solvability invariants.
- Seed-dependent distractor variation so benchmark seeds produce different observable scenarios.
- Strict action-parameter validation: malformed LLM actions become invalid transitions instead of crashing the episode.
- Wilson 95% confidence intervals for success-rate reporting.
- Reward ablation runner, HTML trajectory exporter, optional Streamlit viewer, and optional PettingZoo AEC adapter.
- Episode trajectory logging and benchmark summaries.

## Tasks

### 1. P0 Partner Authentication Incident
A project manager must discover a customer report among distractor email, correlate it to the correct Jira incident among distractor issues, assign and notify engineering, have the engineer record investigation and move the issue in progress, schedule a review, resolve the issue, and notify Customer Success.

Research properties: search/retrieval, entity correlation, cross-app state, role delegation, delayed credit, dependency depth, distractors.

### 2. Checkout Launch Go/No-Go
Product must inspect launch readiness, assign engineering, obtain an engineering validation, obtain manager approval, coordinate the go/no-go state in Slack, schedule a review, and close the launch ticket.

Research properties: heterogeneous roles, approval chain, multi-agent handoffs, dependency graph, cross-app coordination.

### 3. Priority Meeting Conflict
A customer meeting is immovable, an engineering review conflicts with it, and Arjun has another blocked hour. Agents must inspect both calendars, infer the earliest feasible slot, reschedule, and notify participants.

Research properties: constraint satisfaction, distributed observations, scheduling, objective mathematical verification.

### 4. Cross-Team Launch Readiness
Customer Success must discover a private partner commitment, hand it to Product, Engineering must inspect and document a Jira blocker, Product must capture evidence in the readiness sheet, Engineering Management must approve, and Product must record approval, schedule the review and announce readiness.

Research properties: private information, cross-agent dependency, permission asymmetry, five-app workflow, evidence grounding, approval chain.

### 5. Budget Approval
Engineering estimates a project cost on a Jira ticket, a manager approves it, and the approval must be recorded in the budget tracker sheet (only the product manager may write the sheet) and announced in the engineering Slack channel.

Research properties: strict RBAC enforcement, multi-step approval chain, sheet-write permission boundary, cross-app coordination.

### 6. Vendor Onboarding
A new vendor (TechNova Solutions) must be onboarded: Legal must clear the contract ticket, IT must confirm provisioning, the Engineering Manager must approve procurement, the vendor tracker sheet must be updated to ACTIVE (only pm_01 may write), a kickoff meeting must be scheduled, and completion announced in the procurement channel.

Research properties: parallel prerequisite subgoals, strict RBAC on sheet writes, multi-agent role separation, five-app workflow.

## Architecture

```text
Policy / multi-agent controller
        |
        v
EnterpriseEnv
        |
        +--> filtered agent observation
        +--> semantic tool action
        |
        v
Gmail / Slack / Jira / Calendar / Sheets simulators
        |
        v
Repository / service layer
        |
        v
SQLite shared company state
        |
        +--> private deterministic verifier
        +--> reward engine
        +--> audit / trajectory log
```

The evaluator state and agent observation are deliberately separated. Evaluator-only keys (`progress`, `subgoals`, `reward_components`) are nested under `info["eval"]` — invisible to RL policies. The agent-facing `info` contains only `success`, `message`, and `step`. Agent observations contain only identity, inbox headers, accessible channels, calendar, and the high-level task instruction.

## Install and run

Python 3.10+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate         # Windows PowerShell/CMD equivalent
python -m pip install --upgrade pip
pip install -e '.[dev]'
pytest -q
python examples/customer_incident_demo.py
python scripts/run_benchmark.py --task all --episodes 10
```

Optional RL packages:

```bash
pip install -e '.[rl,dev]'
```

## Useful commands

Run one benchmark:

```bash
python scripts/run_benchmark.py --task customer_incident --episodes 100
python scripts/run_benchmark.py --task product_launch --episodes 100
python scripts/run_benchmark.py --task meeting_conflict --episodes 100
python scripts/run_benchmark.py --task launch_readiness --episodes 100
python scripts/run_benchmark.py --task budget_approval --episodes 100
python scripts/run_benchmark.py --task vendor_onboarding --episodes 100
```

Inspect the seeded company:

```bash
python scripts/inspect_company.py
```


## New research infrastructure in v1.2

- `SheetsApp`: spreadsheet access and mutation with membership roles.
- `launch_readiness`: a genuinely cross-agent five-app task.
- `ScenarioFactory`: easy/medium/hard/adversarial generation plus disjoint train/dev/test manifests.
- `scripts/replay_episode.py`: deterministic trajectory replay.
- failure taxonomy: looping, retrieval, permission, constraint, tool, policy and horizon failures.
- sample generated split manifests under `generated_scenarios/`.

See `docs/NEW_UPGRADES.md`, `docs/factory.md`, and `docs/replay_and_failures.md`.

## Reward design

The reward is based on task progress and useful state changes, not on app usage:

```text
reward = useful_action_or_redundancy
       + newly_unlocked_subgoal_progress
       + useful_coordination_bonus
       + terminal_success
       + step_cost
       + invalid/timeout penalties
```

A successful action with no state/progress change receives the redundant-action penalty. This blocks reward farming from repeated reads.

## Factory path

`ScenarioFactory` now implements reproducible scenario blueprints, difficulty presets, deterministic distractor injection, and train/dev/test manifest generation. It validates that generated/reset scenarios:

- start at zero progress,
- reference only valid dependency nodes,
- contain an acyclic subgoal graph.

Generate sample splits with `python scripts/generate_dataset.py --output generated_scenarios --train 100 --dev 20 --test 50 --difficulty hard`.

**Scope note:** The current factory generates reproducible scenario variants across distractor density and seed. Entity IDs (`INC-421`, `LAUNCH-101`, etc.), agent names, org topology, and DAG structure are fixed per task family — train/dev/test splits are seed-disjoint but not entity-disjoint. Entity-disjoint OOD splits and org/DAG-level variation are planned extensions and are outside the scope of this version.

## Design principles

1. One source of truth across apps.
2. Thin app simulators, not SaaS clones.
3. Partial/asymmetric observations.
4. Search and discovery before direct mutation.
5. Heterogeneous employee permissions.
6. Dependency-rich tasks with multiple valid action interleavings.
7. State-based deterministic verification.
8. Reward progress/outcome, not clicks/tool calls.
9. Seeded reproducibility and inspectable traces.
10. Build a research instrument first; UI is only a debugger/demo surface.

## LLM benchmark — five providers (three FREE, no credit card)

All produce JSON + CSV results under `benchmark_results/`.

### Option A — Google Gemini (FREE — recommended for Windows)

```powershell
# Get free key at https://aistudio.google.com/app/apikey
$env:GEMINI_API_KEY="AIza..."
python scripts/run_llm_benchmark.py --provider gemini --task customer_incident --episodes 1
python scripts/run_llm_benchmark.py --provider gemini --task all --episodes 3
```

Default model: `gemini-1.5-flash`. Typical latency: ~1–2 s/call.

### Option B — Alibaba Qwen via DashScope (FREE)

```powershell
# Get free key at https://dashscope.aliyuncs.com
$env:DASHSCOPE_API_KEY="sk-..."
python scripts/run_llm_benchmark.py --provider qwen --task customer_incident --episodes 1
python scripts/run_llm_benchmark.py --provider qwen --task all --episodes 3
```

Default model: `qwen-turbo`. Also available: `qwen-plus`, `qwen-max`.

### Option C — Groq Cloud (FREE, fastest)

```powershell
# Get free key at https://console.groq.com
$env:GROQ_API_KEY="gsk_..."
python scripts/run_llm_benchmark.py --provider groq --task all --episodes 3
```

Default model: `llama-3.1-8b-instant`. Override with `--model llama-3.3-70b-versatile`.

### Option D — Ollama (local, no API key, slow on CPU)

```powershell
ollama pull qwen2.5:7b
python scripts/run_llm_benchmark.py --provider ollama --model qwen2.5:7b --task customer_incident --episodes 1
```

Expect ~7–10 s/call on CPU; use a GPU or a hosted provider for repeated benchmarking.

### Centralized vs decentralized experiment

```powershell
python scripts/run_llm_benchmark.py --provider gemini --task all --episodes 3 --mode centralized  --output benchmark_results/gemini_centralized.json
python scripts/run_llm_benchmark.py --provider gemini --task all --episodes 3 --mode decentralized --output benchmark_results/gemini_decentralized.json
```

See `RUN_WINDOWS_FREE_LLM.md` for the complete Windows/VS Code step-by-step guide.

## Final validation

The packaged validation report is in `docs/final_validation.md`. The improved build is checked with **70 automated tests** (including negation-hardening tests covering both pre- and post-keyword negation patterns, and info-leakage tests verifying evaluator state is separated from agent-facing info), 25-seed rule/random baseline evaluation, reward-ablation execution, trajectory export, provider-response parser mocks (Ollama, Gemini, Qwen), and editable installation.

## Local PC quick start

### Windows PowerShell

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
python examples/customer_incident_demo.py
python scripts/compare_baselines.py --episodes 25
python scripts/export_trajectory.py --task customer_incident --seed 42
```

Or run `powershell -ExecutionPolicy Bypass -File scripts/quickstart_windows.ps1`.

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
pytest -q
python examples/customer_incident_demo.py
python scripts/compare_baselines.py --episodes 25
python scripts/export_trajectory.py --task customer_incident --seed 42
```

### Optional trajectory UI

```bash
pip install -e '.[ui]'
streamlit run ui/app.py
```

### Optional PettingZoo adapter

```bash
pip install -e '.[rl]'
```

## Submission assets

`deliverables/` contains the final submission checklist, presentation content, a 4-minute demo script, and a note about the required genuine Claude Code/Cursor prompt trace. The prompt trace must be exported from the actual development tool rather than fabricated.

## Docker + Ollama reproducible run

The recommended evaluator path is Docker Compose because it removes the two most common local failures: an Ollama server that is not running and a model that was never pulled.

```bash
cp .env.example .env
# optional: edit OLLAMA_MODEL, TASK, EPISODES, MODE
docker compose up --build --abort-on-container-exit benchmark
```

Compose starts Ollama, waits for it to become healthy, pulls the configured model into a persistent volume, runs environment/Ollama diagnostics, and then launches the LLM benchmark. Results are written to `benchmark_results/` on the host.

Useful variants:

```bash
OLLAMA_MODEL=qwen2.5:7b TASK=customer_incident EPISODES=1 docker compose up --build --abort-on-container-exit benchmark
TASK=meeting_conflict MODE=decentralized docker compose up --build --abort-on-container-exit benchmark
```

For an already-running host Ollama installation, diagnose before benchmarking:

```bash
python scripts/diagnose.py --model qwen2.5:3b
python scripts/run_llm_benchmark.py --provider ollama --model qwen2.5:3b --task customer_incident --episodes 1
```

### Why the previous Ollama run failed

The saved failed trajectory used natural-language searches such as `authentication outage` and `production authentication outage`. The old repository implementation required the complete query string to occur contiguously in the target text, so semantically correct searches returned zero results. Small local models then tended to retry equivalent searches until the duplicate-action guard stopped the episode. Search now uses deterministic lexical term matching and ranking, preserving task difficulty while making the simulated enterprise search tool behave realistically.

## Baseline taxonomy and benchmark credibility

Four baselines are included. Their intended use and credibility differ:

| Baseline | Score | Credibility |
|---|---|---|
| **Oracle** | ~100 % | Deterministic rule-based upper bound. Confirms the task is solvable. |
| **Hint-guided / SOP-guided** | ~93 % | Receives exact ticket IDs, cell addresses, and verbatim JSON payloads in its context. **Not evidence of autonomous capability** — treat as an oracle debug baseline or SOP execution check, not as an LLM intelligence score. |
| **Zero-shot LLM** | 0–10 % | No hints; tests genuine autonomous multi-agent reasoning on novel task instances. The meaningful research number. |
| **Random** | ~0 % | Action-space lower bound. Confirms the reward function is not trivially hackable. |

When citing results, always report the zero-shot score. The hint-guided score should be labeled "SOP-guided debug baseline (hint-injected)" to avoid inflating perceived LLM capability.

### Research integrity

The LLM policy still receives only agent-visible observations and actual tool results. Search ranking, diagnostics, and retry handling do not inspect hidden verifier state or execute business actions for the policy. The deterministic verifier remains the source of truth for success.
