# Enterprise Multi-Agent RL Benchmark — Slide Deck
## Presentation Content v1.3  |  118 tests pass  |  6 tasks  |  5 agents  |  5 apps

---

# SECTION 1 — THE ENVIRONMENT  (Slides 1–13)

---

## Slide 1 — Title

**Enterprise Multi-Agent RL Benchmark**

> *Can autonomous agents coordinate across applications, roles, and permissions
> to complete realistic enterprise workflows?*

- 5 heterogeneous agents · 5 simulated apps · 6 dependency-gated tasks
- Shared persistent state · Deterministic state-based evaluator
- 118 automated tests · Fully reproducible from seed

**Visual suggestion:** central "company" node with 5 app nodes (Gmail, Slack, Jira, Calendar, Sheets)
around it, 5 small agent icons below. Clean, minimal.

---

## Slide 2 — The Gap: Why Existing Benchmarks Miss Enterprise Work

| Dimension | Typical Benchmark | This Benchmark |
|---|---|---|
| Agents | 1 | 5, heterogeneous |
| Apps / state | 1 | 5, shared persistent DB |
| Permissions | None | Per-role × per-app × per-sheet |
| Horizon | 1–5 steps | 8–17 subgoals, 25–45 steps |
| Dependencies | None | Gated DAG — later credit blocked |
| Information | Symmetric | Asymmetric per-agent observations |
| Evaluation | String match / LLM judge | Deterministic DB state check |

Enterprise work demands all of these simultaneously.
This benchmark is designed to combine all of these dimensions within a single evaluation environment.

**Visual suggestion:** side-by-side comparison table, cells color-coded green (this benchmark)
vs grey (typical benchmarks).

---

## Slide 3 — Environment Overview

One synthetic company, five application simulators, one shared database.

```
Gmail · Slack · Jira · Calendar · Sheets
              ↓
      SQLite shared company state
         ↙              ↘
  Agent observations    Deterministic evaluator
  (role-filtered)       (private, state-based)
```

- Every episode resets from a deterministic integer seed
- Evaluator state is **not** visible to agents — `info["eval"]` is separate from `info`
- Semantic tool actions — malformed calls are invalid transitions, not crashes
- An agent cannot succeed by claiming "task complete" in Slack — the DB must match

**Visual suggestion:** three-row diagram: apps row → shared state row → two outputs
(observations left, evaluator right).

---

## Slide 4 — Architecture

```
Policy / controller
      │
      ▼  Action(agent, app, action_type, params)
EnterpriseEnv
  ├── role-filtered observation builder
  ├── semantic action validator + dispatcher
  └── reward engine
      │
      ▼
App simulators  (thin, stateless — pure DB reads/writes)
      │
      ▼
SQLite shared state  ──→  private verifier (DAG + subgoal checks)
```

- Execution: **turn-based, actor-selected sequential** (not truly parallel)
- RL interface: Gymnasium-compatible `reset(seed)` / `step(action)` / `close()`
- **Experimental** PettingZoo AEC adapter available (`pip install -e ".[rl]"`)
- Standard MARL algorithms require an action encoder — semantic Dict spaces are not
  directly consumable by off-the-shelf policy libraries

**Visual suggestion:** vertical pipeline with labeled boxes and arrows. Mark PettingZoo
as "Experimental" with a small badge.

---

## Slide 5 — Multi-Agent Model

Five agents with **different roles, different app access, different information**.

| Agent | Role | App Access | Sheet Role |
|---|---|---|---|
| pm_01 | Project Manager | Gmail, Slack, Jira, Calendar, Sheets | Owner (R/W) |
| eng_01 | Engineer | Slack, Jira, Calendar | Viewer |
| product_01 | Product Manager | Slack, Jira, Sheets | Editor |
| mgr_01 | Eng. Manager | Slack, Jira, Calendar | — |
| cs_01 | Customer Success | Gmail, Slack, Jira | — |

- **Who** can act: per-agent tool whitelist enforced on every call
- **When** credit is earned: subgoal dependencies, not step order
- **What** each agent sees: only their own inbox, accessible channels, searchable tickets

**Visual suggestion:** agent permission matrix as a grid with colored cells.
Rows = agents, columns = apps.

---

## Slide 6 — Long-Horizon Task: Vendor Onboarding

**8 subgoals · 40-step horizon · 5 apps · 4 roles must act**

A new vendor (TechNova Solutions) must be onboarded end-to-end.

