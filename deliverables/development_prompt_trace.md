# Development Prompt Trace - Enterprise MARL Benchmark
### Gourang Gosavi | AI Engineer | Turing
> Reconstructed log of AI-assisted development sessions across Claude, GPT-4, Cursor, and Gemini.
> Sessions were done in temporary/incognito chats so original logs are lost - this is a representative
> trace reflecting the actual decisions, iterations, and technical choices made during the build.

---

## Phase 1 - Environment Architecture Design

**Prompt:**
> ok so I want to build a multi agent RL benchmark for enterprise workflows. background is I've been
> building OpenAI Gym environments at Turing, both UI and non-UI types so I have decent experience with
> the gym interface. the idea I have is 5 agents each with a different enterprise role like PM, engineer,
> product manager, engineering manager, customer success. they all operate across Gmail Slack Jira Calendar
> and Sheets simultaneously and need to complete long horizon tasks that actually require real coordination
> between them not just parallel independent work. what should the core architecture look like? I'm
> thinking SQLite but not sure if that's overkill for a benchmark

**AI Response (summarised):**
Suggested SQLite as the shared source of truth with thin app simulator modules on top,
role-filtered observations per agent, and a Gymnasium-compatible step/reset API. Agreed
SQLite was the right call over in-memory dicts for realistic query patterns.

---

**Prompt:**
> right ok but I don't want agents sharing global state directly - each agent should only see
> what their role actually allows. like a PM shouldnt see an engineers private calendar and
> an engineer shouldnt be able to write to the vendor tracker sheet. how do i enforce this at
> the observation layer without hardcoding a giant if-else for every agent

**AI Response (summarised):**
Proposed a `CompanyRepository` layer that filters all queries by `agent_id` and `role`,
plus a `seed_company()` function that bootstraps the SQLite state fresh at each reset.

---

**Prompt:**
> ok makes sense. one more thing, the verifier that checks if a task is done should NEVER
> expose its internal state to the agents. this was actually a problem I ran into before at
> turing where the policy could somehow read the success signal it shouldnt have access to and
> it was gaming it. how do i properly separate evaluator state from what the agent sees in the
> info dict

**AI Response (summarised):**
Recommended putting all evaluator data (`progress`, `subgoals`, `reward_components`) under
`info["eval"]`, keeping only `success`, `message`, and `step` at the top-level `info` dict.

---

**Prompt:**
> perfect thats exactly what i wanted. now the task structure - I want dependency gated subgoals
> basically a DAG where later steps are completely blocked until earlier ones complete. the challenge
> is doing this cleanly without making each task implementation a mess of nested conditionals.
> whats the cleanest way to represent and check this

**AI Response (summarised):**
Proposed a `subgoals` list with explicit `depends_on` fields per subgoal entry, and a
`verify_subgoal()` method that checks dependency state before evaluating the DB predicate.

---

## Phase 2 - Task Design

**Prompt:**
> I want to design 6 tasks total. each one should be testing something different and measurable,
> not just "complete a workflow" but specific research properties like constraint satisfaction,
> role based permission asymmetry, parallel prerequisites that need an AND join, etc.
> can you give me a framework for thinking about task diversity so I dont end up with 6
> tasks that all test basically the same thing

**AI Response (summarised):**
Listed research axes: retrieval difficulty, role asymmetry, parallel branch joins, RBAC enforcement,
private information handoff, and dependency depth. Recommended mapping each task to 2-3 distinct axes.

---

**Prompt:**
> ok let me spec out vendor onboarding, this is the most complex one. so a new vendor needs to be
> onboarded end to end. legal has to clear a contract ticket, IT has to confirm provisioning, then
> the manager can only approve AFTER both of those are done (this is the parallel prereq I want).
> then PM has to update a spreadsheet to mark the vendor active and only the PM has write access to
> that sheet not anyone else. then kickoff gets scheduled in calendar and finally theres a slack
> announcement. I need the subgoal DAG for this - make sure the legal and IT steps are truly parallel
> prereqs and both are required before manager approval can fire

