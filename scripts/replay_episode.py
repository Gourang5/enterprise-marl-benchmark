#!/usr/bin/env python3
from pathlib import Path
import argparse, json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path: sys.path.insert(0, str(ROOT / "src"))
from enterprise_env.evaluation.replay import replay_episode

p=argparse.ArgumentParser(); p.add_argument("episode"); p.add_argument("--no-strict",action="store_true"); a=p.parse_args()
print(json.dumps(replay_episode(a.episode, strict=not a.no_strict), indent=2))