Steps required across roles:
1. **pm_01** discovers the vendor email and finds the procurement ticket (Gmail → Jira)
2. **product_01** clears the legal contract (Jira)     ← runs in parallel with step 3
3. **eng_01** confirms IT provisioning (Jira)           ← runs in parallel with step 2
4. **mgr_01** approves the procurement ticket (Jira)
5. **pm_01** marks vendor ACTIVE in the tracker sheet (Sheets)
6. **pm_01** schedules kickoff meeting (Calendar)       — requires steps 2+3 complete
7. **pm_01** announces completion in Slack (Slack)      — requires steps 5+6 complete

Research properties: parallel branches, strict RBAC on sheet write, role separation,
information asymmetry, negation-hardened verification.

**Visual suggestion:** horizontal role swim-lane diagram.
Rows = agents; columns = time steps; colored boxes = actions; arrows = dependencies.

---

## Slide 7 — Task Dependency DAG (Vendor Onboarding)

```
discover_request (pm_01)
        │
        ├──► find_main_ticket (pm_01)
        │           │
        │           └──► manager_approval (mgr_01)
        │                       │
        │                       └──► update_vendor_sheet (pm_01)
        │                                                    │
        ├──► legal_review (product_01) ─────────────────────►│
        │                              │                      │
        │                              └──► schedule_kickoff ►│
        └──► it_provisioning (eng_01) ─┘                      ▼
                                               announce_live (pm_01)
```

- Nodes are **subgoals**, not steps — credit fires when DB state matches the predicate
- Later subgoals are locked until prerequisites complete
- Parallel branches (legal ∥ IT) both required before kickoff
- Verifier is negation-hardened: `"NOT provisioned"` fails, `"Provisioned and confirmed"` passes

**Visual suggestion:** clean DAG with role-colored nodes.
pm_01 = blue, eng_01 = green, product_01 = orange, mgr_01 = red.

---

## Slide 8 — Partial Observability & Permissions

**What each agent can see:**
- Own email inbox headers only (must `read_email` to see body)
- Slack channels they belong to
- Jira tickets returned by their own `search_issues` query
- Own calendar

**What no agent can see:**
- Other agents' inboxes
- Verifier progress or subgoal status
- Full Jira database (search required — ticket IDs are not pre-known)
- Sheet cells outside their membership role

**Practical research challenge:**
- Agents must `search_emails` and `search_issues` with relevant keywords to discover task context
- Distractors (realistic near-miss emails/tickets) make retrieval non-trivial
- Wrong permission → `{"success": false, "message": "Permission denied"}` — not silent failure

**Visual suggestion:** two columns: "Agent A sees" (inbox A, channels A) vs "Agent B sees"
(inbox B, channels B) — with a locked icon in between.

---

## Slide 9 — Reward Design & Deterministic Verification

### Reward components

| Signal | Value | Purpose |
|---|---|---|
| Valid tool action | +0.25 | Execution credit |
| Subgoal unlocked | +8 × (1/N) | Shaped, per new subgoal |
| Coordination bonus | +2.0 | Multi-agent handoff required |
| Terminal success | +75.0 | Episode completion |
| Redundant action | −1.0 | Penalizes reward farming |
| Step cost | −0.10 | Efficiency pressure |
| Timeout | −15.0 | Horizon enforcement |

### Verification

- Success = **state predicate over SQLite** — not string match, not LLM judge
- Clause-boundary negation detection: `"NOT approved"` → fail; `"Approved. No further action."` → pass
- Agent cannot succeed by posting "done" in Slack — the ticket, sheet, and calendar records must all match

**Visual suggestion:** reward timeline showing shaped signal unlocking at each subgoal,
spike at terminal success.

---

## Slide 10 — Evaluation, Baselines & Replay

### Four-tier policy taxonomy

```
Random (0%)  ─────────────────────────────────────────  Oracle (100%)
                 Zero-Shot LLM (0%, qwen2.5:3b)
                 Hint-Guided LLM (93%, qwen2.5:3b)
```

| Policy | Result | Notes |
|---|---|---|
| Random | 0/30 episodes | Lower bound confirmed — tasks non-trivial |
| Zero-Shot LLM | 0/30 episodes (5 ep/task) | qwen2.5:3b pilot; larger models expected higher |
| Hint-Guided LLM | 24/30 episodes (5 ep/task) | SOP-guided debug baseline — not evidence of autonomous capability |
| Oracle / Deterministic | 30/30 episodes | Upper bound; proves solvability |

