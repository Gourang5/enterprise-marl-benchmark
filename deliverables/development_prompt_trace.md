# Development Prompt Trace — Enterprise MARL Benchmark
### Gourang Gosavi | AI Engineer & RL Specialist | Turing
> Representative log of AI-assisted development sessions across Claude, GPT-4, Cursor, and Gemini.
> Conversations were conducted in temporary/session-only modes across tools; this is a reconstructed
> trace reflecting the actual decisions, iterations, and technical direction of the build.

---

## Phase 1 — Environment Architecture Design

**Prompt:**
> I want to build a multi-agent RL benchmark for enterprise workflows. At Turing I've been building
> OpenAI Gym environments — both UI and Non-UI — and I want to take that further. The idea is:
> 5 agents, each with a different enterprise role (PM, engineer, product manager, engineering manager,
> customer success), operating across Gmail, Slack, Jira, Calendar, and Sheets. They need to complete
> long-horizon tasks that require coordination. What should the core architecture look like?

**AI Response (summarised):**
Suggested a shared SQLite database as the single source of truth, thin app simulators on top,
role-filtered observations per agent, and a Gymnasium-compatible step/reset API.

---

**Prompt:**
> Good. I don't want the agents to share a global state directly — each agent should only see
> what their role allows. A project manager shouldn't see an engineer's private calendar, for example.
> How do I enforce this at the observation level without hardcoding everything?

**AI Response (summarised):**
Proposed a `CompanyRepository` layer that filters queries by `agent_id` and `role`, and a
`seed_company()` function that bootstraps the SQLite state at reset time.

---

**Prompt:**
> Makes sense. One more constraint — the verifier that checks task completion should never expose
> its state to the agents. In my Gym environments at Turing we always had this problem where the
> policy could read success signals it shouldn't have access to. How do I separate evaluator state
> from agent-facing info?

**AI Response (summarised):**
Recommended putting all evaluator-only data (`progress`, `subgoals`, `reward_components`) under
`info["eval"]`, leaving only `success`, `message`, and `step` in the top-level `info` dict.

---

**Prompt:**
> Perfect. That's exactly the kind of separation I wanted. Now let's talk about the task structure.
> I want dependency-gated subgoals — like a DAG where later steps are blocked until earlier ones
> complete. How do I implement this cleanly without making each task a mess of conditional logic?

**AI Response (summarised):**
Proposed a `subgoals` list with explicit `depends_on` fields per subgoal, and a `verify_subgoal()`
method that checks both the dependency state and the database predicate before awarding credit.

---

## Phase 2 — Task Design

**Prompt:**
> I want to design 6 tasks. Each one should exercise a different research property — not just
> "complete the task" but something measurable like constraint satisfaction, permission asymmetry,
> parallel prerequisites, etc. Give me a framework for thinking about task diversity.

**AI Response (summarised):**
Listed research axes: retrieval difficulty, role asymmetry, parallel branches, RBAC enforcement,
private information handoff, and dependency depth. Suggested mapping each task to 2-3 axes.

---

**Prompt:**
> Let me spec out vendor onboarding. A new vendor needs to be onboarded: legal clears a contract
> ticket, IT confirms provisioning, manager approves, PM updates a spreadsheet, kickoff gets
> scheduled, and an announcement goes out. Legal and IT should be parallel prerequisites — manager
> can only approve once both are done. Only the PM can write the vendor tracker sheet.
> Build the subgoal DAG for this.

**AI Response (summarised):**
Designed 8-subgoal DAG: `discover_email` → `find_ticket` → (`legal_review` ∥ `it_provisioning`)
→ `manager_approval` → `update_sheet` → `schedule_kickoff` → `announce`. Noted that the parallel
branch needs an AND-join before `manager_approval`.

---

**Prompt:**
> The sheet write permission is critical. At Turing I've seen benchmarks where any agent can write
> anything and the reward function doesn't catch it. I need the verifier to check not just WHAT
> was written but WHO wrote it. How do I implement that?

**AI Response (summarised):**
Added `writer_id` tracking to the `spreadsheets` table and updated the verifier predicate to check
`repo.sheet_cell(sheet_id, cell_ref).writer_id == "pm_01"`.

---

**Prompt:**
> Good. Now the verifier for Slack messages — I need it to be negation-aware. A message saying
> "vendor is NOT approved" should fail, but "approved with no further action required" should pass.
> Simple keyword matching won't handle this. What's the right approach?

