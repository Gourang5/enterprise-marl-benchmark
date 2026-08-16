# Final Validation Report — v1.2

Validation performed in the packaging environment.

## Passed

- Python source compilation (`compileall`).
- Editable install using existing local build tooling (`pip install -e . --no-build-isolation`).
- **64/64 automated tests passed** (including negation-hardening and info-leakage tests).
- Six deterministic task baselines are wired into the benchmark runner.
- Launch Readiness baseline: 3/3 successful episodes, 17 steps, zero invalid actions.
- 10-seed paired rule/random baseline report regenerated for all six tasks.
- Hard-difficulty factory manifests generated: 40 train / 12 dev / 20 test scenarios.
- Train/dev/test seed spaces are disjoint by construction.
- Saved Launch Readiness episode replayed from seed 77 with **zero mismatches**.
- Docker Compose YAML parses successfully and defines `ollama`, `model-bootstrap`, and `benchmark` services.

## Environment limitations

The packaging container has no Docker daemon and no local Ollama daemon/model. Therefore this report does not claim a live container launch or a successful real-model inference run. The repository includes Ollama preflight checks and Docker Compose orchestration so those checks can be run on the submission machine without paid API access.

A normal isolated `pip install -e .` attempted to resolve build dependencies from the internet, but this packaging environment has no network access. Installation with `--no-build-isolation` succeeded using the already-installed local build tooling; this is an environment constraint, not a source-code failure.
