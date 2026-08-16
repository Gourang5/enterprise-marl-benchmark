# Research Upgrades Applied in This ZIP

## Environment
- Added a fifth simulated enterprise app: **Sheets**.
- Added sheet membership roles and server-side write authorization.
- Added Sheets tools to environment legal-tool discovery, action validation, observations and Ollama tool schemas.
- Added `launch_readiness_v1`, a five-app workflow with four required human/agent roles and dependency-gated verification.

## Factory
- Replaced the thin factory stub with implemented scenario blueprints.
- Added `easy`, `medium`, `hard`, and `adversarial` presets.
- Added deterministic factory-level distractor injection.
- Added reproducible train/dev/test JSONL manifest generation with disjoint seed spaces.
- Included sample hard-difficulty manifests in `generated_scenarios/`.

## Evaluation
- Added failure taxonomy for tool, permission, constraint, retrieval, looping, policy and horizon failures.
- Added aggregate permission-violation and constraint-violation metrics.
- Added episode save/replay tooling for determinism checks.
- Added a replayable successful Launch Readiness trajectory.
- Updated benchmark CLIs to cover all six task families.

## Demo / researcher usability
- Updated Streamlit task selector and failure display.
- Updated README, factory documentation, presentation content, and validation report.
- Preserved the Docker + local Ollama path and earlier natural-language search fix.

## Validation result
- 64/64 automated tests pass.
- Launch Readiness deterministic baseline completes in 17 steps.
- Replay check reports zero mismatches.