**AI Response (summarised):**
Designed the 8-subgoal DAG: `discover_email` → `find_ticket` → (`legal_review` in parallel with
`it_provisioning`) → `manager_approval` → `update_sheet` → `schedule_kickoff` → `announce`.
Flagged that the parallel branch needs an explicit AND-join predicate before `manager_approval`.

---

**Prompt:**
> the sheet write permission is really important here. i've seen other benchmarks where any agent
> can write anything and the evaluator just checks what was written not who wrote it. i need the
> verifier to check BOTH - what was written AND that it was specifically pm_01 who wrote it,
> not product_01 masquerading as the PM. how do i track writer identity at the DB level

**AI Response (summarised):**
Added `writer_id` column to the `spreadsheets` table and updated the verifier predicate to check
`repo.sheet_cell(sheet_id, cell_ref).writer_id == "pm_01"`.

---

**Prompt:**
> now the slack message verifier - needs to be negation aware. so "vendor is NOT approved" should
> fail but "approved with no further action required" should pass. simple keyword matching wont handle
> this, ive tried that before and it breaks on edge cases. what approach actually handles the
> negation correctly at the clause boundary level

**AI Response (summarised):**
Proposed a clause-boundary-aware `_affirms(text, keyword)` function that splits on punctuation
and negation markers, checking whether the keyword appears in a non-negated clause.

---

**Prompt:**
> ok test case: "Not only approved, but fully signed off." - does this pass or fail?

**AI Response (summarised):**
Identified that "Not only" is an intensifier, not a negation of "approved". Fixed the clause
detection logic to recognise "not only X but Y" as an affirmation pattern.

---

**Prompt:**
> and "This has not been approved yet" - fail?

**AI Response (summarised):**
Confirmed it fails correctly. "not been approved" is a direct pre-keyword negation caught by
the negation marker scan before the keyword.

---

## Phase 3 - Reward Function

**Prompt:**
> reward design time. I need shaped reward not just sparse terminal because from my RLHF work i know
> sparse reward is extremely hard to learn from in long horizon tasks especially when you have 8+ subgoals.
> but I also need to specifically prevent reward hacking because agents will find ways to farm it.
> the specific case I'm worried about is an agent just reading the same email over and over and getting
> rewarded each time because it's technically a valid tool call. design the full reward component breakdown
> and make sure the anti hacking piece is solid

**AI Response (summarised):**
Proposed: `subgoal_progress_reward` (new subgoal unlocked), `useful_action_reward` (state change occurred),
`coordination_bonus` (cross-agent handoff), `terminal_success_bonus`, `step_cost` (small negative),
`redundant_action_penalty` (repeated read with no state change), `invalid_action_penalty`.

---

**Prompt:**
> the redundant action thing - I dont want to penalize an agent for reading something it already read
> once if there's been meaningful progress since then. only penalize truly pointless repeated reads
> with zero state change in between. how do i track that efficiently without adding a lot of overhead
> to the episode state

**AI Response (summarised):**
Suggested tracking `(agent_id, action_type, key_param)` tuples in episode state, penalising only
when the exact same tuple recurs with no intervening state change since its last occurrence.

---

**Prompt:**
> and for the baseline policies i need 4 tiers. oracle which is scripted and deterministic and
> should get 100%, hint guided LLM which gets the ticket IDs and SOPs directly in context,
> zero shot LLM with no hints just the task description, and random. the oracle needs to actually
> be a proper scripted policy not just hardcoded step sequences - it should be readable and
> maintainable. build the oracle for vendor onboarding

**AI Response (summarised):**
Wrote `VendorOnboardingBaseline(ScriptedPolicy)` with a 10-step sequence keyed to entity IDs
(`vendor-request-001`, `VEND-401/402/403`, `SHEET-VENDOR`, `CH-PROCUREMENT`), covering all
5 agents in correct dependency order with an internal step counter.

---

## Phase 4 - LLM Evaluation Harness

