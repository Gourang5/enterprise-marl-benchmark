# Improvements applied after repository review

## Fixed

- Replaced brittle full-phrase SQL search with deterministic lexical ranking for Gmail, Jira, and Slack.
- Added regression coverage for the exact failed Ollama search phrases from the saved trajectory.
- Added Ollama server/model preflight with actionable errors.
- Added `scripts/diagnose.py` for clean separation of fixture/search/runtime failures.
- Moved the pre-fix failed Ollama output to `diagnostics/original_ollama_failure.*` so it is retained as evidence without being mistaken for final benchmark results.
- Added Dockerfile, Docker Compose, persistent Ollama model volume, model bootstrap, health gating, and `.env.example`.
- Added Docker documentation and clean-machine commands.
- Aligned README/LLM docs/presentation content with the actual Ollama-only implementation.
- Removed stale provider claims.
- Aligned task YAML IDs/horizons with runtime `v2` tasks and added a manifest consistency test.
- Re-ran 25-seed deterministic/random baselines after the changes.
- Confirmed the customer-incident demo still completes in 11 steps.
- Increased automated suite to 23 passing tests.

## Intentionally not faked

- No live Ollama success metric was fabricated because this review container does not run an Ollama daemon/model server.
- No Claude Code/Cursor development trace was fabricated; the assignment requires the genuine history.
- No claim is made that Docker containers were executed here because Docker is not installed in the review container. The Compose YAML was parsed/structurally checked, and the Python-side configuration is covered by tests/diagnostics.

See `docs/REVIEW_AND_IMPROVEMENTS.md` for the broader research/product recommendations.
