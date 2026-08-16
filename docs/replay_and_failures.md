# Replay and Failure Analysis

Every benchmark result contains the exact task name, seed and full action trajectory. A trajectory can be persisted and replayed against a clean environment to detect nondeterminism.

```bash
python scripts/replay_episode.py benchmark_results/launch_readiness_episode.json
```

The replay check re-executes the same tool actions from the original seed and compares success/progress transitions.

Benchmark episodes also expose an interpretable failure taxonomy:

- `tool_use_failure`
- `permission_failure`
- `constraint_violation`
- `retrieval_failure`
- `looping`
- `policy_failure`
- `planning_or_horizon_failure`
- `incomplete_coordination`

Aggregates include permission and constraint violation rates in addition to success, progress, steps, invalid-action rate, repeated actions, token use and latency.