**AI Response (summarised):**
Proposed a clause-boundary-aware `_affirms(text, keyword)` function that splits on punctuation
and negation markers, then checks whether the keyword appears in a non-negated clause.

---

**Prompt:**
> Let me test that. What about: "Not only approved, but fully signed off." — does it pass?

**AI Response (summarised):**
Identified that "Not only" is an intensifier, not a negation of "approved" — the function needed
to recognise "not only X but Y" as an affirmation pattern. Fixed the clause detection logic.

---

**Prompt:**
> And "This has not been approved yet" — does that correctly fail?

**AI Response (summarised):**
Confirmed it fails correctly — "not been approved" is a direct pre-keyword negation caught by
the negation marker scan.

---

## Phase 3 — Reward Function

**Prompt:**
> I need a shaped reward, not just sparse terminal reward. From my RLHF work I know sparse reward
> is hard to learn from in long-horizon tasks. But I also need to prevent reward hacking — agents
> shouldn't be able to farm reward by just reading the same email over and over.
> Design the reward components.

**AI Response (summarised):**
Proposed: `subgoal_progress_reward` (unlocking new subgoal), `useful_action_reward` (state change),
`coordination_bonus` (cross-agent handoff), `terminal_success_bonus`, `step_cost` (small negative),
`redundant_action_penalty` (repeated read with no state change), `invalid_action_penalty`.

---

**Prompt:**
> The redundant action penalty is important. But I don't want to penalise agents for reading
> something once that they already read — only for pointless repeated reads with zero progress.
> How do I track that without adding too much overhead?

**AI Response (summarised):**
Suggested tracking `(agent_id, action_type, key_param)` tuples in episode state, penalising
only when the exact same tuple appears with no intervening state change.

---

**Prompt:**
> Good. Now for the baseline policies — I need four tiers. Oracle (scripted, 100%), hint-guided LLM
> (gets ticket IDs and SOPs in context), zero-shot LLM (no hints), and random. The oracle needs to
> be a proper scripted policy, not just hardcoded actions. Build the oracle for vendor onboarding.

**AI Response (summarised):**
Wrote a `VendorOnboardingBaseline(ScriptedPolicy)` with a 10-step sequence keyed to hardcoded
entity IDs (`vendor-request-001`, `VEND-401`, `VEND-402`, `VEND-403`, `SHEET-VENDOR`,
`CH-PROCUREMENT`), covering all 5 agents in correct dependency order.

---

## Phase 4 — LLM Evaluation Harness

**Prompt:**
> I want to benchmark actual LLMs against this environment. At Turing I've run LLM eval pipelines
> before — I know the key failure modes: the model tries an action with wrong parameters, or it
> loops on the same search query. How do I handle these robustly without the benchmark crashing?

**AI Response (summarised):**
Designed a 6-attempt retry loop with: strict JSON schema validation before `env.step()`,
cyclic/exact duplicate action detection, and a `policy_error` flag on failure rather than
an exception crash.

---

**Prompt:**
> I also want to support multiple providers — not just OpenAI. I'm thinking Ollama locally,
> Gemini free tier, Groq, Qwen via DashScope, and Anthropic. Abstract them behind a common
> client interface. Also add a `--no-hints` flag so I can compare zero-shot vs hint-guided.

**AI Response (summarised):**
Built a `make_client(provider, model, api_key)` factory with a common `chat(messages)` interface,
and a `no_hints` parameter in `run_llm_episode()` that strips the SOP context from the prompt.

---

**Prompt:**
> The failure taxonomy needs to be more granular. In my SkillsBench work at Turing we categorised
> failures into types so we could fix the right thing. I want: looping, retrieval failure,
> permission violation, constraint violation, tool use failure, policy failure, and horizon failure.
> Add this to the episode result.

**AI Response (summarised):**
Added `failure_taxonomy` dict to episode results, populated from action error types and
detection patterns during the episode loop.

---

## Phase 5 — ScenarioFactory

**Prompt:**
> I need a factory that can generate reproducible training datasets. Think train/dev/test splits
> with seed-disjoint episodes, difficulty levels that inject different numbers of distractor
> emails and Jira tickets, and a manifest file that validates each generated scenario.
> Similar to what we'd use for SkillsBench data generation at Turing.

**AI Response (summarised):**
Built `ScenarioFactory` with `easy/medium/hard/adversarial` distractor presets (3/6/15/30),
`blueprint()` for individual scenario metadata, and `generate_manifest()` for dataset-level
JSON with seed-disjoint split enforcement.

---

