# Docker execution

## Goal

Provide a clean-machine path where an evaluator does not need to manually install Python dependencies, start Ollama, or remember to pull the model.

## Stack

- `ollama`: local model server with persistent model volume.
- `model-bootstrap`: one-shot container that pulls `OLLAMA_MODEL` after the server is healthy.
- `benchmark`: installs the environment, runs diagnostics, then launches the selected benchmark task.

## Run

```bash
cp .env.example .env
docker compose up --build --abort-on-container-exit benchmark
```

Environment variables:

- `OLLAMA_MODEL` defaults to `qwen2.5:3b`.
- `TASK` defaults to `customer_incident`.
- `EPISODES` defaults to `1`.
- `MODE` defaults to `centralized`.

Results are bind-mounted to the host `benchmark_results/` directory.

## GPU note

The default compose file is portable and does not require a GPU. On Linux/NVIDIA systems, GPU passthrough can be added as a local compose override without changing benchmark code. Keeping GPU configuration out of the base file prevents Mac/Windows/CPU-only evaluators from failing during startup.