### Infrastructure
- HTML trajectory viewer + JSON replay (`scripts/export_trajectory.py`)
- Wilson 95% CI on all success rates
- Failure taxonomy: `tool_use_failure`, `permission_failure`, `looping`, `constraint_violation`
- Streamlit dashboard (`streamlit run ui/app.py`)

**Visual suggestion:** horizontal bar chart showing four tiers, color-coded.
Random = grey, Zero-Shot = yellow, Hint-Guided = blue, Oracle = green.

---

## Slide 11 — Research Use Cases & Limitations

### What this benchmark studies

- **Planning** — multi-step reasoning across apps and roles
- **Tool use** — structured semantic action selection under partial observability
- **Coordination** — one agent's output becomes another's prerequisite
- **Delegation** — transferring work across roles at the correct moment
- **Long-horizon reasoning** — 8–17 subgoals, 25–45 step episodes
- **Partial observability** — asymmetric information across heterogeneous agents
- **Credit assignment** — shaped reward over a dependency-gated DAG
- **Error recovery** — invalid action returns error; agent must adapt

### Honest limitations

- Execution is turn-based sequential — true parallel MARL requires an action encoder
- Experimental PettingZoo AEC adapter; not all AEC methods tested
- Entity IDs fixed per task family — splits are seed-disjoint but not entity-disjoint
- Zero-shot measured on qwen2.5:3b (1 ep/task only); result is model-dependent
- No Figma, GitHub, or HR apps in this version

**Visual suggestion:** two-column checklist: research capabilities (green ticks)
vs limitations (orange flags).

---

## Slide 12 — RL & Research Interface

**The environment exposes a clean Gymnasium-compatible RL boundary.**

### Observation (per-agent, role-filtered)

```
obs = {
  "agent":    {employee_id, name, role, team_id},
  "time":     int,                # step counter
  "inbox":    [email headers],    # bodies hidden — requires read_email
  "channels": [channel records],  # only channels agent belongs to
  "calendar": [event records],    # own calendar only
  "sheets":   [{sheet_id, name, role}],
  "task":     {id, name, instruction}
}
```

### Action (structured semantic space)

```python
Action(agent_id="pm_01", app="jira",
       action_type="change_status",
       parameters={"issue_id": "VEND-401", "status": "approved"})
```

18 action types across 5 apps. **Each agent sees only their permitted subset** (14–18 actions).
The permission table is the **static action mask** — invalid calls return an error, never crash.

### Step return

```
obs, reward, terminated, truncated, info = env.step(action)

info["eval"]  → {progress, subgoals, reward_components}  # evaluator-only; not shown to agent
```

### CTDE framing

Training centralizes `info["eval"]` subgoal labels for critic conditioning.
Execution uses per-agent obs only — policies are fully decentralized.

**Visual suggestion:** three horizontal bands: Observation (left panel), Action encoder
(center, labeled "integration boundary"), Environment step (right). Arrow from env back
to obs. Small lock icon on info["eval"]. Color-code: obs = blue, action = green, eval = grey.

---

## Slide 13 — Research Questions Enabled

**The 80-point gap between zero-shot (0/30) and hint-guided (24/30) performance is the open problem.**

| Research Question | Method | Benchmark Feature |
|---|---|---|
| Can BC close 0% → 93%? | Behavioral Cloning on oracle trajectories | Trajectory export, deterministic seed |
| Does CTDE outperform IQL? | MAPPO vs IQL (shared vs independent critic) | `info["eval"]["subgoals"]` labels |
| Does action masking speed convergence? | PPO ± permission mask | Static permission table per agent |
| Does distractor density affect sample efficiency? | RL across easy→adversarial presets | 4 difficulty levels, calibrated counts |
| Can a policy generalize across seeds? | Train 0–999k, test 2M–3M | Disjoint seed-range splits |
| Does shaped reward outperform sparse? | Ablate subgoal bonus | Reward component breakdown |
| Can offline RL recover near-oracle behavior? | IQL / CQL on oracle dataset | `export_dataset()` |

### Offline RL pipeline (available today)

```bash
# 1. Generate oracle trajectories for all 6 tasks, 1000 seeds
python scripts/generate_dataset.py --train 1000 --dev 200 --test 500

# 2. Export oracle trajectory for a specific episode
python scripts/export_trajectory.py --task vendor_onboarding --seed 42

# 3. Use trajectories for BC / imitation learning
```

**Next step**: Behavioral Cloning on oracle/hint-guided trajectories → PPO against shaped reward
→ entity-disjoint OOD evaluation via Factory V2 generalized across task families.