**Prompt:**
> The validator needs to be strict. Every generated scenario must: start at zero progress
> (no free initial subgoals), have an acyclic dependency graph, and have all dependency IDs
> resolve to real subgoal names. If any of these fail, the scenario should be rejected at
> generation time, not at training time.

**AI Response (summarised):**
Added three validation checks: initial progress check via `env.reset()` + `info["eval"]["progress"]`,
topological sort for cycle detection, and dependency ID resolution against the subgoal name set.

---

## Phase 6 — factory_v2: Generated Worlds

**Prompt:**
> I realised a problem with ScenarioFactory. The entity IDs are fixed — VEND-401, TechNova Solutions,
> Aisha Patel — they never change between seeds. A policy trained on this could memorise the IDs
> rather than learning the workflow. I want a second factory layer that generates completely different
> employee names, emails, vendor names, and ticket IDs per seed. How do I design this without
> breaking the existing static environment?

**AI Response (summarised):**
Proposed `factory_v2` as a completely separate module (`src/enterprise_env/factory_v2/`) with its
own `CompanySpec` dataclass, `WorldGenerator` using an isolated `random.Random(seed)`, and
`GeneratedVendorOnboardingTask` that overrides the static setup. Zero changes to existing files.

---

**Prompt:**
> The RNG isolation is important — I've had bugs at Turing where a generator polluted global
> random state and made other tests non-deterministic. Make sure the factory_v2 world generator
> uses its own seeded RNG instance, never `random.random()` or `numpy.random`.

**AI Response (summarised):**
Confirmed `WorldGenerator.__init__` stores `self.rng = random.Random(spec.seed)` and all
entity generation calls use `self.rng.choice()`, `self.rng.randint()` etc. — never global state.

---

**Prompt:**
> Good. Now the vendor ticket IDs — I want the prefix to be derived from the vendor name so it
> looks realistic. Like if the vendor is "Metrics Solutions", the tickets should be METR-401,
> METR-402, METR-403. Four letters from the noun, uppercase.

**AI Response (summarised):**
Implemented `prefix = noun[:4].upper()` in `_gen_vendor()`, with `main_ticket = f"{prefix}-401"`,
`legal_ticket = f"{prefix}-402"`, `it_ticket = f"{prefix}-403"`.

---

**Prompt:**
> I also want a SHA-256 fingerprint for each generated world so I can track exactly which world
> configuration was used in each experiment. Same seed should always give the same fingerprint,
> different seed should always give different. What goes into the hash?

**AI Response (summarised):**
Built `compute_fingerprint()` hashing a canonical JSON of: seed, company name, scenario,
difficulty, sorted employee list (agent_id, role, name, email), and vendor identifiers.
Returns `sha256:{digest[:16]}` for readability.

---

**Prompt:**
> The world validator — I need it to catch: duplicate agent IDs, malformed emails, non-unique
> vendor tickets, missing required roles for the scenario, missing required permissions per role,
> and empty vendor entity fields. Run this at generation time so bad worlds never get used.

**AI Response (summarised):**
Implemented `WorldValidator` with 5 check methods covering all listed conditions. Also caught
a bug: `seed` is an int but `email_id` is a string, so `str(world.spec.seed) not in v.email_id`
was needed — the initial version used `int in str` which raises a TypeError.

---

**Prompt:**
> I need the oracle to work on generated worlds too. But the existing oracle uses hardcoded IDs.
> Write a `GeneratedVendorOnboardingBaseline` that reads entity IDs from the world object —
> `world.vendor.main_ticket`, `world.employee_by_role("project_manager").agent_id`, etc.

**AI Response (summarised):**
Wrote `GeneratedVendorOnboardingBaseline(ScriptedPolicy)` with 10 steps all keyed to
`self.world.vendor.*` and `self.world.employee_by_role(role).agent_id`. Verified oracle
passes 100% on seeds 42, 43, 99, 100, 7.

---

**Prompt:**
> One issue — I tried to reuse the `_episode()` function from runner.py to run the generated
> episode, but it calls `make_env()` internally which creates a static env, not a generated one.
> I don't want to modify runner.py. What's the cleanest fix?

**AI Response (summarised):**
Inlined the episode loop directly in `factory_v2/__init__.py`'s `run_generated_episode()` —
creates `build_env(world)`, resets with `world.spec.seed`, runs the policy loop, collects
trajectory. No changes to runner.py.

---

## Phase 7 — Testing Strategy

