# Research-Grade Upgrade Summary

This build extends the earlier fixed prototype with implemented research infrastructure rather than slide-only claims.

## Added

1. **Sheets simulator** with list/read/update/append tools, membership roles, write enforcement, audit logging and LLM tool schemas.
2. **Cross-Team Launch Readiness task** spanning Gmail, Slack, Jira, Sheets and Calendar. Customer Success, Engineering, Product and Engineering Management each own required evidence or authority.
3. **ScenarioFactory difficulty presets** (`easy`, `medium`, `hard`, `adversarial`) with deterministic distractor injection.
4. **Train/dev/test manifest generation** with disjoint seed ranges and reproducible blueprints.
5. **Replay tooling** for deterministic episode re-execution.
6. **Failure taxonomy** and additional permission/constraint violation metrics.
7. **UI support** for the new task and failure diagnostics.
8. **Benchmark coverage** updated to include all six task families.

## Validation

- 70 automated tests pass.
- All six deterministic baselines complete their tasks.
- Random-policy benchmark remains an unsolved floor in the packaged evaluation.
- A saved Launch Readiness trajectory replays with zero mismatches.
- Sample hard-difficulty train/dev/test manifests are included under `generated_scenarios/`.

## Still intentionally not fabricated

No successful live Ollama score is claimed in this container because a running Ollama daemon/model is not available here. Docker/Ollama preflight remains the supported path for producing genuine model results on the submission machine.
