# Presentation Content — Enterprise MARL Benchmark v1.2

---

# SECTION 1 — THE ENVIRONMENT

---

## Slide 1 — Title & Thesis

**Enterprise Multi-Agent RL Environment**
*A benchmark for long-horizon coordination across simulated enterprise applications*

> "Enterprise work is not a single-turn tool call. It is a multi-agent, multi-application,
> permission-bounded workflow that unfolds across hours or days. We build an open benchmark
> that models this faithfully."

Key stats: **5 agents · 5 apps · 6 tasks · 70 automated tests · 0 flaky**

---

## Slide 2 — Why Enterprise Agent Benchmarks?

Existing benchmarks test simple, single-turn, single-agent tasks.
Real enterprise work requires:

| Challenge | Example |
|---|---|
| **Multi-agent coordination** | Engineer validates before manager approves |
| **Multi-app state** | Jira ticket links to Slack thread, Gmail thread, Sheets row |
| **Role-based permissions** | Only pm_01 may write the vendor tracker sheet |
| **Information asymmetry** | Each agent sees only their own inbox, channels, and tickets |
| **Long horizon** | 8–17 sequential steps across 5 applications |
| **Dependency ordering** | Legal review AND IT provisioning must both complete before kickoff |

**Gap in existing benchmarks:**
- WebArena / SWEbench: single agent, single app, no permissions, short horizon
- NetHack / BabyAI: no real-world grounding, no multi-app state
- This benchmark: cross-app, multi-agent, permission-enforced, dependency-gated

---

## Slide 3 — Environment Overview

One synthetic Fortune 500 company (fully synthetic, Walmart-inspired naming)
exposed through **five thin application simulators** backed by **one shared SQLite database**.

```
Gmail ──────┐
Slack ──────┤
Jira ───────┼──► SQLite shared state ──► Subgoal verifier ──► Reward
Calendar ───┤
Sheets ─────┘
```

Every episode resets from a deterministic seed — fully reproducible.
State is company-wide: an email sent by agent A is readable by agent B (if permitted).

**Key design choices:**
- State-based deterministic verification — an agent cannot succeed by saying "task complete"
- Evaluator state (`info["eval"]`) is **separated** from agent-visible state
- Semantic tool calls — malformed calls are invalid transitions, not crashes

---

## Slide 4 — Architecture

```
┌─────────────────────────────────────────┐
│  Policy / multi-agent controller        │
└────────────────┬────────────────────────┘
                 │ Action(agent, app, action_type, params)
                 ▼
┌─────────────────────────────────────────┐
│  EnterpriseEnv                          │
│  ┌──────────────────────────────────┐   │
│  │  Role-filtered observation       │   │
│  │  (inbox headers, channels, etc.) │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │  Semantic tool action validator  │   │
│  └──────────────────────────────────┘   │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│  App simulators (Gmail/Slack/Jira/      │
│  Calendar/Sheets) — thin, stateless     │
└────────────────┬────────────────────────┘
                 ▼
┌─────────────────────────────────────────┐
│  SQLite shared company state            │
│  ┌────────────┐  ┌──────────────────┐   │
│  │  Private   │  │  Agent-visible   │   │
│  │  verifier  │  │  observation     │   │
│  │  (DAG +    │  │  (filtered by    │   │
│  │  reward)   │  │  role + perms)   │   │
│  └────────────┘  └──────────────────┘   │
└─────────────────────────────────────────┘
```

Execution model: **turn-based actor-selected sequential** — each step selects the next
acting agent; agents do not act simultaneously. An experimental PettingZoo AEC
compatibility layer is available (`pip install -e ".[rl]"`).

---

## Slide 5 — Multi-Agent Model & Permissions

Five heterogeneous agents with distinct roles, apps, and permissions:

| Agent | Role | Gmail | Slack | Jira | Calendar | Sheets |
|---|---|---|---|---|---|---|
| pm_01 (Sarah) | Project Manager | R/W | R/W | R/W | R/W | owner |
| eng_01 (Arjun) | Engineer | — | R/W | R/W | R/W | viewer |
| product_01 (Maya) | Product Manager | — | R/W | R/W | — | editor |
| mgr_01 (Daniel) | Eng. Manager | — | R/W | R/W | R/W | — |
| cs_01 (Priya) | Customer Success | R/W | R | R/W | — | — |

**Sheet-level RBAC**: owner > editor > viewer — enforced server-side on every write.
**Tool-level permissions**: per-agent whitelist stored in DB, checked before execution.

Permissions enforce **who** can act.
Subgoal dependencies enforce **when** a subgoal can be credited.

---

## Slide 6 — Long-Horizon Task Example: Vendor Onboarding

