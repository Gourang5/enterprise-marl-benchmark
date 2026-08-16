# Assignment fit and improvement review

## Verdict

This repository is **directly related to the Multi-Agent RL Environment Design assignment**. It implements a synthetic Fortune-500-style company world, multiple employee agents, four enterprise app simulators, long-horizon cross-app tasks, deterministic verification/reward, evaluation baselines, trajectory logging, and factory scaffolding.

It is best described as a **research benchmark MVP**, not a full SaaS clone or a mature mass-production factory.

## What was already strong

- Shared company state across Gmail, Slack, Jira, and Calendar.
- Five heterogeneous roles with permissions.
- Three task families with different reasoning/coordination failure modes.
- State-based success verification rather than reference-trajectory matching.
- Rule/random baselines and inspectable trajectories.
- Centralized and decentralized LLM control modes.
- Synthetic data and reproducible seeds.

## Critical issue found and fixed

The original enterprise search used SQL `%full query phrase%` matching. A reasonable LLM query such as `authentication outage` failed because those exact adjacent words were not present in the seeded report. The saved Ollama trajectory therefore received empty search results and entered a duplicate-action loop.

Search now uses deterministic lexical term matching and ranking. It remains non-semantic and transparent, but behaves more like enterprise search and tolerates paraphrased multi-word queries.

## Runtime reliability improvements

- Ollama preflight verifies server reachability and model installation before an episode.
- `scripts/diagnose.py` separates environment/search problems from Ollama problems.
- Docker Compose starts Ollama, waits for health, pulls the model, runs diagnostics, and launches the benchmark.
- A persistent Docker volume avoids re-pulling the model on every run.
- `OLLAMA_BASE_URL` supports host and container deployments.

## Consistency fixes

- Documentation is aligned to the actually shipped Ollama-only provider path.
- Task manifests now use the runtime `*_v2` task IDs and horizons.
- Automated manifest/runtime consistency coverage was added.
- The suite now validates 23 tests after the added regressions.

## Highest-value next improvements

1. **Make the factory real, not mostly conceptual.** Generate task instances from typed templates: roles, objects, constraints, distractor density, dependency depth, and verifier parameters. Export each generated episode as a manifest.
2. **Add a fifth/sixth app with artifact state.** A lightweight Sheets/Docs or Figma-like simulator would demonstrate that the architecture generalizes beyond communication + ticketing apps. A launch task could require editing a readiness sheet or design approval artifact.
3. **Add counterfactual/adversarial task variants.** Examples: stale Slack guidance contradicts Jira; duplicate customer names; manager approval arrives before engineering validation but should not unlock completion; calendar has timezone ambiguity.
4. **Add policy-independent solvability search.** Instead of only a hand-written rule policy, use bounded state-space/planner checks on generated scenarios to prove at least one valid completion path.
5. **Separate train/eval scenario distributions.** Hold out entity names, wording templates, dependency structures, and distractor regimes to measure generalization rather than memorization.
6. **Add intervention metrics.** Track permission violations attempted, unsupported assumptions, handoff quality, state regressions, and irreversible-action errors—not only final success.
7. **Add snapshot/replay.** Serialize DB + RNG + task manifest at any step so a researcher can branch the same partial trajectory across policies.
8. **Add model matrix automation.** Run 3B/7B/other local models across fixed seeds and emit a comparison report with confidence intervals.
9. **Improve the demo UI.** Show app panes plus a verifier/evaluator pane side-by-side, with hidden state visibly marked as evaluator-only. This makes the separation of observation and scoring obvious in the demo video.
10. **Presentation positioning.** Lead with the research questions this environment can answer: coordination, tool-use reliability, long-horizon credit assignment, permission-aware behavior, and generalization under controlled difficulty scaling.

## Submission risks still requiring a human

- The development prompt trace must be the genuine Claude Code/Cursor history; it should not be synthesized.
- The Google Slides deck still needs visual design and final narrative polish.
- A live Ollama run should be executed on the submission machine and the resulting metrics captured honestly.
- The GitHub repository and demo video must be produced/uploaded outside this code bundle.