**Prompt:**
> i want to actually benchmark LLMs against this environment. at turing ive run LLM eval pipelines
> before and i know the failure modes - model tries an action with completely wrong parameter format,
> or it gets stuck in a loop querying the same thing. how do i handle these robustly so the benchmark
> doesnt just crash when the model does something dumb

**AI Response (summarised):**
Designed a 6-attempt retry loop with strict JSON schema validation before `env.step()`,
cyclic and exact duplicate action detection, and a `policy_error` flag on failure rather than
raising an exception.

---

**Prompt:**
> also I want to support multiple providers not just one. I'm thinking Ollama for local testing
> with no api key needed, Gemini free tier, Groq which is really fast, Qwen via DashScope, and
> Anthropic. they all need to sit behind the same interface so I can swap them with a flag.
> also add a --no-hints flag so I can run the same benchmark in zero shot vs hint guided mode
> and compare directly

**AI Response (summarised):**
Built a `make_client(provider, model, api_key)` factory returning objects with a common `chat(messages)`
interface, plus a `no_hints` parameter in `run_llm_episode()` that strips SOP context from the prompt.

---

**Prompt:**
> failure taxonomy needs to be more granular. in my skillsbench work at turing we categorized failures
> into types so we could actually diagnose what was wrong and fix the right thing rather than just knowing
> the episode failed. I want these categories: looping, retrieval failure, permission violation, constraint
> violation, tool use failure, policy failure, horizon failure. add this breakdown to every episode result
> so i can slice the failures properly

**AI Response (summarised):**
Added `failure_taxonomy` dict to episode results, populated from action error types and detection
patterns accumulated during the episode loop.

---

## Phase 5 - ScenarioFactory

**Prompt:**
> I need a factory that generates reproducible training datasets. similar in spirit to what we
> use for data generation in skillsbench at turing. specifically I need train/dev/test splits where
> seeds are completely disjoint across splits so a model can never see a training seed at test time.
> difficulty levels that inject different numbers of distractor emails and jira tickets to vary
> retrieval difficulty. and a manifest file that validates every generated scenario before it goes
> into the dataset. can you design this

**AI Response (summarised):**
Built `ScenarioFactory` with `easy/medium/hard/adversarial` distractor presets (2/6/15/30 distractors),
`blueprint()` for individual scenario metadata, and `generate_manifest()` for dataset-level JSON
with seed-disjoint range enforcement across splits.

---

**Prompt:**
> validator needs to be strict. three things it must check: one, scenario starts at zero progress
> so there are no free subgoals at reset time. two, the dependency graph is actually acyclic because
> a cyclic DAG would make it unsolvable. three, all dependency IDs in each subgoal resolve to real
> subgoal names in that same task. if any of those fail reject it at generation time not at training
> time where its too late

**AI Response (summarised):**
Added three validation checks: initial progress via `env.reset()` + `info["eval"]["progress"]`,
topological sort for DAG cycle detection, and dependency ID resolution against the subgoal name set.

---

## Phase 6 - factory_v2: Generated Worlds

**Prompt:**
> i realized a pretty fundamental problem with ScenarioFactory. the entity IDs are fixed across seeds -
> VEND-401 is always VEND-401, TechNova Solutions is always TechNova Solutions, Aisha Patel is always
> Aisha Patel. a policy trained on enough episodes could just memorize those IDs and cheat without
> actually learning the workflow. I need a second layer that generates completely different employee
> names emails vendor names and ticket IDs for each seed. the key constraint is it absolutely cannot
> break the existing static environment - these need to live in separate modules with zero shared state

**AI Response (summarised):**
Proposed `factory_v2` as a completely separate module at `src/enterprise_env/factory_v2/` with its
own `CompanySpec` dataclass, isolated `WorldGenerator`, and `GeneratedVendorOnboardingTask` that
overrides static setup. Zero changes to existing files required.

---

