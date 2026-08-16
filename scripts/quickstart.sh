#!/usr/bin/env bash
set -e
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
pytest -q
python examples/customer_incident_demo.py
python scripts/run_benchmark.py --task all --episodes 10
