#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from enterprise_env.generation import ScenarioFactory


def main():
    p = argparse.ArgumentParser(description="Generate reproducible scenario split manifests")
    p.add_argument("--output", default="generated_scenarios")
    p.add_argument("--train", type=int, default=100)
    p.add_argument("--dev", type=int, default=20)
    p.add_argument("--test", type=int, default=50)
    p.add_argument("--difficulty", choices=["easy", "medium", "hard", "adversarial"], default="medium")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    manifest = ScenarioFactory().export_dataset(args.output, args.train, args.dev, args.test, args.difficulty, args.seed)
    print(f"Generated {args.output}: {manifest['splits']}")


if __name__ == "__main__":
    main()
