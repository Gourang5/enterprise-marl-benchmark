# Free local LLM setup

The benchmark uses **Ollama only**. No paid API key is required.

## Recommended: Docker Compose

```bash
cp .env.example .env
docker compose up --build --abort-on-container-exit benchmark
```

This starts Ollama, waits for health, pulls the configured model, runs diagnostics, and launches the benchmark.

## Host Ollama

Install Ollama, then:

```bash
ollama pull qwen2.5:3b
python scripts/diagnose.py --model qwen2.5:3b
python scripts/run_llm_benchmark.py --provider ollama --model qwen2.5:3b --task customer_incident --episodes 1
```

For a stronger machine, `qwen2.5:7b` is a better evaluation model. The 3B default is intentionally lightweight, but small models are more prone to planning loops.

## Common failures

- **Cannot reach Ollama**: start the Ollama server or use Docker Compose.
- **Model not installed**: run `ollama pull <model>`.
- **Search returns no result for a reasonable phrase**: run `python scripts/diagnose.py --skip-ollama`; the diagnostic checks the incident search fixture.
- **Policy loops**: inspect `policy_error`, `duplicate_rejections`, and the saved trajectory. Prefer the 7B model when hardware allows.

The policy never receives hidden verifier state. Diagnostics and search ranking only improve the simulated tool/runtime layer.