**Prompt:**
> I want a comprehensive test suite. From my evaluation pipeline work at Turing I know what
> actually matters: determinism tests (same seed → same output), diversity tests (different seeds →
> different entities), validator pass/fail paths, oracle solvability across multiple seeds,
> and legacy regression (factory_v2 import must not break the static environment).
> Structure the test classes.

**AI Response (summarised):**
Organised 48 tests into 10 classes: `TestDeterminism`, `TestDiversity`, `TestFingerprint`,
`TestValidator`, `TestEmployeeStructure`, `TestVendorStructure`, `TestManifest`,
`TestGeneratedEnvOracle`, `TestCrossAppPropagation`, `TestLegacyRegression`.

---

**Prompt:**
> The cross-app propagation tests are important — they verify that when `GeneratedVendorOnboardingTask.setup()`
> runs, the generated employee names and vendor IDs actually got written to the SQLite database.
> Add tests that query the DB after `env.reset()` and check the rows match the world object.

**AI Response (summarised):**
Added `test_employee_names_updated_in_db`, `test_vendor_email_exists_in_db`,
`test_vendor_tickets_exist_in_db`, `test_vendor_sheet_exists_in_db`,
`test_vendor_channel_exists_in_db` — each calls `env.repo.*` after reset and asserts
the DB row matches `world.*`.

---

**Prompt:**
> Run the full test suite. I want to see 118 passed, zero failures, zero warnings.

**AI Response (summarised):**
All 118 tests pass. Breakdown: 70 original environment tests + 48 factory_v2 tests.
Zero failures, zero warnings, zero flaky tests across 5 runs.

---

## Phase 8 — LLM Benchmark Results

**Prompt:**
> Run the full benchmark. Oracle first, then Ollama zero-shot no hints across all 6 tasks,
> 5 episodes each. I want to see the four-tier taxonomy numbers: oracle ~100%, zero-shot near 0%.

**AI Response (summarised):**
Oracle: 100% all 6 tasks, 5 episodes. Zero-shot (qwen2.5:3b, no hints): 0% all 6 tasks,
5 episodes. Primary failure mode: looping (repeated same query) and early policy failure.
Average progress: 0-40% depending on task — partial progress but no completions.

---

**Prompt:**
> Now run with hints. I expect much higher success — the hint-guided baseline should prove the
> task and reward design are correct, even if the zero-shot LLM can't solve it autonomously.

**AI Response (summarised):**
Hint-guided (qwen2.5:3b, with SOP context): 5/6 tasks pass, ~83% overall.
`launch_readiness` fails due to model looping at 38% progress — model capability limitation,
not a benchmark bug. Zero invalid actions, zero permission violations across all tasks.

---

**Prompt:**
> The gap between zero-shot (0%) and hint-guided (83%) is the core research finding.
> Make sure this is clearly labelled in the results — hint-guided is NOT evidence of autonomous
> capability, it's an SOP-following check. The meaningful number for autonomous agent research
> is the zero-shot number.

**AI Response (summarised):**
Added explicit labelling in `baselines.json` and `README.md` baseline taxonomy table:
"Hint-guided: SOP-guided debug baseline (hint-injected) — not evidence of autonomous capability."

---

## Phase 9 — Final Architecture Decisions

**Prompt:**
> Looking at the overall design — do you think the decision to use SQLite over an in-memory dict
> was the right call for this kind of benchmark?

**AI Response (summarised):**
Yes — SQLite enables: (1) realistic query patterns via search rather than direct lookup,
(2) persistent cross-agent state without shared memory, (3) easy trajectory inspection and
replay via SQL queries, (4) consistent reset via `DROP TABLE / CREATE TABLE` + `seed_company()`.
An in-memory dict would have required custom serialisation for all of these.

---

**Prompt:**
> One last thing — the PettingZoo AEC adapter. I've seen people try to hook Gym environments
> into PettingZoo and get the turn order wrong. In AEC, only one agent acts per step.
> How does that map to our multi-agent setup where any agent can act?

**AI Response (summarised):**
Implemented an experimental adapter where `agent_selection` cycles through the 5 agents,
but agents can skip their turn with a no-op if they have nothing to do. The underlying
`EnterpriseEnv.step()` still accepts any agent's action — the AEC wrapper just enforces
the sequential API contract on top.

---

*End of development trace — Enterprise MARL Benchmark v1.3*
*Total development time: ~2 days | Tools used: Claude Code, GPT-4, Cursor, Gemini*
*Author: Gourang Gosavi | github.com/Gourang5*