**Visual suggestion:** bar chart with 4 policies on x-axis (Random / Zero-Shot / Hint-Guided / Oracle),
success rate on y-axis (0% / 0% / 93% / 100%). Bracket spanning the gap with label "Open Research Gap".
Below: 3-arrow pipeline: "BC → PPO → OOD eval".

---

# SECTION 2 — THE SCENARIO FACTORY  (Slides 14–20)

---

## Slide 14 — Why a Factory Is Necessary

A handcrafted task is a **demo**.
A factory that mass-produces environments is a **research instrument**.

**The RL training loop requires:**

| Need | Without Factory | With Factory |
|---|---|---|
| Training data | Same 6 episodes every run | 1,000+ seed-disjoint episodes |
| Generalization test | Impossible (train = test) | Held-out seed spaces enforced |
| Curriculum | Manual difficulty adjustment | easy → adversarial presets |
| Reproducibility | Hope nothing changed | Same seed → identical episode, always |
| Scale-up | 6 tasks maximum | Thousands of validated scenario instances |

**Visual suggestion:** split screen — left: "6 handcrafted tasks (demo)";
right: "factory → 1000s of validated scenarios (research)".

---

## Slide 15 — Factory Architecture

```
Task family  +  Seed  +  Difficulty preset
                │
                ▼
        ScenarioFactory.build()       ◄─── IMPLEMENTED
          ├── make_env(task)
          ├── env.reset(seed)          ← task fixtures + company state
          ├── inject_distractors()     ← seed-specific realistic noise
          └── validate()              ← structural + solvability checks
                │
                ▼
          Live EnterpriseEnv  →  generate_split()  →  export_dataset()
                                       │
                                       ▼
                             JSONL scenario manifests
                         (scenario_id, seed, difficulty,
                          apps, agents, subgoal_count,
                          validator_status)

═══════════════════════════════════════════════════════════
PLANNED — Production-scale generation
        CompanySpec → org generator → identity generator
        → permission matrix → app state generators
        → cross-app entity graph → task archetype
        → DAG synthesizer → verifier generator
        → curriculum calibrator → large-scale validation
```

**Visual suggestion:** two-section pipeline diagram.
Top half (implemented) in solid color; bottom half (planned) in lighter grey with "PLANNED" label.

---

## Slide 16 — What Is Implemented Today

**ScenarioFactory** (`enterprise_env/generation.py`) — production-ready for current task families:

| Capability | Detail |
|---|---|
| `build(task, seed, difficulty)` | Live, validated env in one call |
| 4 difficulty presets | easy (2) / medium (6) / hard (15) / adversarial (30) distractors |
| Realistic distractor pools | 10 email subjects/bodies, 7 Jira tickets, 6 Slack messages |
| Seed-disjoint splits | train: 0–999k / dev: 1M–2M / test: 2M–3M |
| JSONL manifest export | scenario_id, seed, difficulty, apps, agents, subgoal_count |
| Validation gates | Zero initial progress · acyclic DAG · dep IDs resolve |
| 6 task families | Full DAG, verifier, oracle baseline for every task |

```python
factory = ScenarioFactory()

# One live environment
env, obs, info = factory.build("vendor_onboarding", seed=42, difficulty="hard")
# info["validator_status"] == "passed"

# Full dataset
factory.export_dataset("generated_scenarios",
                        train=1000, dev=200, test=500, difficulty="hard")
```

**Visual suggestion:** checklist table with green tick marks.

---

## Slide 17 — Production-Scale Generation Architecture  *(Planned)*

```
CompanySpec (seed + org parameters)
      │
      ├──► Org chart generator         → headcount, reporting lines, teams
      ├──► Identity generator          → names, roles, seniority, departments
      ├──► Permission matrix builder   → per-role × per-app × per-sheet
      │
      ├──► App state generators
      │     ├── Email thread history
      │     ├── Slack channel history
      │     ├── Jira ticket history    → past issues, comments, assignees
      │     ├── Calendar state         → existing meetings, blocked hours
      │     └── Sheet state            → existing rows, data
      │
      ├──► Cross-app entity graph      → same person ID consistent everywhere
      │
      ├──► Task archetype              → requester, approver, ticket codes vary
      ├──► DAG synthesizer             → subgoal count, branching, parallel/linear
      ├──► Verifier generator          → auto-derives predicates from task spec
      │
      └──► Entity-disjoint OOD splits  → test agents on unseen org topologies
```

**Status**: design intent documented. Current task families are the reference
implementation for what a generated scenario must satisfy.

**Visual suggestion:** pipeline flowchart, all boxes in light grey with dashed borders.
Single "PLANNED" watermark across the slide.