The hardest task — 8 subgoals, 40-step horizon, genuine parallel branches:

```
discover_request (pm_01 reads vendor email)
        │
        ├──► find_main_ticket (pm_01 reads VEND-401)
        │           │
        │           └──► manager_approval (mgr_01 approves VEND-401)
        │                       │
        │                       └──► update_vendor_sheet (pm_01 marks ACTIVE in Sheets)
        │                                                       │
        ├──► legal_review (product_01 clears VEND-402) ─────────┤
        │           │                                            │
        │           └──────────────┬──────────────────────────  │
        │                          │                             │
        └──► it_provisioning (eng_01 confirms VEND-403)         │
                            │      │                             │
                            └──────┴──► schedule_kickoff ───────┤
                                                                 ▼
                                             announce_live (pm_01 Slack)
```

**Research properties**: parallel prerequisites (legal ∥ IT), 5 apps, strict RBAC on
sheet write, multi-role separation, negation-hardened verifier, information asymmetry.

---

## Slide 7 — Partial Observability & Information Asymmetry

Each agent's observation contains **only**:
- Their own email inbox headers (must `read_email` to see body)
- Slack channels they belong to
- Jira tickets they can access (requires search first — no direct lookup by ID)
- Their own calendar
- Agent identity + task instruction

**Not visible to agents:**
- Other agents' inboxes
- Verifier progress / subgoal status (`info["eval"]` is stripped at the API boundary)
- Full Jira database — must search to discover ticket IDs
- Sheet cells outside their membership role

**Distractor injection** via ScenarioFactory: realistic near-miss emails and Jira tickets
(same enterprise domain, different task-relevant details) challenge retrieval.

---

## Slide 8 — Reward Design & Deterministic Verification

### Reward components

| Component | Value | Purpose |
|---|---|---|
| Valid tool action | +0.25 | Execution credit |
| Subgoal progress | +8 × (1/N) | Shaped reward per newly unlocked subgoal |
| Multi-agent coordination | +2.0 | Bonus when subgoal requires prior agent handoff |
| Terminal success | +75.0 | Episode completion |
| Redundant action | −1.0 | Anti-hacking: repeated reads do not farm reward |
| Step cost | −0.10 | Efficiency pressure |
| Timeout | −15.0 | Horizon enforcement |

### Deterministic verification

Success is a **state-based predicate** over SQLite — not trajectory similarity, not LLM judge.
The verifier checks: *did the correct agent post the correct content to the correct record?*

**Negation-hardened**: clause-boundary-aware keyword matching.
`"NOT approved"` → fails. `"Approved. No further action required."` → passes.
`"Previous request rejected. This one approved."` → passes (negation in prior sentence).

An agent cannot succeed by saying "task complete" in Slack — the DB state must match.

---

## Slide 9 — Evaluation Infrastructure

### Four-tier policy taxonomy

| Policy | Success Rate | Purpose |
|---|---|---|
| **Random** | **0%** all 6 tasks | Lower bound — tasks require structured reasoning |
| **Zero-Shot LLM** | **0%** (qwen2.5:3b, 1 ep/task) | Raw generalization; the meaningful research number |
| **Hint-Guided LLM** | **93%** overall (qwen2.5:3b, 5 ep/task) | Validates task design and reward function |
| **Oracle / Deterministic** | **100%** all 6 tasks | Upper bound — confirms mechanical solvability |

All results from actual measured runs. Zero-shot 0% with a 3B local model establishes
the capability gap. Larger models (GPT-4o, Claude 3.5) would achieve higher zero-shot
performance — this is a model question, not a benchmark design question.

### Infrastructure

- Trajectory HTML exporter + JSON replay (`scripts/export_trajectory.py`)
- Wilson 95% confidence intervals on all success-rate reports
- Failure taxonomy: tool_use_failure, permission_failure, looping, constraint_violation, horizon
- Reward ablation runner (shaped vs sparse)
- Streamlit dashboard (`streamlit run ui/app.py`)
- Docker Compose reproducible deployment (Ollama + benchmark + UI)

---

## Slide 10 — Full Results Table & Research Value

### Measured results — qwen2.5:3b, centralized mode

| Task | Oracle | Hint-Guided (5ep) | Zero-Shot (1ep) | Random |
|---|---|---|---|---|
| customer_incident | 100% | 100% | 0% | 0% |
| product_launch | 100% | 100% | 0% | 0% |
| meeting_conflict | 100% | 80% | 0% | 0% |
| launch_readiness | 100% | 100% | 0% | 0% |
| budget_approval | 100% | 100% | 0% | 0% |
| vendor_onboarding | 100% | 80% | 0% | 0% |
| **OVERALL** | **100%** | **93%** | **0%** | **0%** |