**Prompt:**
> the RNG isolation is critical, this is non negotiable. I've had actual bugs at turing where a generator
> was calling random.random() globally and it was polluting the RNG state of other tests and making
> them nondeterministic in ways that were really hard to debug. the factory_v2 world generator needs
> its own seeded RNG instance and must NEVER touch random.random() numpy.random or any global state

**AI Response (summarised):**
Confirmed `WorldGenerator.__init__` stores `self.rng = random.Random(spec.seed)` and all entity
generation calls use exclusively `self.rng.choice()`, `self.rng.randint()` etc.

---

**Prompt:**
> for the vendor ticket IDs i want the prefix derived from the vendor name so it looks realistic.
> if the vendor is something like "Metrics Solutions" the tickets should be METR-401 METR-402 METR-403,
> four letters from the noun in uppercase. same pattern as real jira project keys

**AI Response (summarised):**
Implemented `prefix = noun[:4].upper()` in `_gen_vendor()`, with ticket IDs as
`f"{prefix}-401"`, `f"{prefix}-402"`, `f"{prefix}-403"`.

---

**Prompt:**
> i also want a SHA-256 fingerprint for each generated world config so i can track exactly which
> world was used in each experiment run. same seed must always produce the exact same fingerprint,
> different seeds must produce different fingerprints always. what should go into the hash and
> what format should the fingerprint string be

**AI Response (summarised):**
Built `compute_fingerprint()` hashing a canonical JSON of: seed, company name, scenario, difficulty,
sorted employee list (agent_id, role, name, email), and vendor identifiers. Returns `sha256:{digest[:16]}`
for readability while still being unique.

---

**Prompt:**
> world validator - i need it to catch: duplicate agent IDs, malformed email addresses, non-unique
> vendor ticket IDs (so you cant have the same ticket for both legal and IT), missing required roles
> for the scenario, missing required permissions per role, and empty vendor entity fields. all of
> this should run at generation time so broken worlds never make it into a dataset or a test

**AI Response (summarised):**
Implemented `WorldValidator` with 5 check methods covering all listed conditions. Also caught a
type bug: initial version used `int in str` to check if seed was in email_id, which raises TypeError.
Fixed to `str(world.spec.seed) not in v.email_id`.

---

**Prompt:**
> oracle also needs to work on generated worlds. the existing oracle uses hardcoded entity IDs like
> VEND-401 and pm_01 but in generated worlds those IDs change per seed. write a GeneratedVendorOnboardingBaseline
> that reads all entity IDs dynamically from the world object at runtime - world.vendor.main_ticket,
> world.employee_by_role("project_manager").agent_id etc. then verify it passes on at least seeds 42 43 99 100 7

**AI Response (summarised):**
Wrote `GeneratedVendorOnboardingBaseline(ScriptedPolicy)` with all 10 steps keyed to `self.world.vendor.*`
and `self.world.employee_by_role(role).agent_id`. Verified oracle passes 100% on all five requested seeds.

---

**Prompt:**
> one issue - when i try to reuse the _episode() function from runner.py to run the generated episode
> it calls make_env() internally which creates the static env not the generated one. i dont want to
> modify runner.py at all because that would risk breaking existing tests. whats the cleanest fix

**AI Response (summarised):**
Inlined the episode loop directly in `factory_v2/__init__.py`'s `run_generated_episode()`, creating
`build_env(world)` and running the policy loop independently. No changes to runner.py.

---

## Phase 7 - Testing Strategy

**Prompt:**
> test suite time. from evaluation pipeline work at turing i know what tests actually matter vs what
> tests just look good. determinism tests are the most important - same seed same output always, no exceptions.
> then diversity tests to confirm different seeds actually produce meaningfully different entities not just
> superficially different ones. validator pass and fail paths both need testing not just the happy path.
> oracle solvability across multiple seeds. and critically a legacy regression test that imports factory_v2
> and then runs the original static environment to make sure the import doesn't break anything via global state
> side effects. structure the test classes around these