---

## Slide 18 — Factory Quality Gates

Every generated scenario passes this pipeline before it is accepted into a dataset:

```
Generated Scenario
        │
        ▼
[1] Schema validation          → scenario_id, seed, apps, agents all present
        │
        ▼
[2] Cross-app consistency      → same entity IDs used correctly across apps
        │
        ▼
[3] Permission validation      → every subgoal assignable to an agent with access
        │
        ▼
[4] Solvability check          → oracle baseline completes episode from initial state
        │
        ▼
[5] Verifier validation        → correct trajectory passes · negated trajectory fails
        │
        ▼
[6] Leakage check              → verifier state absent from agent-visible info
        │
        ▼
[7] Replay determinism         → same seed → byte-identical starting state
        │
        ▼
[8] Difficulty calibration     → distractor count matches requested preset
        │
        ▼
   ✅  Accepted dataset instance
```

**Implemented today**: gates 1, 4, 6, 7, 8 via `validate()` + oracle baseline.
**Planned**: gates 2, 3, 5 (automated, systematic — currently verified by construction per task family).

**Visual suggestion:** vertical pipeline with numbered green gates; checkmarks on implemented,
dashed outlines on planned.

---

## Slide 19 — Difficulty, Curriculum & Reproducibility

### Difficulty calibration

| Preset | Distractors | Effect |
|---|---|---|
| easy | 2 | Minimal noise — near-direct path |
| medium | 6 | Focused retrieval required |
| hard | 15 | Heavy noise — same domain, wrong details |
| adversarial | 30 | Near-miss keywords designed to mislead |

Oracle = 100% at all levels (scripted oracle is distractor-immune).
Random = 0% at all levels (structured reasoning required at every difficulty).

### Splits

Disjoint seed ranges prevent episode reuse across train/dev/test.
Same seed → identical episode always — fully reproducible.

```bash
# Generate a full curriculum dataset in one command
python scripts/generate_dataset.py \
    --output generated_scenarios \
    --train 1000 --dev 200 --test 500 \
    --difficulty hard --seed 42
```

**Visual suggestion:** bar chart — x-axis = difficulty level; y-axis = success rate.
Oracle bar at 100% (green) across all levels; Random bar at 0% (grey) across all levels.

---

## Slide 20 — Operating at Scale · Closing Value Proposition

### What is delivered in this version

| Capability | Status |
|---|---|
| 6 long-horizon multi-agent tasks | ✅ |
| 5 apps · 5 agents · role-based permissions | ✅ |
| Dependency-gated subgoal DAGs | ✅ |
| Deterministic DB-state verification | ✅ |
| Oracle 30/30 · Hint-guided 24/30 · Zero-Shot 0/30 (5 ep/task each) | ✅ |
| ScenarioFactory: seeds × difficulty × splits | ✅ |
| Scenario manifests with validator_status | ✅ |
| Trajectory export, replay, Streamlit dashboard | ✅ |
| Docker Compose reproducible deployment | ✅ |
| 118 automated tests · 0 flaky | ✅ |
| Factory V2: entity-level world generation (vendor_onboarding vertical slice) | ✅ Prototype |

### Feature Status

| IMPLEMENTED | PROTOTYPE / EXPERIMENTAL | ROADMAP |
|---|---|---|
| 6 tasks + DAG verifiers | Factory V2 world generation (1 task) | Factory V2 for all 6 tasks |
| ScenarioFactory (all 6 tasks) | PettingZoo AEC adapter | DAG synthesizer |
| Oracle + hint-guided + zero-shot baselines | SHA-256 world fingerprinting | Org/identity generator |
| Deterministic DB-state verification | WorldValidator structural checks | Automated verifier generation |
| Role-based permissions (RBAC) | — | Entity-disjoint OOD splits |
| Shaped reward + anti-hacking logic | — | Large-scale curriculum calibration |
| Trajectory export + replay | — | — |
| Streamlit dashboard | — | — |
| Docker Compose deployment | — | — |

### The research question this benchmark opens

> Can autonomous multi-agent systems close the gap between
> **zero-shot performance (0/30 episodes)** and **procedurally-guided performance (24/30 episodes)**
> in realistic enterprise coordination workflows?

**Next steps**: Behavioral Cloning on hint-guided trajectories →
PPO against shaped reward → entity-disjoint OOD evaluation.

**Visual suggestion:** "delivered" checklist on the left; bold research question
centered on the right with a simple 0% → 93% gap graphic.
