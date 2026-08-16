# Scenario Factory

The factory is implemented in `enterprise_env.generation.ScenarioFactory`.

## What the factory does today

```python
from enterprise_env.generation import ScenarioFactory

factory = ScenarioFactory()

# Build a single live environment
env, obs, info = factory.build("vendor_onboarding", seed=42, difficulty="hard")

# Generate a full train/dev/test dataset
factory.export_dataset(
    "generated_scenarios",
    train=1000, dev=200, test=500,
    difficulty="hard", seed=0
)
```

### Implemented capabilities

| Capability | Details |
|---|---|
| `build(task, seed, difficulty)` | Live env in one call; resets task + injects distractors |
| Difficulty presets | easy (2 distractors) / medium (6) / hard (15) / adversarial (30) |
| Realistic distractor pools | 10 near-miss email subjects/bodies, 7 Jira noise tickets, 6 Slack messages |
| Disjoint seed ranges | train: 0–999k / dev: 1M–2M / test: 2M–3M |
| `generate_split(n, split, difficulty, seed)` | JSONL manifest with per-scenario metadata |
| `export_dataset(output_dir, ...)` | Writes train/dev/test JSONL + manifest.json |
| `validate(env)` | Zero progress · acyclic DAG · valid dependency refs |
| 6 task families | Full DAG, verifier, and oracle baseline for every task |

### Scalable axes today

`task_family × seed × difficulty × split`

```bash
# Generate a hard dataset
python scripts/generate_dataset.py \
    --output generated_scenarios \
    --train 1000 --dev 200 --test 500 \
    --difficulty hard --seed 42
```

Each JSONL row records: task family, seed, split, difficulty, max_steps, app set, subgoal count.
The same scenario is reconstructed deterministically from the seed.

---

## Production-scale design (planned)

The current factory fixes entity IDs, agent names, org topology, and DAG structure
inside each task family. Generating genuinely novel environments requires parameterizing
these axes. The planned architecture:

```
CompanySpec
    → org chart generation (headcount, reporting lines, team structure)
    → employee identity generation (names, roles, seniority)
    → permission matrix generation (per-role × per-app × per-sheet)
    → app state generation
        → email thread history
        → Slack channel history
        → Jira ticket history (prior issues, assignees, comments)
        → calendar state (existing meetings)
        → sheet state (existing rows)
    → cross-app entity consistency
        → same employee ID appears correctly in email, Slack, Jira, Calendar
    → task archetype parameterization
        → vary requester, approver, ticket codes, project names
    → DAG synthesis
        → vary subgoal count, branching, parallel vs sequential structure
    → distractor generation from CompanySpec
    → entity-disjoint OOD train/test splits
```

**Status**: architecture intent documented; not implemented in this version.
Current task families are the reference implementations showing what
a generated task must provide: a subgoal DAG, verifier, oracle baseline,
and a solvability-confirmed initial state.

---

## Validation gates

Every built scenario must pass before use:

1. **Zero initial progress** — no subgoal is accidentally pre-satisfied
2. **Acyclic DAG** — DFS cycle detection on the dependency graph
3. **Valid dependencies** — all `depends_on` IDs resolve to existing subgoal IDs
4. **Deterministic replay** — same seed → same episode outcome

Solvability is confirmed by running the oracle baseline on any new task family.
The oracle achieves 100% on all 6 current task families across 25 seeds.

---

## Difficulty presets

| Level | Distractors | Intended use |
|---|---|---|
| easy | 2 | Initial training; near-clean environment |
| medium | 6 | Standard benchmark evaluation |
| hard | 15 | Heavy retrieval challenge |
| adversarial | 30 | Maximum noise with misleading near-miss keywords |

Oracle baseline is 100% at all difficulty levels (scripted oracle is distractor-immune).
Random baseline is 0% at all difficulty levels (structured reasoning required regardless).

---

## Limitations

- Splits are **seed-disjoint** but not **entity-disjoint** — the same ticket IDs
  and agent names appear across all splits. Entity-disjoint OOD splits require
  CompanySpec generation (planned).
- Distractor content is drawn from fixed pools (10 email subjects, 10 bodies, etc.).
  CompanySpec generation would derive distractors from the synthetic company state.
- DAG structure is fixed per task family. DAG synthesis is a planned extension.
