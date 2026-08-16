# Submission Checklist — Enterprise MARL Benchmark v1.2

## Repository (all done)
- [x] Working multi-agent environment (PettingZoo AEC interface)
- [x] Gmail, Slack, Jira, Calendar, Sheets simulators
- [x] Shared SQLite company state (in-memory, reset-on-seed)
- [x] Partial observations (role-filtered, app-scoped)
- [x] Role-based permissions (5 agents × 5 apps)
- [x] 6 long-horizon tasks with dependency DAGs
- [x] vendor_onboarding with genuine parallel branches (legal ∥ IT)
- [x] ScenarioFactory with 4 difficulty levels + distractor injection
- [x] Deterministic verification (state-based, not LLM judge)
- [x] Shaped reward with anti-hacking logic
- [x] Random baseline (0% → lower bound)
- [x] Deterministic/oracle baseline (100% → upper bound)
- [x] LLM benchmark harness (Ollama, Gemini, Groq, Qwen, Anthropic)
- [x] Centralized/decentralized LLM control modes
- [x] --no-hints flag for zero-shot vs hint-guided ablation
- [x] Wilson 95% CI metrics + failure taxonomy
- [x] Reward ablation runner (shaped vs sparse)
- [x] Trajectory HTML exporter + replay
- [x] Streamlit dashboard UI (port 8501)
- [x] PettingZoo AEC adapter (pettingzoo_aec.py)
- [x] Docker Compose (ollama + benchmark + ui services)
- [x] 34 passing tests, 0 flaky
- [x] .gitignore, requirements.txt, pyproject.toml
- [x] Academic policy justification (docs/policy_design.md)

## Benchmark Results (in benchmark_results/)
- [x] baselines.json — oracle baseline (100% all tasks)
- [x] difficulty_results.json — all 6 tasks × 4 difficulty levels
- [x] llm_results_5ep.json — hint-guided LLM, 5 episodes per task
- [x] reward_ablation.json — shaped vs sparse reward comparison
- [ ] llm_results_zeroshot.json — zero-shot comparison (running now)
- [ ] comparison_hint_vs_zeroshot.json — side-by-side table

## Human-facing deliverables
- [x] deliverables/PRESENTATION_CONTENT.md — updated with 6th task + policy taxonomy
- [x] deliverables/DEMO_SCRIPT.md — step-by-step demo instructions
- [ ] Push to GitHub (`git remote add origin <URL> && git push -u origin master`)
- [ ] Record demo video using DEMO_SCRIPT.md
- [ ] Copy PRESENTATION_CONTENT.md into Google Slides + add visuals
- [ ] Verify GitHub URL from a clean machine

## GitHub Push Commands
```bash
# After creating empty repo on github.com:
git remote add origin https://github.com/YOUR_USERNAME/enterprise-marl-benchmark.git
git push -u origin master
```

## Demo Video Script (5 min)
1. [0:00] Show repo structure + README
2. [0:30] `python -m pytest tests/ -v` → 34 passed
3. [1:00] `python scripts/run_benchmark.py --task all` → 100% oracle
4. [1:30] `streamlit run ui/app.py` → show dashboard
5. [2:00] Show trajectory HTML viewer
6. [2:30] `python scripts/run_llm_benchmark.py --provider ollama --model qwen2.5:3b --task customer_incident --episodes 1`
7. [3:30] `python scripts/run_llm_benchmark.py ... --no-hints` → show failure
8. [4:00] `python scripts/compare_hint_vs_zeroshot.py` → show gap table
9. [4:30] Walk through docs/policy_design.md — justify the 4-tier taxonomy
