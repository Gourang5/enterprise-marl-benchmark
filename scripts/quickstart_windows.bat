@echo off
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
python examples\customer_incident_demo.py
python scripts\compare_baselines.py --episodes 10
