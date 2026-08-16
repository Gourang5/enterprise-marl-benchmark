# Presentation content

## Section 1 — The Environment

### Slide 1 — Enterprise work is a multi-agent, multi-app problem
Enterprise workflows are not single-turn tool calls. State and responsibility move across employees, applications, permissions, and time. The benchmark tests whether agents can discover information, coordinate, respect permissions, and reach a verifiable business outcome.

### Slide 2 — Environment thesis
One consistent synthetic Fortune 500 company world is exposed through five thin application simulators: Gmail, Slack, Jira, Calendar, and Sheets. The database is the source of truth; application tools are controlled interfaces over that state.

### Slide 3 — Architecture
Policy/controller → role-filtered observation → semantic tool action → app simulator → shared SQLite state → verifier/reward → next observation. Evaluator-only state is separated from agent-visible state.

### Slide 4 — Multi-agent design
Five heterogeneous roles: Project Manager, Engineer, Product Manager, Engineering Manager, Customer Success. Permissions and app visibility differ by role. Centralized and decentralized LLM-control modes expose different coordination difficulty.

### Slide 5 — Long-horizon task design
Four tasks test different capabilities: P0 incident response, launch go/no-go, scheduling conflict resolution, and cross-team launch readiness across all five apps. Tasks use dependency DAGs, distractors, cross-app state persistence, and deterministic state-based success conditions.

### Slide 6 — Reward and verification
Reward progress and useful state transitions rather than app usage. Penalize invalid/redundant actions and timeouts. Final success is a deterministic function of required state, not similarity to a reference trajectory.

### Slide 7 — Evaluation
Report task success, 95% confidence interval, steps, reward, progress, timeouts, invalid action rate, repeated actions, LLM calls, tokens, and latency. Rule baselines establish solvability; random policies establish a floor; LLM policies measure actual agent capability. The submission uses local Ollama and includes a reproducible Docker Compose path, so the benchmark does not depend on paid model APIs.

### Slide 8 — Demo trajectory
Show one incident episode step-by-step in the trajectory viewer: search customer email → inspect incident → assign engineer → Slack handoff → engineering investigation → review event → resolution → customer-success update.

## Section 2 — The Factory

### Slide 9 — From one benchmark to an environment factory
Implemented ScenarioFactory + seeded fixture generation + difficulty-specific distractor injection + task DAG + deterministic verifier + train/dev/test blueprint exporter + replay + benchmark runner.

### Slide 10 — Validation gates
Generated episodes start unsolved, have acyclic dependency graphs, use deterministic seeds, export disjoint train/dev/test manifests, and can be replayed from recorded trajectories. Rule baselines act as shipped solvability oracles.

### Slide 11 — Scaling dimensions
Agents, apps, horizon, dependency depth, distractor density, permission asymmetry, information fragmentation, and task family can all become configuration axes.

### Slide 12 — Why a researcher would buy it
Reproducibility, inspectable/replayable trajectories, objective verification, five-app multi-agent coordination, failure taxonomy, local-model evaluation, and implemented train/dev/test scenario production rather than only handcrafted demos.
