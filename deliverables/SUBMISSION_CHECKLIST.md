# Submission Checklist — Enterprise MARL Benchmark v1.2

## Repository

- [x] Working multi-agent environment (Gymnasium-compatible)
- [x] Experimental PettingZoo AEC compatibility layer (`wrappers/pettingzoo_aec.py`)
- [x] Gmail, Slack, Jira, Calendar, Sheets simulators
- [x] Shared SQLite company state (in-memory, reset-on-seed)
- [x] Partial observations (role-filtered, app-scoped)
- [x] Role-based permissions (5 agents × 5 apps, sheet-level RBAC)
- [x] 6 long-horizon tasks with dependency-gated subgoal DAGs
- [x] vendor_onboarding with genuine parallel branches (legal ∥ IT)
- [x] ScenarioFactory with 4 difficulty levels + realistic distractor injection
- [x] Deterministic verification (state-based, not LLM judge)
- [x] Negation-hardened verifiers (clause-boundary-aware `_affirms()`)
- [x] Shaped reward with anti-hacking logic (redundant action penalty)
- [x] Random baseline (0% → lower bound confirmed)
- [x] Oracle / deterministic baseline (100% → upper bound confirmed)
- [x] Hint-guided LLM baseline (93% overall — validates reward and DAGs)
- [x] Zero-shot LLM measured (0% on qwen2.5:3b — establishes capability gap)
- [x] LLM benchmark harness (Ollama, Gemini, Groq, Qwen, Anthropic)
- [x] Centralized/decentralized LLM control modes
- [x] `--no-hints` flag for zero-shot vs hint-guided ablation
- [x] Wilson 95% CI metrics + failure taxonomy
- [x] Reward ablation runner (shaped vs sparse)
- [x] Trajectory HTML exporter + JSON replay
- [x] Streamlit dashboard UI (port 8501)
- [x] Docker Compose (ollama + benchmark + ui services)
- [x] **70 passing tests, 0 flaky**
- [x] `.gitignore`, `requirements.txt`, `pyproject.toml`
- [x] Academic policy justification (`docs/policy_design.md`)
- [x] Evaluator/agent info separation (`info["eval"]` for evaluator, top-level for agent)

## Benchmark Results (in benchmark_results/)

- [x] `baselines.json` — oracle baseline (100%) + random baseline (0%)
- [x] `difficulty_results.json` — all 6 tasks × 4 difficulty levels
- [x] `llm_results_5ep.json` — hint-guided LLM (93% overall, 5 ep/task)
- [x] `llm_results_zeroshot.json` — zero-shot LLM (0% across all tasks, 1 ep/task)
- [x] `comparison_hint_vs_zeroshot.json` — side-by-side comparison
- [x] `reward_ablation.json` — shaped vs sparse reward comparison
- [x] `customer_incident_trajectory.html` — sample HTML trajectory viewer
- [x] `launch_readiness_episode.json` — replay-verified episode

## Human-facing deliverables

- [x] `deliverables/PRESENTATION_CONTENT.md` — 18 slides, Section 1 (Environment) + Section 2 (Factory)
- [x] `deliverables/DEMO_SCRIPT.md` — 4–6 min demo with exact working commands
- [x] `deliverables/PROMPT_TRACE_NOTE.md` — instructions for exporting genuine development prompt trace
- [x] Pushed to GitHub (`https://github.com/Gourang5/enterprise-marl-benchmark`)

## Remaining manual actions

- [ ] Export genuine Claude Code / Cursor prompt history from your account
      and place in `deliverables/development_prompt_trace.md`
- [ ] Copy PRESENTATION_CONTENT.md into Google Slides and add visuals
      (architecture diagram, DAG flowchart, results bar chart)
- [ ] Record a 4–6 min demo video using DEMO_SCRIPT.md commands
- [ ] Verify GitHub repository is publicly accessible from a clean browser

## Demo Video Commands (exact, confirmed working)

```bash
# 1. Show tests passing
python -m pytest tests/ -v
# → 70 passed

# 2. Run oracle baseline
python scripts/run_benchmark.py --task all --episodes 10
# → 100% on all 6 tasks

# 3. Export trajectory
python scripts/export_trajectory.py --task customer_incident --seed 42
# → open benchmark_results/customer_incident_trajectory.html

# 4. ScenarioFactory demo
python scripts/generate_dataset.py --output generated_scenarios --train 20 --dev 5 --test 10

# 5. Show hint vs zero-shot gap
python scripts/compare_hint_vs_zeroshot.py

# 6. Streamlit dashboard (optional)
streamlit run ui/app.py
```
