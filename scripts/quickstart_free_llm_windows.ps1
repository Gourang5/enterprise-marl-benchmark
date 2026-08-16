Write-Host "Enterprise MARL local-Ollama quick start" -ForegroundColor Cyan
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
Write-Host "Pull the local model if needed:" -ForegroundColor Yellow
Write-Host "ollama pull qwen2.5:3b"
Write-Host "Then diagnose and run:" -ForegroundColor Yellow
Write-Host "python scripts/diagnose.py --model qwen2.5:3b"
Write-Host "python scripts/run_llm_benchmark.py --provider ollama --model qwen2.5:3b --task customer_incident --episodes 1"