Two hint-guided failures: model constraint_violation (wrong parameter format) on
meeting_conflict and vendor_onboarding — task design is correct; failure is model-side.

### Research value

| Finding | Implication |
|---|---|
| Oracle 100% | Tasks are mechanically solvable — not broken or under-specified |
| Random 0% | Tasks require structured sequential reasoning — not trivially solvable |
| Hint-guided 93% | Reward function fires correctly; DAGs are well-specified |
| Zero-shot 0% | Large open capability gap; structured workflow knowledge is critical |

### Limitations (honest)

- Zero-shot evaluated on qwen2.5:3b only; larger models expected to score higher
- Execution is turn-based sequential; true parallel MARL requires action encoding
- Entity IDs fixed per task family; entity-disjoint OOD splits are planned
- PettingZoo adapter is experimental — known limitations documented in wrapper

---

# SECTION 2 — THE SCENARIO FACTORY

---

## Slide 11 — Why a Factory?

A single handcrafted task is a **demo**. A factory that mass-produces environments
is a **research instrument**.

**The RL training loop requires:**
1. **Training set** — held-out seeds the agent has never seen
2. **Dev set** — hyperparameter tuning without contaminating test
3. **Test set** — final evaluation, never used during training
4. **Curriculum** — easy → adversarial progression during learning
5. **Ablation variants** — same task, different distractor density, same seed

**Without a factory:** evaluation is on the same 6 handcrafted episodes every run.
Training/test contamination is inevitable.

**With a factory:** generate 1,000 training seeds, 200 dev, 500 test —
all disjoint, all reproducible, all validatable in one command.

---

## Slide 12 — Factory Architecture

```
Task family (customer_incident, vendor_onboarding, …)
    + Difficulty preset (easy / medium / hard / adversarial)
    + Seed (integer → fully deterministic)
                │
                ▼
        ScenarioFactory.build()
                │
    ┌───────────┴────────────────────────────┐
    │  make_env(task, max_steps)             │
    │  env.reset(seed)     ← task fixtures   │
    │  _inject_distractors(env, seed, count) │
    │  validate(env)       ← sanity checks   │
    └────────────────────────────────────────┘
                │
                ▼
    EnterpriseEnv (ready for episode)
                │
                ▼
    generate_split(n, split, difficulty, seed)
                │
                ▼
    export_dataset() → train.jsonl / dev.jsonl / test.jsonl / manifest.json
```

Every generated scenario is validated before export:
zero initial progress · acyclic DAG · all dependency IDs resolve

---

## Slide 13 — What Is Implemented Today

**ScenarioFactory** (`enterprise_env/generation.py`) — fully functional:

| Capability | Status |
|---|---|
| `build(task, seed, difficulty)` — live env in one call | ✅ Implemented |
| 4 difficulty presets (easy/medium/hard/adversarial) | ✅ Implemented |
| Realistic near-miss distractor pools | ✅ Implemented |
| Disjoint seed ranges for train/dev/test | ✅ Implemented |
| JSONL manifest export with per-scenario metadata | ✅ Implemented |
| Validation gates (zero progress, acyclic DAG, dep resolution) | ✅ Implemented |
| 6 task families with full DAG, verifier, and oracle baseline | ✅ Implemented |
| Seeded distractor content variation across episodes | ✅ Implemented |

**Scalable axes**: task family × seed × difficulty × split

```python
from enterprise_env.generation import ScenarioFactory
factory = ScenarioFactory()

# Single live environment
env, obs, info = factory.build("vendor_onboarding", seed=42, difficulty="hard")

# Full dataset
factory.export_dataset("generated_scenarios", train=1000, dev=200, test=500, difficulty="hard")
```

---

## Slide 14 — Production-Scale Factory Design (Planned)

Current factory fixes entity IDs, agent names, org topology, and DAG structure per task family.
Production-scale generalization requires parameterizing these axes:

```
CompanySpec
    → org chart generation (headcount, reporting, team structure)
    → employee identity generation (names, roles, seniority)
    → permission matrix generation (per-role × per-app × per-sheet)
    → app state generation
        → email thread history
        → Slack channel history
        → Jira ticket history (prior issues, comments, assignees)
        → calendar state (existing meetings, conflicts)
        → sheet state (existing rows, data)
    → cross-app entity consistency
        → same person ID appears in email, Slack, Jira, Calendar correctly
    → task archetype parameterization
        → vary requester, approver identity, ticket codes, project names
    → dependency DAG synthesis
        → vary subgoal count, branching, parallel vs sequential structure
    → entity-disjoint OOD train/test splits
    → distractor generation from CompanySpec (not hardcoded pools)
```

