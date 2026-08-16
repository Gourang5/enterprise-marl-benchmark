# Environment Factory

The factory is implemented in `enterprise_env.generation.ScenarioFactory`; it is no longer only a future-design note.

## Production pipeline

```text
Task family
   + company fixture
   + seed
   + difficulty preset
        |
        v
ScenarioFactory
   -> task dependency DAG
   -> app fixtures
   -> permission/access model
   -> seeded distractor injection
   -> initial-state validation
   -> reproducible scenario blueprint
   -> train/dev/test manifest
        |
        v
benchmark / replay / analysis
```

## Difficulty presets

- `easy`: 2 factory-level distractors
- `medium`: 6 distractors
- `hard`: 15 distractors
- `adversarial`: 30 distractors

Task families may add their own seed-dependent distractors on top. Difficulty is deterministic for a given seed.

```python
from enterprise_env.generation import ScenarioFactory
factory = ScenarioFactory()
env, obs, info = factory.build("launch_readiness", seed=42, difficulty="hard")
```

## Train/dev/test generation

The factory assigns disjoint seed ranges to train, dev and test manifests to reduce accidental overlap.

```bash
python scripts/generate_dataset.py \
  --output generated_scenarios \
  --train 1000 --dev 200 --test 500 \
  --difficulty hard --seed 42
```

Each JSONL row records task family, exact task ID, seed, split, difficulty, step budget, app set and subgoal count. The same blueprint can be reconstructed deterministically.

## Validation gates

Every built environment must:

1. start at zero verifier progress;
2. reference only valid dependency nodes;
3. contain an acyclic dependency graph;
4. preserve deterministic state under the same seed;
5. keep verifier state private from the policy.

Rule baselines provide a practical solvability oracle for every shipped task family.

## Current scalable axes

- task family
- seed
- difficulty / distractor density
- train/dev/test split
- app combination
- horizon through task and difficulty configuration

The next factory extensions would parameterize org-chart topology, generated employee identities, dependency-graph shape, and permission asymmetry rather than holding those dimensions fixed inside a task family.
