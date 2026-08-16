$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
python examples/customer_incident_demo.py
python scripts/compare_baselines.py --episodes 10