**Status**: design intent documented; implementation is the primary planned extension.
Current task families are the reference implementations for what generated tasks must satisfy.

---

## Slide 15 — Validation & Quality Assurance

### Structural validation (every scenario)

- Zero initial verifier progress — no subgoal is accidentally pre-satisfied
- Acyclic dependency graph — DFS cycle detection on every build
- Valid dependency references — all `depends_on` IDs exist in subgoal set

### Solvability validation

- Oracle baseline (rule-based) covers all 6 task families
- Oracle at 100% across 25 seeds confirms mechanical solvability
- Running oracle on any new generated scenario confirms it is solvable

### Leakage prevention

- `info["eval"]` contains privileged evaluator data; stripped from agent observations
- PettingZoo adapter strips eval keys from per-agent info dicts
- Verifier cannot be satisfied by text claims — only DB state counts

### Verifier hardening (36 unit tests)

- Pre-keyword negation: `"NOT approved"` → False
- Post-keyword question-answer: `"Approved? No, rejected."` → False
- Cross-sentence "No": `"Approved. No further action."` → True
- Prior-sentence negation: `"Previously rejected. Now approved."` → True

---

## Slide 16 — Difficulty, Curriculum & Splits

### Difficulty presets

| Level | Distractors | Use |
|---|---|---|
| easy | 2 | Initial training; near-clean environment |
| medium | 6 | Standard evaluation |
| hard | 15 | Heavy retrieval challenge |
| adversarial | 30 | Maximum noise; misleading near-miss keywords |

Oracle 100% at all levels (distractor-immune by design).
Random 0% at all levels (structured reasoning required regardless of noise).

### Train/Dev/Test seed allocation

| Split | Seed range | Purpose |
|---|---|---|
| train | 0 – 999,999 | Agent learning |
| dev | 1,000,000 – 1,999,999 | Hyperparameter selection |
| test | 2,000,000 – 2,999,999 | Final evaluation |

All splits are **seed-disjoint** (episodes never repeat across splits).
Current limitation: splits share entity IDs across splits — not entity-disjoint.
Entity-disjoint OOD splits require CompanySpec generation (planned).

---

## Slide 17 — RL Integration & Future Training

### What works today (no code changes needed)

- Gymnasium-compatible `EnterpriseEnv` with `reset(seed)` / `step(action)` / `close()`
- Shaped reward signal ready for PPO / A2C / value-based methods
- Experimental PettingZoo AEC adapter (`pettingzoo_aec.py`)
- Trajectory export for behavioral cloning data collection

### Limitations to address for RL training

- Semantic actions (Dict spaces) require an action encoder before standard RL libraries
- True parallel MARL is not supported — execution is actor-selected sequential
- Observation space is Dict-based; requires flattening or a custom encoder

### Planned training curriculum

```
1. Behavioral Cloning  — train on hint-guided trajectories
2. PPO / Policy Gradient — optimize against shaped reward
3. QMIX / VDN (CTDE) — centralized training, decentralized execution
4. LLM Fine-tuning — SFT on successful episodes → RLHF
```

The environment infrastructure supports all four paradigms without modification to the core env.

---

## Slide 18 — Closing Value Proposition

**What this version delivers:**

| Capability | Status |
|---|---|
| 6 long-horizon multi-agent enterprise tasks | ✅ |
| 5 apps, 5 heterogeneous agents, role-based permissions | ✅ |
| Dependency-gated subgoal DAGs (linear, fan-out, parallel) | ✅ |
| Deterministic state-based verification (no LLM judge) | ✅ |
| Negation-hardened verifiers (clause-boundary-aware) | ✅ |
| Oracle (100%) + Random (0%) confirm task quality | ✅ |
| Hint-guided 93% validates reward function soundness | ✅ |
| Zero-shot 0% establishes the open research gap | ✅ |
| ScenarioFactory: seeds × difficulty × train/dev/test splits | ✅ |
| Trajectory export, replay, Streamlit dashboard | ✅ |
| Docker Compose reproducible deployment | ✅ |
| 70 automated tests, 0 flaky | ✅ |

**Primary planned extensions:**
- Entity-disjoint OOD splits via CompanySpec generation
- RL training: BC, PPO, QMIX against shaped reward
- Additional apps: GitHub, HR, Finance, Docs
- Larger model zero-shot evaluation (GPT-4o, Claude 3.5, Gemini 1.5 Pro)

**The research question this benchmark opens:**
> Can autonomous multi-agent systems close the gap between zero-shot performance
> and structured-workflow (SOP-guided) performance in realistic enterprise coordination tasks?
