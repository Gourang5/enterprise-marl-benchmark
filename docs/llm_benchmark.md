# LLM benchmark

## Provider

The packaged benchmark is deliberately **Ollama-only**. This gives evaluators one reproducible local path and avoids paid-key setup differences.

```bash
python scripts/run_llm_benchmark.py --provider ollama --model qwen2.5:3b --task customer_incident --episodes 1
```

Use `--task all` for all task families and `--mode decentralized` to constrain each turn to the active employee.

## Preflight

The CLI checks that the Ollama server is reachable and the requested model is installed before starting an episode. This separates infrastructure errors from policy/task failures.

```bash
python scripts/diagnose.py --model qwen2.5:3b
```

## Action protocol

The model emits exactly one JSON action with:

- `agent_id`
- `tool` as `app.action`
- `parameters`
- optional short `reason`

The policy validates role permissions, parameter types, and grounded resource IDs before calling `env.step()`.

## Loop protection

Actions repeated without a world-state change are rejected. If a successful search already returned a concrete resource ID, a bounded recovery path may perform only the corresponding safe read operation. It never assigns, sends, comments, schedules, resolves, or otherwise completes business work for the model.

## Metrics

Results include success, progress, reward, steps, invalid action rate, repeated actions, policy errors, LLM calls, prompt/completion tokens, and latency. JSON and CSV outputs are written under `benchmark_results/`.

## Model guidance

`qwen2.5:3b` is the lightweight default. For a stronger demonstration on capable hardware, use `qwen2.5:7b`. Local-model success should be reported as an empirical benchmark result, not assumed from deterministic baseline solvability.