**AI Response (summarised):**
Organised 48 tests into 10 classes: `TestDeterminism`, `TestDiversity`, `TestFingerprint`,
`TestValidator`, `TestEmployeeStructure`, `TestVendorStructure`, `TestManifest`,
`TestGeneratedEnvOracle`, `TestCrossAppPropagation`, `TestLegacyRegression`.

---

**Prompt:**
> the cross app propagation tests are important, add those too. they should verify that after
> env.reset() the generated employee names and vendor IDs from the world object actually got
> written to the SQLite DB correctly. so query the DB directly after reset and assert the rows
> match the world object fields

**AI Response (summarised):**
Added `test_employee_names_updated_in_db`, `test_vendor_email_exists_in_db`,
`test_vendor_tickets_exist_in_db`, `test_vendor_sheet_exists_in_db`,
`test_vendor_channel_exists_in_db` - each queries `env.repo.*` after reset and asserts
DB rows match `world.*` fields.

---

**Prompt:**
> run the full suite, want to see 118 passed zero failures zero warnings

**AI Response (summarised):**
All 118 tests pass. Breakdown: 70 original environment tests + 48 factory_v2 tests.
Zero failures, zero warnings across 5 consecutive runs.

---

## Phase 8 - LLM Benchmark Results

**Prompt:**
> run the full benchmark. start with oracle to confirm 100%, then Ollama zero shot no hints across
> all 6 tasks 5 episodes each. I expect zero shot to be very low or zero given the model is small
> (qwen2.5:3b) and the tasks are genuinely hard

**AI Response (summarised):**
Oracle: 100% all 6 tasks, 5 episodes each. Zero-shot (qwen2.5:3b, no hints): 0/30 across all tasks.
Primary failure mode was looping on the same search query and early policy failure. Average progress
was 0-40% depending on task but no episodes completed.

---

**Prompt:**
> now run with hints. this should be much higher - the hint guided result is really just proving
> the task design and reward are correct, not proving the LLM is capable autonomously. I need this
> number to validate the environment not to claim the LLM solved it

**AI Response (summarised):**
Hint-guided (qwen2.5:3b, with SOP context): 24/30 episodes across all tasks (80%). One task
(`launch_readiness`) had model looping at ~38% progress - model capability limitation, not a
benchmark bug. Zero invalid actions, zero permission violations across all tasks.

---

**Prompt:**
> the gap between zero shot (0%) and hint guided (80%) is the core finding and needs to be clearly
> labelled everywhere. hint guided is NOT evidence of autonomous capability its just an SOP following
> check to validate the environment. make sure the results files and README both say this explicitly

**AI Response (summarised):**
Added explicit framing in `baselines.json` and README baseline taxonomy table:
"Hint-guided: SOP-guided debug baseline (hint-injected) - not evidence of autonomous capability."

---

## Phase 9 - Final Architecture Decisions

**Prompt:**
> stepping back and looking at the overall design - do you think SQLite over an in-memory dict was
> actually the right call here? genuinely asking, not looking for validation

**AI Response (summarised):**
Yes for 4 reasons: (1) realistic query patterns via search rather than direct lookup, (2) persistent
cross-agent state without shared memory coupling, (3) easy trajectory inspection and replay via SQL,
(4) clean reset via DROP TABLE + CREATE TABLE + seed_company(). In-memory dict would have needed
custom serialisation for all of this.

---

**Prompt:**
> last thing - the PettingZoo AEC adapter. AEC means only one agent acts per step but our environment
> accepts any agent's action at any step. how does the adapter handle this mismatch without breaking
> the underlying environment

**AI Response (summarised):**
Implemented an experimental adapter where `agent_selection` cycles through all 5 agents but agents
can skip with a no-op if they have nothing to do. The underlying `EnterpriseEnv.step()` still
accepts any agent's action - the AEC wrapper just enforces the sequential API contract on top.

---

*End of development trace - Enterprise MARL Benchmark v1.3*
*Total build time: approx 2 days | Tools used: Claude, GPT-4, Cursor, Gemini*
*Author: Gourang Gosavi | github.com/Gourang5*
